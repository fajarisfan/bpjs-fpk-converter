import re
import time
import tempfile
import os
import uuid
import threading

import pandas as pd
import tabula
import pdfplumber

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FPK Converter API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── TASK STORAGE ──────────────────────────────────────────
tasks = {}

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

def process_pdf_task(task_id: str, file_content: bytes, filename: str):
    """Proses PDF di background, kirim log per baris."""
    logs = []
    logs.append(f"🚀 Memulai proses untuk {filename}")
    tasks[task_id]['logs'] = logs
    tasks[task_id]['status'] = 'processing'

    tmp_path = None
    try:
        # Simpan file sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        # Step 1: metadata
        logs.append("📄 Membaca metadata PDF...")
        nama, tingkat = ambil_metadata_pdf(tmp_path)
        logs.append(f"✅ Tingkat: {tingkat}, Nama file: {nama}.csv")
        tasks[task_id]['logs'] = logs

        # Step 2: ekstraksi tabel
        logs.append("📊 Mengekstrak tabel dengan tabula (pages='all')...")
        df_list = tabula.read_pdf(tmp_path, pages='all', multiple_tables=True,
                                  lattice=True, pandas_options={'header': None})
        logs.append(f"✅ Ditemukan {len(df_list)} tabel mentah")
        tasks[task_id]['logs'] = logs

        # Step 3: gabungkan & bersihkan
        cleaned = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
        df = pd.concat(cleaned, ignore_index=True)
        df_data = df.iloc[:, :6].copy()
        df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
        df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
        df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
        df_data['Disetujui'] = pd.to_numeric(
            df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True),
            errors='coerce').fillna(0).astype(int)

        total_rows = len(df_data)
        logs.append(f"🧹 Memproses {total_rows} baris data...")
        tasks[task_id]['logs'] = logs

        # Step 4: proses per baris dan kirim log setiap 50 baris
        data_list = []
        for idx, row in df_data.iterrows():
            sep = row['No.SEP']
            disetujui = int(row['Disetujui'])
            data_list.append({"no": idx+1, "no_sep": sep, "disetujui": disetujui})
            # Kirim log per 50 baris atau baris terakhir
            if (idx + 1) % 50 == 0 or (idx + 1) == total_rows:
                logs.append(f"   ✅ Baris {idx+1}/{total_rows}: SEP {sep} → Rp {disetujui:,}")
                tasks[task_id]['logs'] = logs

        # Step 5: selesai
        total = sum(item['disetujui'] for item in data_list)
        dup = df_data[df_data['No.SEP'].duplicated(keep=False)]
        duplikat = sorted(dup['No.SEP'].unique().tolist()) if not dup.empty else []

        logs.append(f"💰 Total nominal: Rp {total:,.0f}")
        logs.append(f"🔍 Duplikat: {len(duplikat)} ditemukan")
        logs.append("✅ Selesai memproses semua baris")

        tasks[task_id]['status'] = 'done'
        tasks[task_id]['result'] = {
            "filename": f"{nama}.csv",
            "tingkat": tingkat,
            "jumlah": total_rows,
            "total": total,
            "duplikat": duplikat,
            "data": data_list,
            "processing_time_ms": 0,  # akan dihitung di endpoint
        }
        tasks[task_id]['logs'] = logs

    except Exception as e:
        logs.append(f"❌ ERROR: {str(e)}")
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)
        tasks[task_id]['logs'] = logs
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.post("/api/proses")
async def proses_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus PDF.")

    task_id = str(uuid.uuid4())
    content = await file.read()

    tasks[task_id] = {
        "status": "pending",
        "logs": [f"📤 Task {task_id} dibuat, menunggu proses..."],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=process_pdf_task,
        args=(task_id, content, file.filename)
    )
    thread.daemon = True
    thread.start()

    return {"task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task tidak ditemukan")

    response = {
        "status": task["status"],
        "logs": task.get("logs", []),
    }
    if task["status"] == "done":
        response["result"] = task.get("result")
    if task["status"] == "error":
        response["error"] = task.get("error")
    return response

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fpk-converter-api"}
