import os
import json
import re
import tempfile
import pandas as pd
import streamlit as st
import tabula
import pdfplumber
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta

# ── CONFIG ──────────────────────────────────────────────────
st.set_page_config(page_title="FPK Converter", page_icon="⚡", layout="centered")

LOG_FILE = "log_konversi.json"

def now_wib():
    return datetime.now(timezone.utc) + timedelta(hours=7)

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
    with open(LOG_FILE, "w") as f:
        json.dump(log[:100], f, ensure_ascii=False, indent=2)

def hapus_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

# ── THEME CSS ────────────────────────────────────────────────
def inject_css(dark: bool):
    if dark:
        bg          = "#0a0a0f"
        bg_grad     = "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.15), transparent), radial-gradient(ellipse 40% 40% at 80% 80%, rgba(139,92,246,0.08), transparent)"
        surface     = "rgba(255,255,255,0.03)"
        border      = "rgba(255,255,255,0.07)"
        border2     = "rgba(255,255,255,0.06)"
        text_h      = "#f1f5f9"
        text_body   = "#64748b"
        text_muted  = "#475569"
        text_dim    = "#334155"
        input_bg    = "rgba(255,255,255,0.04)"
        input_bdr   = "rgba(255,255,255,0.1)"
        input_col   = "#f1f5f9"
        label_col   = "#94a3b8"
        exp_text    = "#94a3b8"
        exp_detail  = "#64748b"
        log_name    = "#cbd5e1"
        log_meta    = "#475569"
        spinner_col = "#6366f1"
        toggle_icon = "☀️"
        toggle_tip  = "Light Mode"
    else:
        bg          = "#f1f5f9"
        bg_grad     = "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.08), transparent)"
        surface     = "rgba(0,0,0,0.02)"
        border      = "rgba(0,0,0,0.08)"
        border2     = "rgba(0,0,0,0.06)"
        text_h      = "#1e293b"
        text_body   = "#475569"
        text_muted  = "#64748b"
        text_dim    = "#94a3b8"
        input_bg    = "rgba(255,255,255,0.8)"
        input_bdr   = "rgba(0,0,0,0.12)"
        input_col   = "#1e293b"
        label_col   = "#475569"
        exp_text    = "#475569"
        exp_detail  = "#64748b"
        log_name    = "#1e293b"
        log_meta    = "#64748b"
        spinner_col = "#6366f1"
        toggle_icon = "🌙"
        toggle_tip  = "Dark Mode"

    st.session_state._toggle_icon = toggle_icon
    st.session_state._toggle_tip  = toggle_tip

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] {{ font-family: 'Sora', sans-serif !important; }}
#MainMenu {{visibility:hidden;}} footer {{visibility:hidden;}} header {{visibility:hidden;}}

.stApp {{
    background-color: {bg};
    background-image: {bg_grad};
}}
.block-container {{ padding-top: 1.5rem; max-width: 680px; }}

