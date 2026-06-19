import os
import json
import re
import time
import socket
import threading
import pandas as pd
import streamlit as st
import requests

from datetime import datetime, timezone, timedelta

# ── WARNA ──────────────────────────────────────────────────
PRIMARY_COLOR = "#ff6b35"
SECONDARY     = "#00c47a"
ACCENT        = "#ffd700"

st.set_page_config(page_title="FPK Converter", page_icon="📄", layout="wide")

# ── SESSION STATE ──────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True
if 'attempts' not in st.session_state:
    st.session_state.attempts = 0
if 'locked_until' not in st.session_state:
    st.session_state.locked_until = None
if 'login_time' not in st.session_state:
    st.session_state.login_time = None
if 'show_pin_form' not in st.session_state:
    st.session_state.show_pin_form = False
if 'results' not in st.session_state:
    st.session_state.results = []
if 'errors' not in st.session_state:
    st.session_state.errors = []
if 'show_done' not in st.session_state:
    st.session_state.show_done = False

# ── CONFIG ──────────────────────────────────────────────────
LOG_FILE  = "/tmp/log_konversi.json"
API_PORT  = 8000
API_URL   = f"http://localhost:{API_PORT}"

def _port_terbuka(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("localhost", port)) == 0

@st.cache_resource
def start_api_backend():
    if _port_terbuka(API_PORT):
        return "already_running"
    def _run():
        import uvicorn
        import api as api_module
        uvicorn.run(api_module.app, host="0.0.0.0", port=API_PORT, log_level="warning")
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    for _ in range(20):
        if _port_terbuka(API_PORT):
            return "started"
        time.sleep(0.5)
    return "timeout"

_api_status = start_api_backend()

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

def save_log(entry):
    log = load_log()
    log.insert(0, entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log[:100], f, ensure_ascii=False, indent=2)

def hapus_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

def update_log_status(nama_file, status):
    log = load_log()
    for item in log:
        if item.get('nama_file') == nama_file:
            item['status'] = status
            item['waktu_selesai'] = now_wib().strftime("%d %b %Y, %H:%M") + " WIB" if status == "Selesai" else None
            break
    with open(LOG_FILE, "w") as f:
        json.dump(log[:100], f, ensure_ascii=False, indent=2)

# ── PIN ─────────────────────────────────────────────────────
MAX_ATTEMPT = 5
LOCKOUT_MIN = 5

def get_correct_pin():
    try:
        return str(st.secrets["PIN"])
    except Exception:
        return "1234"

