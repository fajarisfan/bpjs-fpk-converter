import os
import re
import time
import json
import tempfile
import asyncio

import pandas as pd
import tabula
import pdfplumber

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, Response

app = FastAPI(title="FPK Converter API - Streaming", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── METADATA & VALIDASI ─────────────────────────────────────────

def ambil_metadata_pdf(pdf_path: str):
    nama_file, tingkat = "Hasil_Konversi_FPK", "UNKNOWN"
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
            bulan_pola = (r"(JANUARI|FEBRUARI|MARET|APRIL|MEI|JUNI|JULI|"
                          r"AGUSTUS|SEPTEMBER|OKTOBER|NOVEMBER|DESEMBER)")
            m_b = re.search(f"{bulan_pola}\\s+(\\d{{4}})", text, re.IGNORECASE)
            m_t = re.search(r"Tingkat\s+Pelayanan\s*:\s*(RITL|RJTL|RITP|RJTP)", text, re.IGNORECASE)
            if m_b:
                bulan     = m_b.group(1).upper()
                tahun     = m_b.group(2)
                tingkat   = m_t.group(1).upper() if m_t else "FPK"
                nama_file = f"FPK_{tingkat}_{bulan}_{tahun}"
            elif m_t:
                tingkat   = m_t.group(1).upper()
                nama_file = f"FPK_{tingkat}"
    except Exception as e:
        print(f"Gagal baca metadata: {e}")
    return nama_file, tingkat


def validasi_format_pdf(pdf_path: str):
    """
    Cek apakah PDF yang diupload benar-benar dokumen 'RINCIAN DATA HASIL
    VERIFIKASI' (FPK BPJS Kesehatan), bukan dokumen lain yang kebetulan
    juga berformat .pdf.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return False, "PDF tidak memiliki halaman."
            text = pdf.pages[0].extract_text() or ""
    except Exception as e:
        return False, f"PDF tidak bisa dibuka/dibaca: {e}"

    penanda_wajib = {
        "judul dokumen 'RINCIAN DATA HASIL VERIFIKASI'": r"RINCIAN\s+DATA\s+HASIL\s+VERIFIKASI",
        "label 'Nama RS'": r"Nama\s+RS",
        "label 'Tingkat Pelayanan'": r"Tingkat\s+Pelayanan",
        "kolom 'No.SEP'": r"No\.?\s*SEP",
        "kolom 'Disetujui'": r"Disetujui",
    }

    hilang = [
        nama for nama, pola in penanda_wajib.items()
        if not re.search(pola, text, re.IGNORECASE)
    ]

    if hilang:
        detail = ", ".join(hilang)
        return False, (
            "Format PDF tidak sesuai. PDF harus berupa dokumen "
            "'RINCIAN DATA HASIL VERIFIKASI' (FPK BPJS Kesehatan). "
            f"Penanda yang tidak ditemukan: {detail}."
        )

    return True, ""


def process_data(pdf_path: str) -> pd.DataFrame:
    """Ekstrak tabel dari PDF. Coba lattice dulu, fallback ke stream kalau kosong."""
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True,
                              lattice=True, pandas_options={'header': None})
    if not df_list:
        df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True,
                                  stream=True, pandas_options={'header': None})
    if not df_list:
        raise ValueError("PDF tidak terbaca.")

    cleaned = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    if not cleaned:
        raise ValueError("Tidak ada tabel valid yang ditemukan di PDF.")

    df      = pd.concat(cleaned, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    df_data['No.SEP'] = (df_data['No.SEP'].astype(str)
                         .str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip())
    df_data['Disetujui'] = (pd.to_numeric(
        df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True),
        errors='coerce').fillna(0).astype(int))
    return df_data[['No.SEP', 'Disetujui']].reset_index(drop=True)


def deteksi_duplikat(df_res: pd.DataFrame):
    dup = df_res[df_res['No.SEP'].duplicated(keep=False)]
    return sorted(dup['No.SEP'].unique().tolist()) if not dup.empty else []


def simpan_upload_sementara(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        return tmp.name


# ── HEALTH ───────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fpk-converter-api"}


# ── /api/proses — single file, non-streaming (dipakai Streamlit) ──

async def _proses_satu_file(file: UploadFile, file_index: int = 0, total_files: int = 1) -> dict:
    t_start  = time.perf_counter()
    tmp_path = None
    try:
        content  = await file.read()
        tmp_path = simpan_upload_sementara(content)

        nama, tingkat = ambil_metadata_pdf(tmp_path)

        ok, pesan_error = validasi_format_pdf(tmp_path)
        if not ok:
            raise ValueError(pesan_error)

        df_res   = process_data(tmp_path)
        total    = int(df_res['Disetujui'].sum())
        jumlah   = len(df_res)
        duplikat = deteksi_duplikat(df_res)

        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

        return {
            "success": True,
            "filename": f"{nama}.csv",
            "original_filename": file.filename,
            "tingkat": tingkat,
            "jumlah": jumlah,
            "total": total,
            "duplikat": duplikat,
            "data": df_res.to_dict(orient="records"),
            "processing_time_ms": elapsed_ms,
            "file_index": file_index,
            "total_files": total_files,
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/proses")
async def proses_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus berformat PDF.")
    try:
        return await _proses_satu_file(file, file_index=0, total_files=1)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Gagal memproses PDF: {e}")


@app.post("/api/proses-batch")
async def proses_batch(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Tidak ada file yang dikirim.")

    results, errors = [], []
    total = len(files)

    for i, file in enumerate(files):
        if not file.filename.lower().endswith(".pdf"):
            errors.append({"file": file.filename, "error": "Bukan file PDF."})
            continue
        try:
            hasil = await _proses_satu_file(file, file_index=i, total_files=total)
            results.append(hasil)
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})

    return {
        "total_files": total,
        "berhasil": len(results),
        "gagal": len(errors),
        "results": results,
        "errors": errors,
    }


# ── /api/proses-stream — dipakai FPK Extractor & fpk.sh (Termux) ──

async def generate_stream(file: UploadFile):
    tmp_path = None
    try:
        content  = await file.read()
        tmp_path = simpan_upload_sementara(content)

        nama, tingkat = ambil_metadata_pdf(tmp_path)

        ok, pesan_error = validasi_format_pdf(tmp_path)
        if not ok:
            yield json.dumps({"type": "error", "message": pesan_error}) + "\n"
            return

        df_res     = process_data(tmp_path)
        total_rows = len(df_res)
        total_nominal_all = int(df_res['Disetujui'].sum())
        duplikat   = deteksi_duplikat(df_res)

        yield json.dumps({
            "type": "metadata",
            "tingkat": tingkat,
            "filename": nama,
            "total_rows": total_rows,
            "total_nominal": total_nominal_all
        }) + "\n"

        total_data = 0
        total_nominal = 0
        for _, row in df_res.iterrows():
            yield json.dumps({
                "type": "data",
                "No.SEP": row['No.SEP'],
                "Disetujui": int(row['Disetujui'])
            }) + "\n"
            total_data += 1
            total_nominal += int(row['Disetujui'])

            percent = int((total_data / total_rows) * 100) if total_rows else 100
            yield json.dumps({"type": "progress", "percent": percent}) + "\n"
            await asyncio.sleep(0.001)

        # field "duplikat" bersifat tambahan — konsumen lama yang cuma
        # ambil field tertentu (mis. jq di fpk.sh) tidak akan terganggu.
        yield json.dumps({
            "type": "done",
            "total_nominal": total_nominal,
            "total_rows": total_data,
            "duplikat": duplikat
        }) + "\n"

    except Exception as e:
        yield json.dumps({"type": "error", "message": str(e)}) + "\n"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/proses-stream")
async def proses_stream(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus PDF")
    return StreamingResponse(generate_stream(file), media_type="application/x-ndjson")


# ── /api/data — raw JSON non-streaming (dipakai tombol 'Raw JSON') ──

@app.post("/api/data")
async def get_data(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus PDF")
    tmp_path = None
    try:
        content  = await file.read()
        tmp_path = simpan_upload_sementara(content)

        ok, pesan_error = validasi_format_pdf(tmp_path)
        if not ok:
            raise HTTPException(status_code=422, detail=pesan_error)

        df_res = process_data(tmp_path)
        return [
            {"type": "data", "No.SEP": r["No.SEP"], "Disetujui": int(r["Disetujui"])}
            for r in df_res.to_dict(orient="records")
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Gagal memproses PDF: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/download-csv")
async def download_csv(rows: list[dict]):
    if not rows:
        raise HTTPException(status_code=400, detail="Data kosong.")
    df = pd.DataFrame(rows)
    if not {"No.SEP", "Disetujui"}.issubset(df.columns):
        raise HTTPException(status_code=400, detail="Format data tidak sesuai.")
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hasil_fpk.csv"}
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r") as f:
        return f.read()