/* HEADER */
.app-header {{ text-align:center; padding:2.5rem 2rem 1.5rem; margin-bottom:0.5rem; }}
.app-header .badge {{
    display:inline-block;
    background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3);
    color:#818cf8; font-size:11px; font-weight:600; letter-spacing:2px;
    text-transform:uppercase; padding:6px 16px; border-radius:100px; margin-bottom:1.2rem;
}}
.app-header h1 {{
    font-size:3rem !important; font-weight:800 !important; color:{text_h} !important;
    line-height:1.1 !important; margin:0 !important; letter-spacing:-1.5px;
}}
.app-header h1 span {{
    background:linear-gradient(135deg,#6366f1,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}}
.app-header p {{ color:{text_body}; font-size:0.95rem; margin-top:0.8rem; font-weight:300; }}

/* THEME TOGGLE */
.theme-bar {{
    display:flex; justify-content:flex-end; margin-bottom:0.5rem;
}}
.theme-btn {{
    background:{surface}; border:1px solid {border};
    color:{text_muted}; font-size:0.75rem; font-weight:600;
    padding:6px 14px; border-radius:100px; cursor:pointer;
    letter-spacing:0.5px; transition:all 0.2s;
}}

/* EXPANDER */
[data-testid="stExpander"] {{
    background:{surface} !important; border:1px solid {border} !important;
    border-radius:14px !important; overflow:hidden !important; margin-bottom:1rem !important;
}}
[data-testid="stExpander"] summary {{
    color:{exp_text} !important; font-size:0.85rem !important;
    font-weight:600 !important; padding:1rem 1.2rem !important;
}}
[data-testid="stExpanderDetails"] {{
    padding:0 1.2rem 1.2rem !important; color:{exp_detail} !important;
    font-size:0.9rem !important; line-height:1.7 !important;
}}

/* TABS */
[data-testid="stTabs"] [data-testid="stTab"] {{
    background:{surface} !important; border:1px solid {border} !important;
    border-radius:10px 10px 0 0 !important; color:{text_muted} !important;
    font-size:0.8rem !important; font-weight:600 !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background:rgba(99,102,241,0.15) !important;
    border-color:rgba(99,102,241,0.35) !important; color:#818cf8 !important;
}}

/* INPUT */
.stTextInput > div > div > input {{
    background:{input_bg} !important; border:1px solid {input_bdr} !important;
    border-radius:12px !important; color:{input_col} !important;
    padding:14px 18px !important; font-size:0.95rem !important;
    font-family:'JetBrains Mono',monospace !important;
    letter-spacing:4px !important; transition:all 0.2s !important;
}}
.stTextInput > div > div > input:focus {{
    border-color:rgba(99,102,241,0.6) !important;
    box-shadow:0 0 0 3px rgba(99,102,241,0.1) !important;
    background:rgba(99,102,241,0.05) !important;
}}
.stTextInput label {{
    color:{label_col} !important; font-size:0.8rem !important;
    font-weight:600 !important; letter-spacing:1px !important; text-transform:uppercase !important;
}}

/* FILE UPLOADER */
[data-testid="stFileUploader"] {{ position:relative !important; }}
[data-testid="stFileUploader"] section {{
    background:{surface} !important; border:1.5px dashed rgba(99,102,241,0.35) !important;
    border-radius:16px !important; padding:2rem 1.5rem !important;
    transition:all 0.3s !important; position:relative !important; overflow:visible !important;
}}
[data-testid="stFileUploader"] section:hover {{
    border-color:rgba(99,102,241,0.7) !important; background:rgba(99,102,241,0.04) !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    display:flex !important; flex-direction:column !important; align-items:center !important; gap:0.75rem !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] {{ color:{text_body} !important; text-align:center !important; }}
[data-testid="stFileUploaderDropzoneInstructions"] span {{ color:#818cf8 !important; font-weight:600 !important; }}
[data-testid="stFileUploader"] section button {{
    background:rgba(99,102,241,0.12) !important; border:1px solid rgba(99,102,241,0.35) !important;
    color:#818cf8 !important; border-radius:10px !important; padding:8px 20px !important;
    font-size:0.85rem !important; font-weight:600 !important; z-index:1 !important; position:relative !important;
}}

/* BUTTONS */
.stButton > button {{
    background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%) !important;
    color:white !important; border:none !important; border-radius:12px !important;
    height:52px !important; font-size:0.9rem !important; font-weight:700 !important;
    transition:all 0.2s ease !important; box-shadow:0 4px 20px rgba(99,102,241,0.25) !important;
    width:100% !important;
}}
.stButton > button:hover {{
    transform:translateY(-2px) !important; box-shadow:0 8px 30px rgba(99,102,241,0.4) !important;
    filter:brightness(1.1) !important;
}}
.stButton > button:active {{ transform:translateY(0) !important; }}

.reset-btn .stButton > button {{
    background:transparent !important; border:1px solid {border} !important;
    color:{text_muted} !important; box-shadow:none !important; height:52px !important;
}}
.reset-btn .stButton > button:hover {{
    background:{surface} !important; color:{label_col} !important;
    transform:none !important; box-shadow:none !important; filter:none !important;
}}

.toggle-btn .stButton > button {{
    background:{surface} !important; border:1px solid {border} !important;
    color:{text_muted} !important; box-shadow:none !important;
    height:36px !important; font-size:0.78rem !important; width:auto !important;
    padding:0 14px !important; border-radius:100px !important;
}}
.toggle-btn .stButton > button:hover {{
    background:rgba(99,102,241,0.1) !important; border-color:rgba(99,102,241,0.3) !important;
    color:#818cf8 !important; transform:none !important; box-shadow:none !important; filter:none !important;
}}

.danger-btn .stButton > button {{
    background:transparent !important; border:1px solid rgba(239,68,68,0.25) !important;
    color:#f87171 !important; box-shadow:none !important;
    height:38px !important; font-size:0.78rem !important;
}}
.danger-btn .stButton > button:hover {{
    background:rgba(239,68,68,0.08) !important; border-color:rgba(239,68,68,0.5) !important;
    color:#fca5a5 !important; transform:none !important; box-shadow:none !important; filter:none !important;
}}

/* DOWNLOAD */
.stDownloadButton > button {{
    background:rgba(16,185,129,0.1) !important; border:1px solid rgba(16,185,129,0.3) !important;
    color:#34d399 !important; box-shadow:0 4px 20px rgba(16,185,129,0.1) !important;
    border-radius:12px !important; height:52px !important; font-size:0.9rem !important;
    font-weight:700 !important; width:100% !important; transition:all 0.2s !important;
}}
.stDownloadButton > button:hover {{
    background:rgba(16,185,129,0.2) !important; border-color:rgba(16,185,129,0.5) !important;
    box-shadow:0 8px 30px rgba(16,185,129,0.2) !important; color:#6ee7b7 !important;
    transform:translateY(-2px) !important;
}}

/* STATS */
.stats-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin:1.5rem 0; }}
.stat-card {{
    background:{surface}; border:1px solid {border};
    border-radius:16px; padding:1.5rem; position:relative; overflow:hidden;
}}
.stat-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg,#6366f1,#8b5cf6);
}}
.stat-card.green-top::before {{ background:linear-gradient(90deg,#10b981,#34d399); }}
.stat-card.blue-top::before  {{ background:linear-gradient(90deg,#3b82f6,#60a5fa); }}
.stat-label {{ color:{text_muted}; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; margin-bottom:0.5rem; }}
.stat-value {{ color:{text_h}; font-size:1.6rem; font-weight:800; letter-spacing:-0.5px; line-height:1; }}
.stat-value.green {{ color:#34d399; }}
.stat-sub {{ color:{text_dim}; font-size:0.75rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }}

/* TINGKAT BADGE */
.tingkat-badge {{
    display:inline-flex; align-items:center; gap:6px;
    padding:4px 12px; border-radius:100px; font-size:0.72rem; font-weight:700;
    letter-spacing:1.5px; text-transform:uppercase; font-family:'JetBrains Mono',monospace; margin-top:0.4rem;
}}
.tingkat-badge.ritl {{ background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3); color:#a78bfa; }}
.tingkat-badge.rjtl {{ background:rgba(59,130,246,0.15); border:1px solid rgba(59,130,246,0.3); color:#60a5fa; }}

/* FILE BADGE */
.file-badge {{
    display:inline-flex; align-items:center; gap:8px;
    background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2);
    color:#34d399; padding:8px 16px; border-radius:100px;
    font-size:0.8rem; font-weight:600; font-family:'JetBrains Mono',monospace; margin:0.5rem 0;
}}

/* LOG */
.log-title {{ color:{text_muted}; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; }}
.log-item {{
    background:{surface}; border:1px solid {border};
    border-radius:14px; padding:0.9rem 1.1rem; margin-bottom:0.55rem; transition:border-color 0.2s;
}}
.log-item:hover {{ border-color:rgba(99,102,241,0.25); }}
.log-item-name {{
    color:{log_name}; font-size:0.82rem; font-weight:600;
    font-family:'JetBrains Mono',monospace;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    margin-bottom:0.35rem;
}}
.log-item-footer {{
    display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;
    font-family:'JetBrains Mono',monospace;
}}
.log-item-time {{ color:{log_meta}; font-size:0.7rem; }}
.log-item-sep  {{ color:{text_dim}; font-size:0.7rem; }}
.log-item-total {{ color:#34d399; font-size:0.75rem; font-weight:700; }}
.log-item-count {{ color:{text_muted}; font-size:0.7rem; }}
.log-badge {{
    display:inline-flex; align-items:center;
    padding:2px 7px; border-radius:100px; font-size:0.62rem;
    font-weight:700; letter-spacing:1px; font-family:'JetBrains Mono',monospace; vertical-align:middle;
}}
.log-badge.ritl {{ background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3); color:#a78bfa; }}
.log-badge.rjtl {{ background:rgba(59,130,246,0.15); border:1px solid rgba(59,130,246,0.3); color:#60a5fa; }}
.log-badge.other {{ background:rgba(100,116,139,0.12); border:1px solid rgba(100,116,139,0.25); color:#94a3b8; }}
.log-empty {{ color:{text_dim}; font-size:0.85rem; text-align:center; padding:2rem 0; font-style:italic; }}

/* SECTION TITLE */
.section-title {{
    color:{text_muted}; font-size:10px; font-weight:700;
    letter-spacing:2px; text-transform:uppercase; margin-bottom:1rem;
}}

/* MISC */
[data-testid="stAlert"] {{ border-radius:12px !important; padding:0.85rem 1rem !important; }}
hr {{ border-color:{border2} !important; margin:1.5rem 0 !important; }}
[data-testid="stDataFrame"] {{
    border-radius:14px !important; overflow:hidden !important; border:1px solid {border} !important;
}}
h3, .stSubheader {{
    color:{label_col} !important; font-size:0.8rem !important;
    font-weight:700 !important; letter-spacing:2px !important; text-transform:uppercase !important;
}}
</style>
""", unsafe_allow_html=True)


# ── LOGIN ────────────────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

inject_css(st.session_state.dark_mode)

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


# ── HELPERS ──────────────────────────────────────────────────
def ambil_metadata_pdf(pdf_path):
    nama_file, tingkat = "Hasil_Konversi_FPK", "UNKNOWN"
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
            bulan_pola = (r"(JANUARI|FEBRUARI|MARET|APRIL|MEI|JUNI|JULI|"
                          r"AGUSTUS|SEPTEMBER|OKTOBER|NOVEMBER|DESEMBER)")
            m_b = re.search(f"{bulan_pola}\\s+(\\d{{4}})", text, re.IGNORECASE)
            m_t = re.search(r"Tingkat\s+Pelayanan\s*:\s*(RITL|RJTL|RITP|RJTP)", text, re.IGNORECASE)
            if m_b:
                bulan   = m_b.group(1).upper()
                tahun   = m_b.group(2)
                tingkat = m_t.group(1).upper() if m_t else "FPK"
                nama_file = f"FPK_{tingkat}_{bulan}_{tahun}"
            elif m_t:
                tingkat   = m_t.group(1).upper()
                nama_file = f"FPK_{tingkat}"
    except Exception as e:
        print(f"Gagal baca metadata: {e}")
    return nama_file, tingkat


def process_data(pdf_path):
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True,
                              lattice=True, pandas_options={'header': None})
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


def render_result(res, idx=0):
    """Render satu hasil konversi (stats + preview + download)."""
    tingkat = res['tingkat']
    t_lower = tingkat.lower()
    t_label = ("🏥 Rawat Inap (RITL)" if tingkat == "RITL"
               else "🏃 Rawat Jalan (RJTL)" if tingkat == "RJTL" else tingkat)
    total_rp = f"Rp {res['total']:,.0f}".replace(",", ".")

    st.markdown(f'<div class="file-badge">📄 {res["filename"]}</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Jumlah Data</div>
            <div class="stat-value">{res['count']}</div>
            <div class="stat-sub">SEP records</div>
        </div>
        <div class="stat-card green-top">
            <div class="stat-label">Total Nominal</div>
            <div class="stat-value green">{total_rp}</div>
            <div class="stat-sub">total disetujui</div>
        </div>
        <div class="stat-card blue-top" style="grid-column:1/-1;">
            <div class="stat-label">Tingkat Pelayanan</div>
            <div class="tingkat-badge {t_lower}">{t_label}</div>
            <div class="stat-sub" style="margin-top:0.6rem;">terdeteksi otomatis dari PDF</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.subheader("Preview Data")
    df_prev = res['df'].copy()
    df_prev.insert(0, 'No', range(1, 1 + len(df_prev)))
    st.dataframe(df_prev, use_container_width=True, height=280, hide_index=True,
                 column_config={
                     "No": st.column_config.NumberColumn("No", width=50),
                     "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d"),
                 })
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        csv = res['df'].to_csv(index=False).encode('utf-8')
        st.download_button(label="⬇ Download CSV", data=csv,
                           file_name=res['filename'], mime="text/csv",
                           key=f"dl_{idx}")
    with col2:
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("Reset", key=f"reset_{idx}"):
            st.session_state.results = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def build_chart(log_data, dark: bool):
    if not log_data:
        return None
    bulan_order = ["JANUARI","FEBRUARI","MARET","APRIL","MEI","JUNI",
                   "JULI","AGUSTUS","SEPTEMBER","OKTOBER","NOVEMBER","DESEMBER"]
    records = {}
    for item in log_data:
        m = re.search(r'FPK_(?:RITL|RJTL|RITP|RJTP|FPK)?_?([A-Z]+)_(\d{4})', item['nama_file'])
        period = f"{m.group(1)} {m.group(2)}" if m else "Lainnya"
        tkt    = item.get('tingkat', 'FPK')
        key    = (period, tkt)
        records[key] = records.get(key, 0) + item['total']

    if not records:
        return None

    periods = sorted(set(k[0] for k in records),
                     key=lambda x: (x.split()[-1], bulan_order.index(x.split()[0])
                                    if x.split()[0] in bulan_order else 99))
    tingkats = sorted(set(k[1] for k in records))

    colors = {'RITL': '#a78bfa', 'RJTL': '#60a5fa', 'RITP': '#34d399', 'RJTP': '#fb923c'}
    font_col = '#94a3b8' if dark else '#475569'
    grid_col = 'rgba(255,255,255,0.05)' if dark else 'rgba(0,0,0,0.06)'
    paper_bg = 'rgba(0,0,0,0)'

    fig = go.Figure()
    for tkt in tingkats:
        vals = [records.get((p, tkt), 0) / 1_000_000 for p in periods]
        fig.add_trace(go.Bar(
            name=tkt, x=periods, y=vals,
            marker_color=colors.get(tkt, '#818cf8'),
            marker_line_width=0,
            text=[f"Rp {v:.1f}M" if v > 0 else "" for v in vals],
            textposition='outside',
            textfont=dict(size=10, color=font_col),
        ))

    fig.update_layout(
        barmode='group',
        paper_bgcolor=paper_bg,
        plot_bgcolor=paper_bg,
        font=dict(family='Sora', color=font_col, size=11),
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(size=11), bgcolor='rgba(0,0,0,0)'),
        xaxis=dict(tickfont=dict(size=10), gridcolor=grid_col, linecolor='rgba(0,0,0,0)'),
        yaxis=dict(tickformat='.1f', ticksuffix='M', gridcolor=grid_col,
                   linecolor='rgba(0,0,0,0)', tickfont=dict(size=10)),
        height=220,
    )
    return fig


# ══════════════════════════════════════════════════════════════
# HALAMAN UTAMA
# ══════════════════════════════════════════════════════════════

# Theme toggle button (top right)
_, col_toggle = st.columns([6, 1])
with col_toggle:
    icon = st.session_state.get('_toggle_icon', '☀️')
    tip  = st.session_state.get('_toggle_tip', 'Light Mode')
    st.markdown('<div class="toggle-btn">', unsafe_allow_html=True)
    if st.button(icon, help=tip, key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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
    2. Upload satu atau beberapa PDF sekaligus.
    3. Klik **⚡ Proses Sekarang** — nama file otomatis terdeteksi (RITL/RJTL + Bulan + Tahun).
    4. Tiap file tampil di tab masing-masing, download CSV per file.
    """)

uploaded_files = st.file_uploader(
    "Upload PDF FPK (bisa lebih dari satu)",
    type=['pdf'],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if uploaded_files:
    if st.button("⚡ Proses Sekarang"):
        results = []
        errors  = []
        prog    = st.progress(0, text="Memproses file...")
        total_f = len(uploaded_files)

        for i, uf in enumerate(uploaded_files):
            prog.progress((i + 1) / total_f, text=f"Membaca: {uf.name} ({i+1}/{total_f})")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uf.getvalue())
                    tmp_path = tmp.name

                nama, tingkat = ambil_metadata_pdf(tmp_path)
                df_res        = process_data(tmp_path)
                total         = int(df_res['Disetujui'].sum())
                jumlah        = len(df_res)
                filename      = f"{nama}.csv"
                os.unlink(tmp_path)

                results.append({
                    'filename': filename,
                    'df'      : df_res,
                    'total'   : total,
                    'count'   : jumlah,
                    'tingkat' : tingkat,
                })
                save_log({
                    'waktu'    : now_wib().strftime("%d %b %Y, %H:%M") + " WIB",
                    'nama_file': filename,
                    'tingkat'  : tingkat,
                    'jumlah'   : jumlah,
                    'total'    : total,
                })
            except Exception as e:
                errors.append(f"❌ {uf.name}: {e}")

        prog.empty()
        st.session_state.results = results
        if errors:
            for err in errors:
                st.error(err)
        if results:
            st.success(f"✅ {len(results)} file berhasil diproses!")


# ── TAMPILKAN HASIL ──────────────────────────────────────────
if st.session_state.get('results'):
    results = st.session_state.results
    if len(results) == 1:
        render_result(results[0], idx=0)
    else:
        tab_labels = [f"{'🏥' if r['tingkat']=='RITL' else '🏃'} {r['tingkat']}" for r in results]
        tabs = st.tabs(tab_labels)
        for i, (tab, res) in enumerate(zip(tabs, results)):
            with tab:
                render_result(res, idx=i)


# ══════════════════════════════════════════════════════════════
# LOG & REKAP
# ══════════════════════════════════════════════════════════════
st.divider()
log_data = load_log()

# -- Chart --
if log_data:
    st.markdown('<div class="section-title">📊 Rekap Per Periode</div>', unsafe_allow_html=True)
    fig = build_chart(log_data, st.session_state.dark_mode)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.divider()

# -- Log header --
col_title, col_hapus = st.columns([4, 1])
with col_title:
    st.markdown('<div class="log-title">🕓 Riwayat Konversi</div>', unsafe_allow_html=True)
with col_hapus:
    if log_data:
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("Hapus Semua", key="hapus_log"):
            hapus_log()
            st.session_state.results = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if not log_data:
    st.markdown('<div class="log-empty">Belum ada riwayat konversi.</div>', unsafe_allow_html=True)
else:
    html = ""
    for item in log_data:
        tkt      = item.get('tingkat', '')
        t_cls    = tkt.lower() if tkt in ('RITL','RJTL','RITP','RJTP') else 'other'
        badge    = f'<span class="log-badge {t_cls}">{tkt}</span>' if tkt else ''
        total_rp = f"Rp {item['total']:,.0f}".replace(",", ".")
        html += f"""
        <div class="log-item">
            <div class="log-item-name">📄 {item['nama_file']} {badge}</div>
            <div class="log-item-footer">
                <span class="log-item-time">🕓 {item['waktu']}</span>
                <span class="log-item-sep">·</span>
                <span class="log-item-total">{total_rp}</span>
                <span class="log-item-sep">·</span>
                <span class="log-item-count">{item['jumlah']} SEP</span>
            </div>
        </div>"""
    st.markdown(html, unsafe_allow_html=True)
