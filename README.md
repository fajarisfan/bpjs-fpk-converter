# 🏥 BPJS FPK Jaspel Converter

A lightweight automation tool to extract verified SEP numbers and approved claim amounts from BPJS Kesehatan FPK (Hasil Verifikasi) PDF documents — converting them into clean, structured CSV output ready for Jaspel financial processing.

> Built to eliminate a manual 7-minute conversion process per file, reducing it to under 10 seconds.

---

## 🚨 Problem

The official BPJS vendor workflow for processing FPK (Finalisasi Pengajuan Klaim) documents required staff to manually extract data from multi-page PDFs following a step-by-step video guide — a slow, error-prone, and repetitive process done every billing cycle.

## ✅ Solution

This tool automates the entire extraction pipeline:
- Upload the FPK PDF from BPJS Kesehatan portal
- Automatically extracts all **No. SEP** and **Biaya Disetujui** fields
- Outputs a clean `.csv` file — identical in structure to the manual result, but in seconds

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Web UI | Streamlit |
| PDF Parsing | pdfplumber |
| Data Processing | Pandas, Regex |
| Deployment | Streamlit Cloud |

---

## 🚀 Live Demo

🔗 [pdf-converter-icha.streamlit.app](https://pdf-converter-icha.streamlit.app)

---

## 📋 How It Works

```
Input  : BPJS FPK PDF (Rincian Data Hasil Verifikasi)
         └── Contains: No.SEP, Tgl. Verifikasi, Biaya Riil RS, Diajukan, Disetujui

Process: Extract → Clean → Filter approved records only

Output : CSV file
         └── Columns: No.SEP | Biaya Disetujui
```

---

## 💻 Run Locally

```bash
# Clone repo
git clone https://github.com/fajarisfan/bpjs-fpk-converter.git
cd bpjs-fpk-converter

# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
```

**Requirements:**
```
streamlit
pdfplumber
pandas
```

---

## 📁 Project Structure

```
bpjs-fpk-converter/
├── app.py              # Main Streamlit application
├── extractor.py        # PDF parsing & data extraction logic
├── requirements.txt
└── README.md
```

---

## 🎯 Impact

- ⏱️ Reduced per-file processing time from ~7 minutes (manual) to under 10 seconds
- ✅ Output format matches official manual workflow — zero retraining needed
- 🏥 Actively used in hospital Jaspel financial disbursement pipeline
- 🔒 No patient data stored — processes only administrative claim numbers

---

## ⚠️ Disclaimer

This tool was built independently as a personal productivity tool. It does not store, transmit, or log any hospital or patient data. All processing is done locally in-session.

---

## 👤 Author

**Isfan Fajar Anugrah**
- GitHub: [@fajarisfan](https://github.com/fajarisfan)
- LinkedIn: [isfan-fajar-anugrah](https://linkedin.com/in/isfan-fajar-anugrah)
