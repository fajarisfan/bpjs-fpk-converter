# ðŸ¥ BPJS FPK Jaspel Converter

A lightweight automation tool to extract verified SEP numbers and approved claim amounts from BPJS Kesehatan FPK (Hasil Verifikasi) PDF documents â€” converting them into clean, structured CSV output ready for Jaspel financial processing.

> Built to eliminate a manual 7-minute conversion process per file, reducing it to under 10 seconds.

---

## ðŸš¨ Problem

The official BPJS vendor workflow for processing FPK (Finalisasi Pengajuan Klaim) documents required staff to manually extract data from multi-page PDFs following a step-by-step video guide â€” a slow, error-prone, and repetitive process done every billing cycle.

## âœ… Solution

This tool automates the entire extraction pipeline with two core modules:

**1. FPK Converter (`app.py`)**
- Upload the FPK PDF from BPJS Kesehatan portal
- Automatically extracts all **No. SEP** and **Biaya Disetujui** fields
- Outputs a clean `.csv` file â€” identical in structure to the manual result, but in seconds

**2. Jaspel Audit Validator (`audit.py`)**
- Cross-checks the converted CSV output against SIMRS Icha data
- Validates claim amounts using the official Jaspel calculation formula from BPJS documentation
- Flags any discrepancies before submission â€” preventing errors in the financial disbursement pipeline

---

## ðŸ› ï¸ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Web UI | Streamlit |
| PDF Parsing | pdfplumber |
| Data Processing | Pandas, Regex |
| Deployment | Streamlit Cloud |

---

## ðŸš€ Live Demo

ðŸ”— [pdf-converter-icha.streamlit.app](https://pdf-converter-icha.streamlit.app)

---

## ðŸ“‹ How It Works

```
Input  : BPJS FPK PDF (Rincian Data Hasil Verifikasi)
         â””â”€â”€ Contains: No.SEP, Tgl. Verifikasi, Biaya Riil RS, Diajukan, Disetujui

Process: Extract â†’ Clean â†’ Filter approved records only

Output : CSV file
         â””â”€â”€ Columns: No.SEP | Biaya Disetujui
```

---

## ðŸ’» Run Locally

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

## ðŸ“ Project Structure

```
bpjs-fpk-converter/
â”œâ”€â”€ app.py              # Main Streamlit app â€” FPK PDF to CSV converter
â”œâ”€â”€ audit.py            # Jaspel audit validator â€” cross-check CSV vs SIMRS data
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ packages.txt
â””â”€â”€ README.md
```

---

## ðŸŽ¯ Impact

- â±ï¸ Reduced per-file processing time from ~7 minutes (manual) to under 10 seconds
- âœ… Output format matches official manual workflow â€” zero retraining needed
- ðŸ” Built-in audit validator catches discrepancies before submission using official Jaspel formula
- ðŸ¥ Actively used in hospital Jaspel financial disbursement pipeline
- ðŸ”’ No patient data stored â€” processes only administrative claim numbers

---

## âš ï¸ Disclaimer

This tool was built independently as a personal productivity tool. It does not store, transmit, or log any hospital or patient data. All processing is done locally in-session.

---

## ðŸ‘¤ Author

**Isfan Fajar Anugrah**
- GitHub: [@fajarisfan](https://github.com/fajarisfan)
- LinkedIn: [isfan-fajar-anugrah](https://linkedin.com/in/isfan-fajar-anugrah)
