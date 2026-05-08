import os
import json
import pandas as pd
import streamlit as st
import tabula
import tempfile
import re
import pdfplumber
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="FPK Converter", page_icon="⚡", layout="centered")

# --- FILE LOG ---
LOG_FILE = "log_konversi.json"

def load_log():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_log(entry: dict):
    log = load_log()
    log.insert(0, entry)
    log = log[:100]
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def hapus_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)


# --- STYLE CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Sora', sans-serif !important; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #0a0a0f;
        background-image:
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.15), transparent),
            radial-gradient(ellipse 40% 40% at 80% 80%, rgba(139, 92, 246, 0.08), transparent);
    }

    .block-container { padding-top: 2rem; max-width: 680px; }

    /* HEADER */
    .app-header { text-align: center; padding: 3rem 2rem 2rem; margin-bottom: 0.5rem; }
    .app-header .badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #818cf8; font-size: 11px; font-weight: 600;
        letter-spacing: 2px; text-transform: uppercase;
        padding: 6px 16px; border-radius: 100px; margin-bottom: 1.2rem;
    }
    .app-header h1 {
        font-size: 3rem !important; font-weight: 800 !important;
        color: #f1f5f9 !important; line-height: 1.1 !important;
        margin: 0 !important; letter-spacing: -1.5px;
    }
    .app-header h1 span {
        background: linear-gradient(135deg, #6366f1, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .app-header p { color: #64748b; font-size: 0.95rem; margin-top: 0.8rem; font-weight: 300; }

    /* EXPANDER */
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        border-radius: 14px !important; overflow: hidden !important; margin-bottom: 1rem !important;
    }
    [data-testid="stExpander"] summary {
        color: #94a3b8 !important; font-size: 0.85rem !important;
        font-weight: 600 !important; padding: 1rem 1.2rem !important;
    }
    [data-testid="stExpander"] summary:hover { color: #cbd5e1 !important; }
    [data-testid="stExpanderDetails"] {
        padding: 0 1.2rem 1.2rem !important; color: #64748b !important;
        font-size: 0.9rem !important; line-height: 1.7 !important;
    }

    /* INPUT */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important; color: #f1f5f9 !important;
        padding: 14px 18px !important; font-size: 0.95rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 4px !important; transition: all 0.2s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(99, 102, 241, 0.6) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
        background: rgba(99, 102, 241, 0.05) !important;
    }
    .stTextInput label {
        color: #94a3b8 !important; font-size: 0.8rem !important;
        font-weight: 600 !important; letter-spacing: 1px !important; text-transform: uppercase !important;
    }

    /* FILE UPLOADER */
    [data-testid="stFileUploader"] { position: relative !important; }
    [data-testid="stFileUploader"] section {
        background: rgba(255,255,255,0.02) !important;
        border: 1.5px dashed rgba(99, 102, 241, 0.35) !important;
        border-radius: 16px !important; padding: 2rem 1.5rem !important;
        transition: border-color 0.3s, background 0.3s !important;
        position: relative !important; overflow: visible !important;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: rgba(99, 102, 241, 0.7) !important;
        background: rgba(99, 102, 241, 0.04) !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        display: flex !important; flex-direction: column !important;
        align-items: center !important; gap: 0.75rem !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] { color: #64748b !important; text-align: center !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] span { color: #818cf8 !important; font-weight: 600 !important; }
    [data-testid="stFileUploader"] section button {
        background: rgba(99, 102, 241, 0.12) !important;
        border: 1px solid rgba(99, 102, 241, 0.35) !important;
        color: #818cf8 !important; border-radius: 10px !important;
        padding: 8px 20px !important; font-size: 0.85rem !important;
        font-weight: 600 !important; cursor: pointer !important;
        transition: all 0.2s !important; position: relative !important; z-index: 1 !important;
    }
    [data-testid="stFileUploader"] section button:hover {
        background: rgba(99, 102, 241, 0.22) !important;
        border-color: rgba(99, 102, 241, 0.6) !important;
    }

    /* BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important; height: 52px !important;
        font-size: 0.9rem !important; font-weight: 700 !important;
        letter-spacing: 0.5px !important; transition: all 0.2s ease !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25) !important; width: 100% !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.4) !important;
        filter: brightness(1.1) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    .reset-btn .stButton > button {
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #64748b !important; box-shadow: none !important; height: 52px !important;
    }
    .reset-btn .stButton > button:hover {
        background: rgba(255,255,255,0.05) !important; color: #94a3b8 !important;
        transform: none !important; box-shadow: none !important; filter: none !important;
    }

    .danger-btn .stButton > button {
        background: transparent !important;
        border: 1px solid rgba(239, 68, 68, 0.25) !important;
        color: #f87171 !important; box-shadow: none !important;
        height: 38px !important; font-size: 0.78rem !important; letter-spacing: 0.5px !important;
    }
    .danger-btn .stButton > button:hover {
        background: rgba(239, 68, 68, 0.08) !important;
        border-color: rgba(239, 68, 68, 0.5) !important; color: #fca5a5 !important;
        transform: none !important; box-shadow: none !important; filter: none !important;
    }

    /* DOWNLOAD */
    .stDownloadButton > button {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        color: #34d399 !important; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.1) !important;
        border-radius: 12px !important; height: 52px !important;
        font-size: 0.9rem !important; font-weight: 700 !important;
        width: 100% !important; transition: all 0.2s !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(16, 185, 129, 0.2) !important;
        border-color: rgba(16, 185, 129, 0.5) !important;
        box-shadow: 0 8px 30px rgba(16, 185, 129, 0.2) !important;
        color: #6ee7b7 !important; transform: translateY(-2px) !important;
    }

    /* STATS */
    .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1.5rem 0; }
    .stat-card {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px; padding: 1.5rem; position: relative; overflow: hidden;
    }
    .stat-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
    .stat-card.green-top::before { background: linear-gradient(90deg, #10b981, #34d399); }
    .stat-card.blue-top::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .stat-label { color: #475569; font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 0.5rem; }
    .stat-value { color: #f1f5f9; font-size: 1.6rem; font-weight: 800; letter-spacing: -0.5px; line-height: 1; }
    .stat-value.green { color: #34d399; }
    .stat-value.blue { color: #60a5fa; font-size: 1.1rem; }
    .stat-sub { color: #334155; font-size: 0.75rem; margin-top: 0.4rem; font-family: 'JetBrains Mono', monospace; }

    /* TINGKAT BADGE */
    .tingkat-badge {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 4px 12px; border-radius: 100px;
        font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px;
        text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
        margin-top: 0.4rem;
    }
    .tingkat-badge.ritl {
        background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); color: #a78bfa;
    }
    .tingkat-badge.rjtl {
        background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa;
    }

    /* LOG HISTORY */
    .log-title { color: #475569; font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; }
    .log-item {
        background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px; padding: 1rem 1.25rem; margin-bottom: 0.6rem;
        display: grid; grid-template-columns: 1fr auto; gap: 0.5rem; align-items: center;
        transition: border-color 0.2s;
    }
    .log-item:hover { border-color: rgba(99, 102, 241, 0.2); }
    .log-item-name {
        color: #cbd5e1; font-size: 0.85rem; font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .log-item-meta { color: #475569; font-size: 0.72rem; margin-top: 3px; font-family: 'JetBrains Mono', monospace; }
    .log-badge {
        display: inline-flex; align-items: center;
        padding: 2px 8px; border-radius: 100px; font-size: 0.65rem;
        font-weight: 700; letter-spacing: 1px; margin-left: 6px;
        font-family: 'JetBrains Mono', monospace; vertical-align: middle;
    }
    .log-badge.ritl { background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); color: #a78bfa; }
    .log-badge.rjtl { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; }
    .log-badge.other { background: rgba(100,116,139,0.12); border: 1px solid rgba(100,116,139,0.25); color: #94a3b8; }
    .log-item-right { text-align: right; }
    .log-item-total { color: #34d399; font-size: 0.85rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
    .log-item-count { color: #475569; font-size: 0.72rem; margin-top: 3px; font-family: 'JetBrains Mono', monospace; }
    .log-empty { color: #334155; font-size: 0.85rem; text-align: center; padding: 2rem 0; font-style: italic; }

    /* MISC */
    [data-testid="stAlert"] { border-radius: 12px !important; padding: 0.85rem 1rem !important; }
    [data-testid="stSpinner"] > div { border-top-color: #6366f1 !important; }
    hr { border-color: rgba(255,255,255,0.06) !important; margin: 1.5rem 0 !important; }
    [data-testid="stDataFrame"] {
        border-radius: 14px !important; overflow: hidden !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
    }
    h3, .stSubheader {
        color: #94a3b8 !important; font-size: 0.8rem !important;
        font-weight: 700 !important; letter-spacing: 2px !important; text-transform: uppercase !important;
    }
    .file-badge {
        display: inline-flex; align-items: center; gap: 8px;
        background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2);
        color: #34d399; padding: 8px 16px; border-radius: 100px;
        font-size: 0.8rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; margin: 0.5rem 0;
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


# --- FUNGSI EKSTRAK METADATA PDF ---
def ambil_metadata_pdf(pdf_path):
    """
    Ekstrak: bulan, tahun, dan tingkat pelayanan (RITL / RJTL / dll)
    dari halaman pertama PDF FPK BPJS.
    Return: (nama_file, tingkat)
    """
    nama_file  = "Hasil_Konversi_FPK"
    tingkat    = "UNKNOWN"
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

            # Ekstrak bulan & tahun
            bulan_pola = (r"(JANUARI|FEBRUARI|MARET|APRIL|MEI|JUNI|JULI|"
                          r"AGUSTUS|SEPTEMBER|OKTOBER|NOVEMBER|DESEMBER)")
            m_bulan = re.search(f"{bulan_pola}\\s+(\\d{{4}})", text, re.IGNORECASE)

            # Ekstrak tingkat pelayanan
            m_tingkat = re.search(
                r"Tingkat\s+Pelayanan\s*:\s*(RITL|RJTL|RITP|RJTP)",
                text, re.IGNORECASE
            )

            if m_bulan:
                bulan  = m_bulan.group(1).upper()
                tahun  = m_bulan.group(2)
                tingkat = m_tingkat.group(1).upper() if m_tingkat else "FPK"
                nama_file = f"FPK_{tingkat}_{bulan}_{tahun}"
            elif m_tingkat:
                tingkat   = m_tingkat.group(1).upper()
                nama_file = f"FPK_{tingkat}"

    except Exception as e:
        print(f"Gagal baca metadata: {e}")

    return nama_file, tingkat


# --- FUNGSI PROSES DATA TABEL ---
def process_data(pdf_path):
    df_list = tabula.read_pdf(
        pdf_path, pages='all', multiple_tables=True,
        lattice=True, pandas_options={'header': None}
    )
    if not df_list:
        raise ValueError("PDF tidak terbaca.")
    cleaned = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    df = pd.concat(cleaned, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    df_data['No.SEP'] = (df_data['No.SEP'].astype(str)
                         .str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip())
    df_data['Disetujui'] = (pd.to_numeric(
        df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True),
        errors='coerce').fillna(0).astype(int))
    return df_data[['No.SEP', 'Disetujui']].reset_index(drop=True)


# ============================================================
# HALAMAN UTAMA
# ============================================================
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
    3. Klik **⚡ Proses Sekarang** — nama file otomatis terdeteksi **(RITL/RJTL + Bulan + Tahun)**.
    4. Cek total nominal, lalu klik **Download CSV**.
    """)

uploaded_file = st.file_uploader(
    "Upload PDF FPK di sini",
    type=['pdf'],
    help="Format yang diterima: .pdf",
    label_visibility="collapsed"
)

if uploaded_file:
    if st.button("⚡ Proses Sekarang"):
        with st.spinner("Lagi dibaca isinya, tunggu bentar..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                nama_periode, tingkat = ambil_metadata_pdf(tmp_path)
                df_result = process_data(tmp_path)

                total    = int(df_result['Disetujui'].sum())
                jumlah   = len(df_result)
                filename = f"{nama_periode}.csv"

                st.session_state.final_df       = df_result
                st.session_state.final_total    = total
                st.session_state.final_count    = jumlah
                st.session_state.auto_filename  = filename
                st.session_state.tingkat        = tingkat

                save_log({
                    "waktu"    : datetime.now().strftime("%d %b %Y, %H:%M"),
                    "nama_file": filename,
                    "tingkat"  : tingkat,
                    "jumlah"   : jumlah,
                    "total"    : total,
                })

                os.unlink(tmp_path)
                st.success("✅ Berhasil diproses!")

            except Exception as e:
                st.error(f"Gagal memproses: {e}")


# --- HASIL KONVERSI ---
if 'final_df' in st.session_state:
    st.markdown(f"""
        <div class="file-badge">📄 {st.session_state.auto_filename}</div>
    """, unsafe_allow_html=True)

    total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")
    tingkat  = st.session_state.get('tingkat', '')
    t_lower  = tingkat.lower()
    t_label  = ("🏥 Rawat Inap (RITL)" if tingkat == "RITL"
                else "🏃 Rawat Jalan (RJTL)" if tingkat == "RJTL"
                else tingkat)

    st.markdown(f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Jumlah Data</div>
                <div class="stat-value">{st.session_state.final_count}</div>
                <div class="stat-sub">SEP records</div>
            </div>
            <div class="stat-card green-top">
                <div class="stat-label">Total Nominal</div>
                <div class="stat-value green">{total_rp}</div>
                <div class="stat-sub">total disetujui</div>
            </div>
            <div class="stat-card blue-top" style="grid-column: 1 / -1;">
                <div class="stat-label">Tingkat Pelayanan</div>
                <div class="tingkat-badge {t_lower}">{t_label}</div>
                <div class="stat-sub" style="margin-top:0.6rem;">terdeteksi otomatis dari PDF</div>
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
            "No"       : st.column_config.NumberColumn("No", width=50),
            "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d"),
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
            mime="text/csv",
        )
    with col2:
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("Reset"):
            for key in ['final_df', 'final_total', 'final_count', 'auto_filename', 'tingkat']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# LOG RIWAYAT KONVERSI
# ============================================================
st.divider()

log_data = load_log()

col_title, col_hapus = st.columns([4, 1])
with col_title:
    st.markdown('<div class="log-title">🕓 Riwayat Konversi</div>', unsafe_allow_html=True)
with col_hapus:
    if log_data:
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("Hapus Semua", key="hapus_log"):
            hapus_log()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if not log_data:
    st.markdown('<div class="log-empty">Belum ada riwayat konversi.</div>', unsafe_allow_html=True)
else:
    log_html = ""
    for item in log_data:
        total_fmt  = f"Rp {item['total']:,.0f}".replace(",", ".")
        tkt        = item.get('tingkat', '')
        tkt_lower  = tkt.lower() if tkt in ('RITL', 'RJTL') else 'other'
        badge_html = f'<span class="log-badge {tkt_lower}">{tkt}</span>' if tkt else ''
        log_html += f"""
        <div class="log-item">
            <div>
                <div class="log-item-name">📄 {item['nama_file']}{badge_html}</div>
                <div class="log-item-meta">🕓 {item['waktu']}</div>
            </div>
            <div class="log-item-right">
                <div class="log-item-total">{total_fmt}</div>
                <div class="log-item-count">{item['jumlah']} SEP</div>
            </div>
        </div>
        """
    st.markdown(log_html, unsafe_allow_html=True)