def check_pin(input_pin):
    correct_pin = get_correct_pin()
    locked_until = st.session_state.get("locked_until")
    if locked_until:
        if now_wib() < locked_until:
            sisa = int((locked_until - now_wib()).total_seconds() // 60) + 1
            return False, f"🔒 Terlalu banyak percobaan. Coba lagi dalam **{sisa} menit**."
        else:
            st.session_state.attempts = 0
            st.session_state.locked_until = None
    if input_pin == correct_pin:
        st.session_state.attempts = 0
        st.session_state.locked_until = None
        return True, ""
    else:
        st.session_state.attempts = st.session_state.get("attempts", 0) + 1
        sisa_attempt = MAX_ATTEMPT - st.session_state.attempts
        if st.session_state.attempts >= MAX_ATTEMPT:
            st.session_state.locked_until = now_wib() + timedelta(minutes=LOCKOUT_MIN)
            return False, f"🔒 PIN salah {MAX_ATTEMPT}x. Dikunci selama **{LOCKOUT_MIN} menit**."
        return False, f"❌ PIN salah. Sisa percobaan: **{sisa_attempt}x**."

def change_pin(pin_lama, pin_baru, pin_konfirm):
    correct_pin = get_correct_pin()
    if pin_lama != correct_pin:
        return False, "❌ PIN lama tidak cocok."
    if len(pin_baru) < 4:
        return False, "❌ PIN baru minimal 4 karakter."
    if pin_baru != pin_konfirm:
        return False, "❌ Konfirmasi PIN tidak cocok."
    return False, "⚠️ Untuk ganti PIN, ubah nilai **PIN** di Streamlit Secrets dashboard, lalu reboot app."

# ── CSS ─────────────────────────────────────────────────────
def inject_css(dark):
    if dark:
        bg = "#0a0a0a"
        surface = "#141414"
        border = "#242424"
        text_h = "#f0f0f0"
        text_muted = "#666666"
        input_bg = "#0d0d0d"
        input_bdr = "#2a2a2a"
        shadow = "rgba(0,0,0,0.7)"
        toggle_icon = "☀️"
        toggle_tip = "Mode Terang"
        log_bg = "#141414"
        log_border = "#242424"
        login_bg = "#141414"
        login_border = "#242424"
        login_shadow = "rgba(0,0,0,0.6)"
        login_txt = "#f0f0f0"
        login_sub = "#777777"
        radio_color = "#f0f0f0"
        radio_bg = "#141414"
        radio_border = "#242424"
        hero_bg = "#141414"
        hero_stat = "#1e1e1e"
        hero_stat_b = "#282828"
    else:
        bg = "#f5f4f2"
        surface = "#ffffff"
        border = "#e4e2dd"
        text_h = "#1a1a1a"
        text_muted = "#888888"
        input_bg = "#ffffff"
        input_bdr = "#d5d3ce"
        shadow = "rgba(0,0,0,0.07)"
        toggle_icon = "🌙"
        toggle_tip = "Mode Gelap"
        log_bg = "#ffffff"
        log_border = "#e0ddd8"
        login_bg = "#ffffff"
        login_border = "#e0ddd8"
        login_shadow = "rgba(0,0,0,0.08)"
        login_txt = "#1a1a1a"
        login_sub = "#666666"
        radio_color = "#1a1a1a"
        radio_bg = "#ffffff"
        radio_border = "#e0ddd8"
        hero_bg = "#ffffff"
        hero_stat = "#f5f4f2"
        hero_stat_b = "#e8e6e1"

    st.session_state._toggle_icon = toggle_icon
    st.session_state._toggle_tip = toggle_tip

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
    #MainMenu {{visibility:hidden;}}
    footer {{visibility:hidden;}}
    header {{visibility:hidden;}}
    .stApp {{ background: {bg}; }}
    .block-container {{
        max-width: 560px !important;
        padding: 0 1rem 4rem !important;
        margin: 0 auto !important;
    }}
    .stTextInput input[type="password"],
    input[type="password"] {{
        color: transparent !important;
        caret-color: {PRIMARY_COLOR} !important;
        -webkit-text-security: disc !important;
        text-shadow: none !important;
        background: {input_bg} !important;
    }}
    .stTextInput button[data-testid="stTextInputHideShowButton"],
    button[aria-label="Show password"],
    button[aria-label="Hide password"],
    button[aria-label="Show password text"],
    button[aria-label="Hide password text"],
    [data-baseweb="input"] ~ button,
    [data-baseweb="input"] + div button {{
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    .stRadio > div {{
        display: flex !important;
        gap: 0.75rem !important;
        flex-wrap: wrap !important;
        justify-content: center !important;
    }}
    .stRadio label {{
        background: {radio_bg} !important;
        border: 1.5px solid {radio_border} !important;
        border-radius: 50px !important;
        padding: 0.5rem 1.6rem !important;
        color: {radio_color} !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        transition: all 0.18s ease !important;
        cursor: pointer !important;
    }}
    .stRadio label:hover {{
        border-color: {PRIMARY_COLOR} !important;
    }}
    .stRadio div[role="radiogroup"] label[data-selected="true"] {{
        background: {PRIMARY_COLOR} !important;
        border-color: {PRIMARY_COLOR} !important;
        color: #fff !important;
    }}
    .stRadio div[role="radiogroup"] label[data-selected="true"] [data-testid="stMarkdownContainer"] {{
        color: #fff !important;
    }}
    .stRadio div[role="radiogroup"] label svg {{
        display: none !important;
    }}
    .stRadio div[role="radiogroup"] label {{
        padding-left: 1.6rem !important;
        padding-right: 1.6rem !important;
    }}
    .bento {{
        background: {surface};
        border-radius: 22px;
        padding: 1.25rem 1.5rem;
        border: 1px solid {border};
        box-shadow: 0 4px 20px {shadow};
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }}
    .bento:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 32px {shadow};
    }}
    .bento .label {{
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: {text_muted};
        margin-bottom: 0.3rem;
        font-weight: 700;
    }}
    .bento .value {{
        font-size: 2rem;
        font-weight: 800;
        color: {text_h};
        line-height: 1.2;
    }}
    .bento .value.accent {{ color: {PRIMARY_COLOR}; }}
    .bento .value.green  {{ color: {SECONDARY}; }}
    .bento .sub {{
        font-size: 0.72rem;
        color: {text_muted};
        margin-top: 0.25rem;
    }}
    .hero-card {{
        background: {hero_bg};
        border: 1px solid {border};
        border-radius: 28px;
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.25rem;
        position: relative;
        overflow: hidden;
    }}
    .hero-card::before {{
        content: '';
        position: absolute;
        top: -50px; right: -50px;
        width: 160px; height: 160px;
        background: rgba(255,107,53,0.06);
        border-radius: 50%;
        pointer-events: none;
    }}
    .hero-label {{
        font-size: 0.6rem;
        font-weight: 800;
        letter-spacing: 2.5px;
        color: {text_muted};
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }}
    .hero-title {{
        font-size: 1.75rem;
        font-weight: 900;
        color: {text_h};
        letter-spacing: -1px;
        margin-bottom: 0.15rem;
        line-height: 1.1;
    }}
    .hero-title span {{ color: {PRIMARY_COLOR}; }}
    .hero-sub {{
        font-size: 0.78rem;
        color: {text_muted};
        margin-bottom: 1.1rem;
        font-weight: 400;
    }}
    .hero-stats {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.6rem;
    }}
    .hero-stat {{
        background: {hero_stat};
        border: 1px solid {hero_stat_b};
        border-radius: 16px;
        padding: 0.75rem 0.9rem;
    }}
    .hero-stat-label {{
        font-size: 0.6rem;
        font-weight: 700;
        color: {text_muted};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.2rem;
    }}
    .hero-stat-value {{
        font-size: 1.3rem;
        font-weight: 800;
        color: {text_h};
        line-height: 1.1;
    }}
    .top-nav {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 0 1rem;
    }}
    .top-nav-logo {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: {PRIMARY_COLOR};
        border-radius: 40px;
        padding: 0.3rem 1rem;
    }}
    .top-nav-logo span {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 800;
        color: #fff;
        letter-spacing: 2px;
    }}
    .top-nav-actions {{
        display: flex;
        gap: 0.5rem;
    }}
    .icon-btn-wrap .stButton > button {{
        background: {surface} !important;
        color: {text_muted} !important;
        border: 1px solid {border} !important;
        border-radius: 50px !important;
        padding: 0 !important;
        width: 36px !important;
        height: 36px !important;
        min-width: 36px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    .icon-btn-wrap .stButton > button:hover {{
        border-color: {PRIMARY_COLOR} !important;
        color: {PRIMARY_COLOR} !important;
        background: {surface2} !important;
        transform: none !important;
        box-shadow: none !important;
    }}
    .stButton > button {{
        background: {PRIMARY_COLOR} !important;
        color: #fff !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        box-shadow: 0 4px 18px rgba(255,107,53,0.28) !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        letter-spacing: 0.3px;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 7px 26px rgba(255,107,53,0.38) !important;
    }}
    .stButton > button:active {{
        transform: scale(0.98) !important;
    }}
    .stDownloadButton > button {{
        background: {surface} !important;
        color: {SECONDARY} !important;
        border: 2px solid {SECONDARY} !important;
        border-radius: 50px !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }}
    .stDownloadButton > button:hover {{
        background: {SECONDARY} !important;
        color: #fff !important;
    }}
    [data-testid="stFileUploader"] section {{
        background: {surface};
        border: 2px dashed {border};
        border-radius: 24px;
        padding: 2.5rem 1.5rem;
        transition: border-color 0.2s, background 0.2s;
    }}
    [data-testid="stFileUploader"] section:hover {{
        border-color: {PRIMARY_COLOR};
        background: {surface2};
    }}
    [data-testid="stTabs"] [data-testid="stTab"] {{
        border-radius: 50px !important;
        padding: 0.4rem 1.4rem !important;
        background: transparent !important;
        color: {text_muted} !important;
        border: 1.5px solid {border} !important;
        font-weight: 700;
        font-size: 0.82rem;
        transition: all 0.15s ease;
    }}
    [data-testid="stTabs"] [aria-selected="true"] {{
        background: {PRIMARY_COLOR} !important;
        color: #fff !important;
        border-color: {PRIMARY_COLOR} !important;
    }}
    [data-testid="stTabContent"] {{
        padding-top: 1rem !important;
    }}
    [data-testid="stDataFrame"] {{
        border-radius: 18px !important;
        overflow: hidden !important;
        border: 1px solid {border} !important;
    }}
    [data-testid="stExpander"] {{
        border-radius: 18px !important;
        border: 1px solid {border} !important;
        background: {surface} !important;
        overflow: hidden;
        box-shadow: 0 2px 12px {shadow};
    }}
    [data-testid="stAlert"] {{
        border-radius: 14px !important;
        border-left: 4px solid !important;
    }}
    .log-item {{
        background: {log_bg} !important;
        border: 1px solid {log_border} !important;
        border-radius: 20px !important;
        padding: 1rem 1.25rem !important;
        margin-bottom: 0.65rem !important;
        box-shadow: 0 2px 10px {shadow} !important;
        transition: border-color 0.15s ease, transform 0.15s ease;
    }}
    .log-item:hover {{
        border-color: {PRIMARY_COLOR} !important;
        transform: translateY(-1px);
    }}
    .log-item .log-name {{
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: {text_h};
        margin-bottom: 0.35rem;
        word-break: break-all;
    }}
    .log-item .log-meta {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: {text_muted};
    }}
    .log-item .log-meta .sep {{ color: {text_dim}; }}
    .log-item .log-meta .total {{ color: {SECONDARY}; font-weight: 700; }}
    .log-badge {{
        display: inline-flex;
        align-items: center;
        padding: 2px 10px;
        border-radius: 40px;
        font-size: 0.58rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        font-family: 'JetBrains Mono', monospace;
        border: 1.5px solid;
        background: transparent;
    }}
    .log-badge.ritl {{ border-color: #a78bfa; color: #a78bfa; background: rgba(139,92,246,0.08); }}
    .log-badge.rjtl {{ border-color: #60a5fa; color: #60a5fa; background: rgba(59,130,246,0.08); }}
    .log-badge.other {{ border-color: #94a3b8; color: #94a3b8; background: rgba(148,163,184,0.08); }}
    .log-badge-susulan {{
        display: inline-flex;
        align-items: center;
        padding: 2px 10px;
        border-radius: 40px;
        font-size: 0.58rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        font-family: 'JetBrains Mono', monospace;
        border: 1.5px solid #f59e0b;
        color: #92400e !important;
        background: #fef3c7 !important;
    }}
    .status-selesai {{
        background: rgba(0,196,122,0.1);
        border: 1.5px solid {SECONDARY};
        color: {SECONDARY};
        padding: 2px 12px;
        border-radius: 40px;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        font-family: 'JetBrains Mono', monospace;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .status-pending {{
        background: rgba(255,215,0,0.08);
        border: 1.5px solid {ACCENT};
        color: {ACCENT};
        padding: 2px 12px;
        border-radius: 40px;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        font-family: 'JetBrains Mono', monospace;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .rekap-card {{
        background: {surface} !important;
        border: 1px solid {border} !important;
        border-radius: 18px !important;
        padding: 1rem 1.25rem !important;
        margin-bottom: 0.6rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 1rem !important;
        box-shadow: 0 2px 10px {shadow} !important;
        transition: border-color 0.15s ease;
    }}
    .rekap-card:hover {{ border-color: {PRIMARY_COLOR} !important; }}
    .rekap-card .period {{
        font-weight: 800; font-size: 0.88rem; color: {text_h};
        font-family: 'JetBrains Mono', monospace; margin-bottom: 0.15rem;
    }}
    .rekap-card .meta {{ color: {text_muted}; font-size: 0.68rem; font-family: 'JetBrains Mono', monospace; }}
    .rekap-card .total {{
        color: {SECONDARY}; font-weight: 800; font-size: 0.82rem;
        font-family: 'JetBrains Mono', monospace; white-space: nowrap;
    }}
    .section-title {{
        font-size: 0.65rem;
        font-weight: 800;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: {text_muted};
        margin-bottom: 1rem;
        border-left: 3px solid {PRIMARY_COLOR};
        padding-left: 10px;
        font-family: 'JetBrains Mono', monospace;
    }}
    .summary-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.6rem;
        margin-bottom: 1rem;
    }}
    .summary-grid .bento {{
        padding: 0.9rem 1rem !important;
        margin-bottom: 0 !important;
        background: {surface} !important;
        border: 1px solid {border} !important;
    }}
    .summary-grid .bento .value {{ font-size: 1.2rem !important; }}
    .summary-grid .bento .label {{ font-size: 0.58rem !important; }}
    .tingkat-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 16px;
        border-radius: 40px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
        border: 1.5px solid;
    }}
    .tingkat-badge.ritl {{ background: rgba(139,92,246,0.10); border-color: #a78bfa; color: #a78bfa; }}
    .tingkat-badge.rjtl {{ background: rgba(59,130,246,0.10); border-color: #60a5fa; color: #60a5fa; }}
    hr {{ border-color: {border} !important; margin: 1.5rem 0 !important; opacity: 0.4; }}
    [data-testid="stStatusWidget"] {{
        border-radius: 16px !important;
        border: 1px solid {border} !important;
        background: {surface} !important;
        padding: 0.75rem !important;
    }}
    @media (max-width: 600px) {{
        .block-container {{ padding: 0 0.75rem 4rem !important; }}
        .hero-title {{ font-size: 1.5rem !important; }}
        .bento {{ padding: 1rem 1.1rem !important; }}
        .login-card {{ padding: 2rem 1.25rem 1.75rem !important; }}
        .login-card h2 {{ font-size: 1.3rem !important; }}
        .login-icon-ring {{ width: 60px !important; height: 60px !important; font-size: 1.6rem !important; }}
    }}
    </style>
    """, unsafe_allow_html=True)

# ── LOGIN ────────────────────────────────────────────────────
if st.session_state.logged_in:
    login_time = st.session_state.get("login_time")
    if login_time:
        elapsed = (now_wib() - datetime.fromisoformat(login_time)).total_seconds() / 3600
        if elapsed > 8:
            st.session_state.logged_in = False
            st.session_state.login_time = None
            st.rerun()

if not st.session_state.logged_in:
    inject_css(st.session_state.dark_mode)
    col_empty, col_theme_login = st.columns([8, 1])
    with col_theme_login:
        icon = "☀️" if st.session_state.dark_mode else "🌙"
        if st.button(icon, help="Ganti tema", key="login_theme_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    st.markdown("""
    <div class="login-wrapper">
        <div class="login-card">
            <div class="login-app-badge"><span>FPK CONVERTER</span></div>
            <div class="login-icon-ring">🔐</div>
            <h2>Selamat Datang</h2>
            <p class="sub">Masukkan PIN untuk melanjutkan</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin_input = st.text_input("", type="password", placeholder="", key="pin_login", label_visibility="collapsed", autocomplete="off")
        if st.button("Masuk →", key="btn_masuk", use_container_width=True):
            ok, msg = check_pin(pin_input)
            if ok:
                st.session_state.logged_in = True
                st.session_state.login_time = now_wib().isoformat()
                st.rerun()
            else:
                st.error(msg)
    st.markdown('<div style="text-align:center;margin-top:0.5rem;"><span style="font-family:JetBrains Mono,monospace;font-size:0.62rem;opacity:0.35;">v1.0 · privasi terlindungi</span></div>', unsafe_allow_html=True)
    st.stop()

# ── SETELAH LOGIN ──────────────────────────────────────────
inject_css(st.session_state.dark_mode)

# ── HELPERS ──────────────────────────────────────────────────
def panggil_api_proses(uf, timeout=60):
    endpoint = f"{API_URL}/api/proses"
    files = {"file": (uf.name, uf.getvalue(), "application/pdf")}
    request_meta = {
        "method": "POST",
        "url": endpoint,
        "headers": {"Content-Type": "multipart/form-data"},
        "body": {"file": uf.name, "size_kb": round(len(uf.getvalue()) / 1024, 1)},
    }
    t0 = time.perf_counter()
    try:
        resp = requests.post(endpoint, files=files, timeout=timeout)
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Tidak bisa menghubungi API di {endpoint}.")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"API tidak merespons dalam {timeout} detik.")
    response_meta = {"status_code": resp.status_code, "latency_ms": latency_ms}
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        response_meta["body"] = {"detail": detail}
        raise RuntimeError(detail, request_meta, response_meta)
    payload = resp.json()
    response_meta["body"] = {
        "success": payload.get("success"),
        "filename": payload.get("filename"),
        "tingkat": payload.get("tingkat"),
        "jumlah": payload.get("jumlah"),
        "total": payload.get("total"),
        "duplikat": payload.get("duplikat"),
        "processing_time_ms": payload.get("processing_time_ms"),
        "data": f"[{len(payload.get('data', []))} baris — lihat tab Preview Data]",
    }
    df_res = pd.DataFrame(payload["data"])
    return payload, df_res, request_meta, response_meta

def render_result(res, idx=0):
    tingkat = res['tingkat']
    t_lower = tingkat.lower()
    t_label = ("🏥 Rawat Inap (RITL)" if tingkat == "RITL"
               else "🏃 Rawat Jalan (RJTL)" if tingkat == "RJTL" else tingkat)
    total_rp = f"Rp {res['total']:,.0f}".replace(",", ".")
    jenis = res.get('jenis', 'Reguler')
    jenis_badge = '<span class="log-badge-susulan">📌 Susulan</span>' if jenis == "Susulan" else ""

    _dark   = st.session_state.get('dark_mode', True)
    surf    = "#1a1a1a" if _dark else "#ffffff"
    bdr     = "#2a2a2a" if _dark else "#e0ddd8"
    txt_h   = "#f0f0f0" if _dark else "#1a1a1a"
    txt_m   = "#777777" if _dark else "#888888"
    shadow  = "rgba(0,0,0,0.5)" if _dark else "rgba(0,0,0,0.06)"

    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:8px;background:{surf};border:1px solid {bdr};border-radius:40px;padding:6px 18px;font-size:0.8rem;font-weight:600;font-family:JetBrains Mono,monospace;box-shadow:0 2px 12px {shadow};">📄 {res["filename"]} {jenis_badge}</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="bento"><div class="label">Jumlah Data</div><div class="value">{res["count"]}</div><div class="sub">SEP records</div></div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div class="bento"><div class="label">Total Nominal</div><div class="value green">{total_rp}</div><div class="sub">total disetujui</div></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        f'<div class="bento"><div class="label">Tingkat Pelayanan</div><div class="tingkat-badge {t_lower}">{t_label}</div><div class="sub" style="margin-top:0.5rem;">terdeteksi otomatis dari PDF</div></div>',
        unsafe_allow_html=True
    )

    st.divider()

    api_log = res.get('api_log')
    if api_log:
        req = api_log['request']
        resp_data = api_log['response']
        ok = 200 <= resp_data['status_code'] < 300
        status_color = SECONDARY if ok else "#f87171"
        with st.expander(f"🔌 API Request/Response — {resp_data['status_code']} · {resp_data['latency_ms']} ms"):
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;margin-bottom:0.8rem;">
                <span style="color:#00b0ff;font-weight:700;">POST</span>
                <span style="opacity:0.8;"> {req['url']}</span>
                &nbsp;→&nbsp;
                <span style="color:{status_color};font-weight:700;">{resp_data['status_code']}</span>
                <span style="opacity:0.6;"> ({resp_data['latency_ms']} ms)</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("**Request**")
            st.code(json.dumps(req, indent=2, ensure_ascii=False), language="json")
            st.markdown("**Response**")
            st.code(json.dumps(resp_data, indent=2, ensure_ascii=False), language="json")

    tab_preview, tab_json = st.tabs(["📊 Preview Data", "📦 JSON Mentah"])
    with tab_preview:
        df_prev = res['df'].copy()
        df_prev.insert(0, 'No', range(1, 1 + len(df_prev)))
        df_prev = df_prev[['No', 'No.SEP', 'Disetujui']]
        st.dataframe(
            df_prev,
            use_container_width=True,
            height=280,
            hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", width=60),
                "No.SEP": st.column_config.TextColumn("No.SEP", width=200),
                "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d", width=150),
            }
        )
    with tab_json:
        if api_log and 'body' in resp_data:
            st.json(resp_data['body'])
        else:
            st.info("Tidak ada JSON response.")

    dup = res['df'][res['df']['No.SEP'].duplicated(keep=False)]
    if not dup.empty:
        dup_list = ', '.join(dup['No.SEP'].unique().tolist())
        st.warning(f"⚠️ **{len(dup['No.SEP'].unique())} No.SEP duplikat ditemukan:** {dup_list}")

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        csv = res['df'].to_csv(index=False).encode('utf-8')
        downloaded = st.download_button(
            label="⬇ Download CSV",
            data=csv,
            file_name=res['filename'],
            mime="text/csv",
            key=f"dl_{idx}"
        )
        if downloaded:
            update_log_status(res['filename'], 'Selesai')
            st.rerun()
    with col2:
        if st.button("Reset", key=f"reset_{idx}"):
            st.session_state.results = []
            st.rerun()

def animasi_terminal_proses(uf, dark: bool):
    acc = PRIMARY_COLOR
    grn = SECONDARY
    yel = ACCENT
    dim = "#555555"
    blu = "#00b0ff"
    surf = "#0d0d0d" if dark else "#f5f0e8"
    bdr_pnl = "#444444" if dark else "#333333"
    txt = "#f0f0f0" if dark else "#111111"
    title_c = "#888888" if dark else "#666666"

    term = st.empty()
    def render(lines):
        visible = lines[-40:]
        inner = "".join(f'<div style="margin:0;line-height:1.65;">{l}</div>' for l in visible)
        term.markdown(f"""
        <div style="background:{surf};border:2px solid {bdr_pnl};border-radius:16px;padding:1rem 1.2rem;font-family:'JetBrains Mono',monospace;font-size:0.74rem;box-shadow:0 8px 30px rgba(0,0,0,0.4);height:360px;overflow:hidden;">
            <div style="color:{title_c};font-weight:700;font-size:0.65rem;letter-spacing:2px;border-bottom:1px solid {bdr_pnl};padding-bottom:0.35rem;margin-bottom:0.6rem;">API RESPONSE</div>
            <div style="overflow:hidden;height:300px;">{inner}</div>
        </div>
        """, unsafe_allow_html=True)

    def ln(text, color=None):
        c = color or txt
        return f'<span style="color:{c};">{text}</span>'

    lines = []
    lines.append(ln('$ POST /api/proses → localhost:8000', acc))
    lines.append(ln(f'  file    : {uf.name}', dim))
    lines.append(ln(f'  size    : {round(len(uf.getvalue())/1024, 1)} KB', dim))
    lines.append(ln('  status  : waiting...', dim))
    render(lines)

    payload, df_res, req_meta, resp_meta = panggil_api_proses(uf)

    tingkat = payload.get("tingkat", "FPK")
    jumlah = payload.get("jumlah", 0)
    total = payload.get("total", 0)
    duplikat = payload.get("duplikat", [])
    proc_ms = payload.get("processing_time_ms", 1000) or 1000
    lat_ms = resp_meta.get("latency_ms", 0)
    filename = payload.get("filename", "")
    sep_list = df_res[["No.SEP", "Disetujui"]].to_dict(orient="records")

    lines[-1] = ln(f'  status  : 200 OK — {lat_ms} ms', grn)
    lines.append(ln(f'  tingkat : {tingkat}', grn))
    lines.append(ln(f'  jumlah  : {jumlah} SEP', grn))
    lines.append(ln(f'  proses  : {proc_ms} ms', grn))
    lines.append(ln(''))
    lines.append(ln('{', txt))
    lines.append(ln(f'  "file"    : "{filename}",', yel))
    lines.append(ln(f'  "tingkat" : "{tingkat}",', yel))
    lines.append(ln(f'  "jumlah"  : {jumlah},', yel))
    lines.append(ln('  "data"    : [', txt))
    render(lines)
    time.sleep(0.3)

    row_count = max(1, jumlah)
    delay_sec = (proc_ms / row_count) / 1000
    delay_sec = max(0.01, min(0.5, delay_sec))

    prog = st.empty()

    for i, row in enumerate(sep_list):
        sep = str(row["No.SEP"])
        nom = int(row["Disetujui"])
        comma = "" if i == len(sep_list) - 1 else ","
        lines.append(
            f'<span style="color:{blu};">    {{"No.SEP": "</span>'
            f'<span style="color:{grn};">{sep}</span>'
            f'<span style="color:{blu};">", "Disetujui": </span>'
            f'<span style="color:{yel};">{nom}</span>'
            f'<span style="color:{blu};">}}{comma}</span>'
        )
        render(lines)
        pct = int(((i + 1) / row_count) * 100)
        prog.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;color:{dim};display:flex;align-items:center;gap:10px;margin-top:4px;">'
            f'<span style="color:{grn};font-weight:700;">{i+1:,} / {row_count:,} SEP</span>'
            f'<div style="flex:1;height:3px;background:#222;border-radius:4px;"><div style="width:{pct}%;height:3px;background:{grn};border-radius:4px;"></div></div>'
            f'<span style="color:{acc};font-weight:700;">{pct}%</span></div>',
            unsafe_allow_html=True
        )
        time.sleep(delay_sec)

    prog.empty()
    total_fmt = f"Rp {total:,}".replace(",", ".")
    lines.append(ln('  ],', txt))
    lines.append(ln(f'  "total_disetujui" : {total},', yel))
    if duplikat:
        lines.append(ln(f'  "duplikat"        : {len(duplikat)} SEP,', "#ff4444"))
    lines.append(ln('  "status"          : "DONE ✓"', grn))
    lines.append(ln('}', txt))
    render(lines)
    time.sleep(0.5)
    term.empty()
    return payload, df_res, req_meta, resp_meta

def build_chart(log_data):
    if not log_data:
        return None
    bulan_order = ["JANUARI","FEBRUARI","MARET","APRIL","MEI","JUNI",
                   "JULI","AGUSTUS","SEPTEMBER","OKTOBER","NOVEMBER","DESEMBER"]
    records = {}
    for item in log_data:
        m = re.search(r'FPK_(?:RITL|RJTL|RITP|RJTP|FPK)?_?([A-Z]+)_(\d{4})', item['nama_file'])
        period = f"{m.group(1)} {m.group(2)}" if m else "Lainnya"
        tkt = item.get('tingkat', 'FPK')
        key = (period, tkt)
        records[key] = records.get(key, 0) + item['total']
    if not records:
        return None
    periods = sorted(set(k[0] for k in records),
                     key=lambda x: (x.split()[-1] if len(x.split())>1 else "0000",
                                    bulan_order.index(x.split()[0]) if x.split()[0] in bulan_order else 99))
    tingkats = sorted(set(k[1] for k in records))
    rows = []
    for p in periods:
        row = {'Periode': p}
        for tkt in tingkats:
            row[tkt] = round(records.get((p, tkt), 0) / 1_000_000, 2)
        rows.append(row)
    return pd.DataFrame(rows).set_index('Periode')


# ══════════════════════════════════════════════════════════════
# HALAMAN UTAMA
# ══════════════════════════════════════════════════════════════

log_data_for_hero = load_log()
_total_konversi = len(log_data_for_hero)
_total_selesai = sum(1 for x in log_data_for_hero if x.get('status') == 'Selesai')
_total_pending = _total_konversi - _total_selesai
_total_nominal = sum(x['total'] for x in log_data_for_hero)

# ── Format nominal PENUH ────────────────────────────────────
_nominal_str = f"Rp {_total_nominal:,.0f}".replace(",", ".")

# ── TOP NAV ──────────────────────────────────────────────────
st.markdown("""
<div class="top-nav">
    <div class="top-nav-logo"><span>FPK CONVERTER</span></div>
    <div class="top-nav-actions" id="top-nav-right"></div>
</div>
""", unsafe_allow_html=True)

col_sp_nav, col_theme_nav, col_pin_nav, col_logout_nav = st.columns([5, 1, 1, 1])
with col_theme_nav:
    icon = st.session_state.get('_toggle_icon', '☀️')
    if st.button(icon, help=st.session_state.get('_toggle_tip','Ganti tema'), key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
with col_pin_nav:
    if st.button("PIN", help="Ganti PIN", key="open_pin"):
        st.session_state.show_pin_form = not st.session_state.get("show_pin_form", False)
with col_logout_nav:
    if st.button("KELUAR", help="Keluar", key="logout_btn"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

if st.session_state.get("show_pin_form"):
    with st.expander("Ganti PIN", expanded=True):
        st.info("💡 Untuk ganti PIN, ubah nilai **PIN** di **Streamlit Cloud → Settings → Secrets**, lalu klik **Reboot app**.")
        p_lama = st.text_input("PIN Lama", type="password", placeholder="", key="p_lama")
        p_baru = st.text_input("PIN Baru", type="password", placeholder="", key="p_baru")
        p_konfirm = st.text_input("Konfirmasi PIN Baru", type="password", placeholder="", key="p_konfirm")
        if st.button("Simpan PIN Baru", key="save_pin_btn"):
            ok, msg = change_pin(p_lama, p_baru, p_konfirm)
            st.warning(msg) if not ok else st.success(msg)

# ── HERO CARD ────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-card">
    <div class="hero-label">FPK Converter · v1.0</div>
    <div class="hero-title">FPK <span>Converter</span></div>
    <div class="hero-sub">Konversi data klaim BPJS Kesehatan ke CSV</div>
    <div class="hero-stats">
        <div class="hero-stat">
            <div class="hero-stat-label">Total Konversi</div>
            <div class="hero-stat-value" style="color:{PRIMARY_COLOR};">{_total_konversi}</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-label">Selesai</div>
            <div class="hero-stat-value" style="color:{SECONDARY};">{_total_selesai}</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-label">Pending</div>
            <div class="hero-stat-value" style="color:{ACCENT};">{_total_pending}</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-label">Total Nominal</div>
            <div class="hero-stat-value" style="color:#a78bfa;font-size:1rem;">{_nominal_str}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_pdf, tab_csv = st.tabs(["📄 Konversi PDF → CSV", "🧮 Kalkulator CSV"])

with tab_pdf:
    if _api_status == "timeout":
        st.error("⚠️ Backend API gagal start. Coba refresh halaman.")
    elif _api_status in ("started", "already_running"):
        st.caption(f"🟢 Backend API aktif di `{API_URL}`")

    uploaded_files = st.file_uploader(
        "Upload PDF FPK (bisa lebih dari satu)",
        type=['pdf'],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        jenis_data = st.radio(
            "Jenis Data",
            ["Reguler", "Susulan"],
            index=0,
            horizontal=True,
            help="Pilih 'Susulan' jika file berasal dari folder SUSULAN"
        )
        is_susulan = (jenis_data == "Susulan")

        if st.button("Proses Sekarang", use_container_width=True):
            results = []
            errors = []
            total_f = len(uploaded_files)
            _dark = st.session_state.get('dark_mode', True)

            for i, uf in enumerate(uploaded_files):
                if total_f > 1:
                    st.markdown(
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.75rem;color:#888;margin-bottom:4px;">FILE {i+1}/{total_f} — {uf.name}</div>',
                        unsafe_allow_html=True
                    )
                try:
                    payload, df_res, req_meta, resp_meta = animasi_terminal_proses(uf, dark=_dark)
                    filename = payload['filename']
                    
                    if is_susulan:
                        base, ext = os.path.splitext(filename)
                        filename = f"{base}_SUSULAN{ext}"

                    tingkat = payload['tingkat']
                    total = payload['total']
                    jumlah = payload['jumlah']
                    
                    results.append({
                        'filename': filename,
                        'df': df_res,
                        'total': total,
                        'count': jumlah,
                        'tingkat': tingkat,
                        'jenis': 'Susulan' if is_susulan else 'Reguler',
                        'api_log': {'request': req_meta, 'response': resp_meta},
                    })
                    save_log({
                        'waktu': now_wib().strftime("%d %b %Y, %H:%M") + " WIB",
                        'nama_file': filename,
                        'tingkat': tingkat,
                        'jumlah': jumlah,
                        'total': total,
                        'jenis': 'Susulan' if is_susulan else 'Reguler',
                        'status': 'Belum Diambil',
                        'waktu_selesai': None,
                    })
                except RuntimeError as e:
                    msg = e.args[0] if e.args else str(e)
                    errors.append(f"❌ {uf.name}: {msg}")
                except Exception as e:
                    errors.append(f"❌ {uf.name}: {e}")

            st.session_state.results = results
            st.session_state.errors = errors
            st.session_state.show_done = True
            st.rerun()

    if st.session_state.get('show_done'):
        errors = st.session_state.pop('errors', [])
        results = st.session_state.get('results', [])
        st.session_state.show_done = False
        if errors:
            for err in errors:
                st.error(err)
        if results:
            total_sep = sum(r['count'] for r in results)
            total_nom = sum(r['total'] for r in results)
            nom_fmt = f"Rp {total_nom:,}".replace(",", ".")
            st.success(f"✅ {len(results)} file berhasil diproses — {total_sep} SEP — {nom_fmt}")

    if st.session_state.get('results'):
        results = st.session_state.results
        if len(results) == 1:
            render_result(results[0], idx=0)
        else:
            tab_labels = [f"{'🏥' if r['tingkat']=='RITL' else '🏃'} {r['tingkat']}" for r in results]
            tabs_hasil = st.tabs(tab_labels)
            for i, (tab_h, res) in enumerate(zip(tabs_hasil, results)):
                with tab_h:
                    render_result(res, idx=i)

# ── TAB KALKULATOR CSV ──────────────────────────────────────
with tab_csv:
    _dark_c = st.session_state.get('dark_mode', True)
    _surf_c = "#1a1a1a" if _dark_c else "#ffffff"
    _bdr_c = "#2a2a2a" if _dark_c else "#e0ddd8"
    _txt_c = "#f0f0f0" if _dark_c else "#1a1a1a"
    _mut_c = "#777777" if _dark_c else "#888888"
    _grn = SECONDARY
    _acc = PRIMARY_COLOR

    st.markdown(f"""
    <style>
    .csv-file-row {{
        background: {_surf_c};
        border: 1px solid {_bdr_c};
        border-radius: 16px;
        padding: 0.75rem 1.2rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        font-family: 'JetBrains Mono', monospace;
    }}
    .csv-grand {{
        background: {_acc};
        border: none;
        border-radius: 20px;
        padding: 1.25rem 1.8rem;
        margin-top: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 8px 30px rgba(255,107,53,0.25);
        font-family: 'JetBrains Mono', monospace;
    }}
    .csv-grand-label {{
        color: #fff; font-size: 0.8rem; font-weight: 700;
        letter-spacing: 1.5px; text-transform: uppercase;
    }}
    .csv-grand-value {{
        color: #fff; font-size: 1.3rem; font-weight: 800;
    }}
    .csv-stat-grid {{
        display: grid; grid-template-columns: 1fr 1fr 1fr;
        gap: 0.75rem; margin: 1rem 0;
    }}
    .csv-stat {{
        background: {_surf_c}; border: 1px solid {_bdr_c};
        border-radius: 16px; padding: 1rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        font-family: 'JetBrains Mono', monospace;
    }}
    .csv-stat-label {{
        color: {_mut_c}; font-size: 0.65rem; font-weight: 700;
        letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 0.3rem;
    }}
    .csv-stat-val {{
        color: {_txt_c}; font-size: 1.2rem; font-weight: 800;
    }}
    .csv-empty-box {{
        border: 2px dashed {_bdr_c};
        background: {_surf_c};
        border-radius: 20px;
        padding: 2.5rem;
        text-align: center;
        margin-top: 0.5rem;
        font-family: 'Inter', sans-serif;
    }}
    </style>
    """, unsafe_allow_html=True)

    csv_files = st.file_uploader(
        "Upload CSV hasil konversi (No.SEP + Disetujui)",
        type=["csv"],
        accept_multiple_files=True,
        key="csv_uploader",
        label_visibility="collapsed"
    )

    if csv_files:
        rows_per_file = []
        total_grand = 0
        total_sep = 0
        errors_csv = []
        for cf in csv_files:
            try:
                df_c = pd.read_csv(cf)
                col_disetujui = next((c for c in df_c.columns if 'disetujui' in c.lower()), None)
                if col_disetujui is None:
                    errors_csv.append(f"⚠️ {cf.name}: kolom 'Disetujui' tidak ditemukan.")
                    continue
                df_c[col_disetujui] = pd.to_numeric(
                    df_c[col_disetujui].astype(str).str.replace(r'[^0-9]', '', regex=True),
                    errors='coerce'
                ).fillna(0)
                subtotal = int(df_c[col_disetujui].sum())
                count_sep = len(df_c)
                rows_per_file.append({'nama': cf.name, 'sep': count_sep, 'subtotal': subtotal})
                total_grand += subtotal
                total_sep += count_sep
            except Exception as e:
                errors_csv.append(f"❌ {cf.name}: {e}")
        for err in errors_csv:
            st.warning(err)
        if rows_per_file:
            grand_fmt = f"Rp {total_grand:,.0f}".replace(",", ".")
            sep_fmt = f"{total_sep:,}".replace(",", ".")
            st.markdown(f"""
            <div class="csv-stat-grid">
                <div class="csv-stat"><div class="csv-stat-label">Total File</div><div class="csv-stat-val">{len(rows_per_file)}</div></div>
                <div class="csv-stat"><div class="csv-stat-label">Total SEP</div><div class="csv-stat-val">{sep_fmt}</div></div>
                <div class="csv-stat"><div class="csv-stat-label">Grand Total</div><div class="csv-stat-val" style="color:{_grn};">{grand_fmt}</div></div>
            </div>
            """, unsafe_allow_html=True)
            for r in rows_per_file:
                subtotal_fmt = f"Rp {r['subtotal']:,.0f}".replace(",", ".")
                sep_r_fmt = f"{r['sep']:,}".replace(",", ".")
                st.markdown(f"""
                <div class="csv-file-row">
                    <div><div style="font-weight:700;">📄 {r['nama']}</div><div style="color:{_mut_c};font-size:0.7rem;margin-top:2px;">{sep_r_fmt} SEP</div></div>
                    <div style="color:{_grn};font-weight:800;">{subtotal_fmt}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class="csv-grand">
                <div class="csv-grand-label">Grand Total Disetujui</div>
                <div class="csv-grand-value">{grand_fmt}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="csv-empty-box">
            <div style="font-size:2rem;margin-bottom:0.5rem;">📊</div>
            <div style="font-weight:700;font-size:1rem;margin-bottom:0.3rem;color:{_txt_c};">Upload file CSV di atas</div>
            <div style="color:{_mut_c};font-size:0.85rem;">Bisa multiple file — format: No.SEP, Disetujui</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# LOG & REKAP
# ══════════════════════════════════════════════════════════════
st.divider()
log_data = load_log()

if log_data:
    bulan_order = ["JANUARI","FEBRUARI","MARET","APRIL","MEI","JUNI",
                   "JULI","AGUSTUS","SEPTEMBER","OKTOBER","NOVEMBER","DESEMBER"]
    rekap = {}
    for item in log_data:
        m = re.search(r'FPK_(?:RITL|RJTL|RITP|RJTP|FPK)?_?([A-Z]+)_(\d{4})', item['nama_file'])
        period = f"{m.group(1)} {m.group(2)}" if m else "Lainnya"
        if period not in rekap:
            rekap[period] = {'total': 0, 'count': 0, 'konversi': 0, 'tingkats': set()}
        rekap[period]['total'] += item['total']
        rekap[period]['count'] += item['jumlah']
        rekap[period]['konversi'] += 1
        rekap[period]['tingkats'].add(item.get('tingkat', ''))

    sorted_periods = sorted(rekap.keys(),
        key=lambda x: (x.split()[-1] if len(x.split())>1 else "0000",
                       bulan_order.index(x.split()[0]) if x.split()[0] in bulan_order else 99),
        reverse=True)

    st.markdown('<div class="section-title">📅 Rekap Per Bulan</div>', unsafe_allow_html=True)
    for p in sorted_periods:
        r = rekap[p]
        total_rp = f"Rp {r['total']:,.0f}".replace(",", ".")
        tkt_str = " · ".join(sorted(t for t in r['tingkats'] if t))
        st.markdown(f"""
        <div class="rekap-card">
            <div>
                <div class="period">{p}</div>
                <div class="meta">{r['konversi']}x konversi · {r['count']} SEP · {tkt_str}</div>
            </div>
            <div class="total">{total_rp}</div>
        </div>
        """, unsafe_allow_html=True)
    st.divider()

if log_data:
    st.markdown('<div class="section-title">📊 Rekap Per Periode</div>', unsafe_allow_html=True)
    df_chart = build_chart(log_data)
    if df_chart is not None:
        st.bar_chart(df_chart, use_container_width=True, height=220,
                     color=["#e040fb","#00b0ff", SECONDARY, PRIMARY_COLOR][:len(df_chart.columns)])
    st.divider()

if log_data:
    total_entri = len(log_data)
    total_selesai = sum(1 for x in log_data if x.get('status') == 'Selesai')
    total_pending = total_entri - total_selesai
    total_nominal = sum(x['total'] for x in log_data)
    nominal_fmt = f"Rp {total_nominal:,.0f}".replace(",", ".")

col_title, col_hapus = st.columns([4, 1])
with col_title:
    st.markdown('<div class="section-title">🕓 Riwayat Konversi</div>', unsafe_allow_html=True)
with col_hapus:
    if log_data:
        if st.button("Hapus", key="hapus_log"):
            hapus_log()
            st.session_state.results = []
            st.rerun()

if not log_data:
    st.markdown('<div style="text-align:center;padding:2rem 0;color:#888;font-style:italic;">Belum ada riwayat konversi.</div>', unsafe_allow_html=True)
else:
    for i, item in enumerate(log_data):
        tkt = item.get('tingkat', '')
        t_cls = tkt.lower() if tkt in ('RITL','RJTL','RITP','RJTP') else 'other'
        badge = f'<span class="log-badge {t_cls}">{tkt}</span>' if tkt else ''
        total_rp = f"Rp {item['total']:,.0f}".replace(",", ".")
        status = item.get('status', 'Belum Diambil')
        wkt_sel = item.get('waktu_selesai')
        jenis = item.get('jenis', 'Reguler')
        jenis_badge = '<span class="log-badge-susulan">📌 Susulan</span>' if jenis == "Susulan" else ""
        if status == 'Selesai':
            status_html = '<span class="status-selesai">✓ Selesai</span>'
            footer_extra = f'<span style="color:#888;font-size:0.68rem;">📥 {wkt_sel}</span>' if wkt_sel else ''
        else:
            status_html = '<span class="status-pending">⏳ Belum Diambil</span>'
            footer_extra = ''
        # ── BUAT HTML UTUH ──────────────────────────────────
        html = f'''
        <div class="log-item">
            <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:0.35rem;">
                <span class="log-name">📄 {item['nama_file']}</span>
                {badge}
                {jenis_badge}
                {status_html}
            </div>
            <div class="log-meta">
                <span>🕓 {item['waktu']}</span>
                <span class="sep">·</span>
                <span class="total">{total_rp}</span>
                <span class="sep">·</span>
                <span class="count">{item['jumlah']} SEP</span>
                {footer_extra}
            </div>
        </div>
        '''
        st.markdown(html, unsafe_allow_html=True)
        if status != 'Selesai':
            if st.button("✓ Tandai Selesai", key=f"tandai_{i}"):
                update_log_status(item['nama_file'], 'Selesai')
                st.rerun()

# ── FOOTER ───────────────────────────────────────────────────
_dark_ft = st.session_state.get('dark_mode', True)
_ft_border = "rgba(255,255,255,0.05)" if _dark_ft else "rgba(0,0,0,0.05)"
_ft_txt1 = "#888" if _dark_ft else "#555"
_ft_txt2 = "#666" if _dark_ft else "#999"
st.markdown(f"""
<div style="text-align:center;padding:1.5rem 0 0.5rem;margin-top:1.5rem;border-top:1px solid {_ft_border};">
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:{_ft_txt1};margin-bottom:0.25rem;">
        Dikembangkan oleh <strong style="color:#6366f1;">Isfan Fajar Anugrah</strong>
    </div>
    <div style="font-size:0.6rem;color:{_ft_txt2};">Versi 1.0 · 2025 · All Rights Reserved</div>
    <div style="display:inline-block;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.1);border-radius:40px;padding:3px 14px;margin-top:0.5rem;">
        <span style="font-size:0.58rem;color:#f87171;">⚠️ Hak Cipta Pribadi — Dilarang digandakan tanpa izin</span>
    </div>
</div>
""", unsafe_allow_html=True)
