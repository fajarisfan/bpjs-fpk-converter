import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import re
import pdfplumber
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="FPK Converter", page_icon="⚡", layout="centered")

# --- STYLE CSS MODERN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    * { font-family: 'Sora', sans-serif !important; }
    
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    
    /* Background */
    .stApp {
        background-color: #0a0a0f;
        background-image: 
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.15), transparent),
            radial-gradient(ellipse 40% 40% at 80% 80%, rgba(139, 92, 246, 0.08), transparent);
    }
    
    /* Sembunyiin semua elemen default streamlit yg ga perlu */
    .block-container { padding-top: 2rem; max-width: 680px; }

    /* HEADER */
    .app-header {
        text-align: center;
        padding: 3rem 2rem 2rem;
        margin-bottom: 0.5rem;
    }
    .app-header .badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #818cf8;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        padding: 6px 16px;
        border-radius: 100px;
        margin-bottom: 1.2rem;
    }
    .app-header h1 {
        font-size: 3rem !important;
        font-weight: 800 !important;
        color: #f1f5f9 !important;
        line-height: 1.1 !important;
        margin: 0 !important;
        letter-spacing: -1.5px;
    }
    .app-header h1 span {
        background: linear-gradient(135deg, #6366f1, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .app-header p {
        color: #64748b;
        font-size: 0.95rem;
        margin-top: 0.8rem;
        font-weight: 300;
    }

    /* LOGIN BOX */
    .login-container {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 20px;
        padding: 2.5rem;
        backdrop-filter: blur(10px);
        margin-top: 1rem;
    }
    
    /* UPLOAD AREA */
    .upload-zone {
        background: rgba(255,255,255,0.02);
        border: 1.5px dashed rgba(99, 102, 241, 0.35);
        border-radius: 20px;
        padding: 2rem;
        transition: all 0.3s;
        margin-bottom: 1rem;
    }
    .upload-zone:hover {
        border-color: rgba(99, 102, 241, 0.7);
        background: rgba(99, 102, 241, 0.05);
    }

    /* INPUT FIELDS */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: #f1f5f9 !important;
        padding: 14px 18px !important;
        font-size: 0.95rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 4px !important;
        transition: all 0.2s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(99, 102, 241, 0.6) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
        background: rgba(99, 102, 241, 0.05) !important;
    }
    .stTextInput label {
        color: #94a3b8 !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    /* FILE UPLOADER */
    .stFileUploader > div {
        background: rgba(255,255,255,0.02) !important;
        border: 1.5px dashed rgba(99, 102, 241, 0.35) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        transition: all 0.3s !important;
    }
    .stFileUploader > div:hover {
        border-color: rgba(99, 102, 241, 0.7) !important;
        background: rgba(99, 102, 241, 0.05) !important;
    }
    .stFileUploader label {
        color: #94a3b8 !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        color: #64748b !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] span {
        color: #818cf8 !important;
        font-weight: 600 !important;
    }

    /* BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 52px !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.4) !important;
        filter: brightness(1.1) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* RESET BUTTON - khusus */
    .reset-btn > button {
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #64748b !important;
        box-shadow: none !important;
    }
    .reset-btn > button:hover {
        background: rgba(255,255,255,0.05) !important;
        color: #94a3b8 !important;
        transform: none !important;
        box-shadow: none !important;
    }

    /* DOWNLOAD BUTTON */
    .stDownloadButton > button {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        color: #34d399 !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.1) !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(16, 185, 129, 0.2) !important;
        border-color: rgba(16, 185, 129, 0.5) !important;
        box-shadow: 0 8px 30px rgba(16, 185, 129, 0.2) !important;
        color: #6ee7b7 !important;
    }

    /* STATS CARDS */
    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .stat-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: all 0.2s;
    }
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
    .stat-card:last-child::before {
        background: linear-gradient(90deg, #10b981, #34d399);
    }
    .stat-label {
        color: #475569;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .stat-value {
        color: #f1f5f9;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1;
    }
    .stat-value.green { color: #34d399; }
    .stat-sub {
        color: #334155;
        font-size: 0.75rem;
        margin-top: 0.4rem;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* SUCCESS & ERROR MSGS */
    .stSuccess {
        background: rgba(16, 185, 129, 0.08) !important;
        border: 1px solid rgba(16, 185, 129, 0.2) !important;
        border-radius: 12px !important;
        color: #34d399 !important;
    }
    .stError {
        background: rgba(239, 68, 68, 0.08) !important;
        border: 1px solid rgba(239, 68, 68, 0.2) !important;
        border-radius: 12px !important;
    }

    /* SPINNER */
    .stSpinner > div {
        border-top-color: #6366f1 !important;
    }

    /* DIVIDER */
    hr {
        border-color: rgba(255,255,255,0.06) !important;
        margin: 1.5rem 0 !important;
    }

    /* DATAFRAME */
    .stDataFrame {
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
    }
    [data-testid="stDataFrameResizable"] {
        background: rgba(255,255,255,0.02) !important;
    }

    /* SUBHEADER */
    .stSubheader, h3 {
        color: #94a3b8 !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
    }

    /* SUCCESS BADGE */
    .file-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: #34d399;
        padding: 8px 16px;
        border-radius: 100px;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# --- LOGIKA LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("""
        <div class="app-header">
            <div class="badge">⚡ FPK Converter</div>
            <h1>Selamat <span>Datang</span></h1>
            <p>Masukkan PIN untuk mengakses aplikasi</p>
        </div>
    """, unsafe_allow_html=True)

    pin = st.text_input("PIN AKSES", type="password", placeholder="••••")
    if st.button("Masuk →"):
        if pin == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("❌ PIN salah. Coba lagi.")
    st.stop()


# --- FUNGSI EKSTRAK NAMA PERIODE ---
def ambil_nama_periode(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            bulan_pola = r"(JANUARI|FEBRUARI|MARET|APRIL|MEI|JUNI|JULI|AGUSTUS|SEPTEMBER|OKTOBER|NOVEMBER|DESEMBER)"
            match = re.search(f"{bulan_pola}\s+(\d{{4}})", text, re.IGNORECASE)
            if match:
                bulan = match.group(1).upper()
                tahun = match.group(2)
                return f"FPK_{bulan}_{tahun}"
    except Exception as e:
        print(f"Gagal baca periode: {e}")
    return "Hasil_Konversi_FPK"


# --- FUNGSI PROSES DATA TABEL ---
def process_data(pdf_path):
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
    if not df_list:
        raise ValueError("PDF tidak terbaca.")
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0).astype(int)
    return df_data[['No.SEP', 'Disetujui']].reset_index(drop=True)


# --- HALAMAN UTAMA ---
st.markdown("""
    <div class="app-header">
        <div class="badge">⚡ Converter Tools</div>
        <h1>FPK <span>Converter</span></h1>
        <p>Upload PDF FPK, konversi otomatis ke CSV siap pakai</p>
    </div>
""", unsafe_allow_html=True)

with st.expander("ℹ️ Cara Penggunaan"):
    st.markdown("""
    1. Pastikan file PDF adalah **Lampiran FPK** (ada tabel rincian SEP).
    2. Klik tombol di bawah atau **Drag & Drop** file ke kotak.
    3. Klik **⚡ Proses Sekarang** dan tunggu data muncul.
    4. Cek total nominal, lalu klik **Download CSV**.
    """)
    
uploaded_file = st.file_uploader(
    "Upload PDF FPK di sini",
    type=['pdf'],
    label_visibility="collapsed"
    help="Format yang diterima: .pdf"
)

if uploaded_file:
    if st.button("⚡ Proses Sekarang"):
        with st.spinner("Lagi dibaca isinya, tunggu bentar..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                nama_periode = ambil_nama_periode(tmp_path)
                df_result = process_data(tmp_path)

                st.session_state.final_df = df_result
                st.session_state.final_total = df_result['Disetujui'].sum()
                st.session_state.final_count = len(df_result)
                st.session_state.auto_filename = f"{nama_periode}.csv"

                os.unlink(tmp_path)
                st.success(f"✅ Berhasil diproses!")

            except Exception as e:
                st.error(f"Gagal memproses: {e}")

if 'final_df' in st.session_state:
    st.markdown(f"""
        <div class="file-badge">
            📄 {st.session_state.auto_filename}
        </div>
    """, unsafe_allow_html=True)

    total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")

    st.markdown(f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Jumlah Data</div>
                <div class="stat-value">{st.session_state.final_count}</div>
                <div class="stat-sub">SEP records</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Nominal</div>
                <div class="stat-value green">{total_rp}</div>
                <div class="stat-sub">total disetujui</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Preview Data")
    df_preview = st.session_state.final_df.copy()
    df_preview.insert(0, 'No', range(1, 1 + len(df_preview)))
    st.dataframe(
        df_preview,
        use_container_width=True,
        height=320,
        hide_index=True,
        column_config={
            "No": st.column_config.NumberColumn("No", width=50),
            "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d")
        }
    )

    st.divider()

    col1, col2 = st.columns([3, 1])
    with col1:
        csv_data = st.session_state.final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇ Download CSV",
            data=csv_data,
            file_name=st.session_state.auto_filename,
            mime="text/csv"
        )
    with col2:
        with st.container():
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("Reset"):
                for key in ['final_df', 'final_total', 'final_count', 'auto_filename']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
