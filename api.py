import re
import time
import tempfile
import os

import pandas as pd
import tabula
import pdfplumber

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FPK Converter API", version="1.0")

# Izinkan dipanggil dari Streamlit (local maupun deployed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── LOGIC EKSTRAKSI (dipindah dari app.py, tidak diubah) ───────

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

    Penanda wajib (semua harus ada di halaman pertama):
      1. Judul dokumen "RINCIAN DATA HASIL VERIFIKASI"
      2. Label "Nama RS"
      3. Label "Tingkat Pelayanan"
      4. Header kolom tabel: "No.SEP" dan "Disetujui"
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
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True,
                              lattice=True, pandas_options={'header': None})
    if not df_list:
        raise ValueError("PDF tidak terbaca.")
    cleaned = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
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


# ── ENDPOINTS ────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fpk-converter-api"}


async def _proses_satu_file(file: UploadFile, file_index: int = 0, total_files: int = 1) -> dict:
    """Helper internal: proses satu UploadFile, return dict hasil."""
    t_start  = time.perf_counter()
    tmp_path = None
    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        nama, tingkat = ambil_metadata_pdf(tmp_path)

        ok, pesan_error = validasi_format_pdf(tmp_path)
        if not ok:
            raise ValueError(pesan_error)

        df_res        = process_data(tmp_path)
        total         = int(df_res['Disetujui'].sum())
        jumlah        = len(df_res)

        dup      = df_res[df_res['No.SEP'].duplicated(keep=False)]
        duplikat = sorted(dup['No.SEP'].unique().tolist()) if not dup.empty else []

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
        # Error validasi format PDF: pesannya sudah jelas, tidak perlu dibungkus lagi.
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Gagal memproses PDF: {e}")


@app.post("/api/proses-batch")
async def proses_batch(files: list[UploadFile] = File(...)):
    """
    Proses beberapa PDF sekaligus.
    Return: { "results": [...], "total_files": N, "errors": [...] }
    """
    if not files:
        raise HTTPException(status_code=400, detail="Tidak ada file yang dikirim.")

    results = []
    errors  = []
    total   = len(files)

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
