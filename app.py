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

# ── CONFIG ──────────────────────────────────────────────────
st.set_page_config(page_title="FPK Converter", page_icon="📄", layout="wide")

LOG_FILE  = "/tmp/log_konversi.json"
API_PORT  = 8000
API_URL   = f"http://localhost:{API_PORT}"


def _port_terbuka(port: int) -> bool:
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

def save_log(entry: dict):
    log = load_log()
    log.insert(0, entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log[:100], f, ensure_ascii=False, indent=2)

def hapus_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

def update_log_status(nama_file: str, status: str):
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

def check_pin(input_pin: str):
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

# ── THEME CSS: BENTO GRID MODERN (Figma-grade) ──────────
def inject_css(dark: bool):
    if dark:
        bg          = "#0f0f0f"
        surface     = "#1a1a1a"
        surface2    = "#242424"
        border      = "#2a2a2a"
        text_h      = "#f0f0f0"
        text_body   = "#b0b0b0"
        text_muted  = "#777777"
        text_dim    = "#444444"
        input_bg    = "#111111"
        input_bdr   = "#333333"
        input_col   = "#f0f0f0"
        label_col   = "#aaaaaa"
        shadow      = "rgba(0,0,0,0.5)"
        toggle_icon = "☀️"
        toggle_tip  = "Mode Terang"
        accent      = "#ff6b35"
        accent2     = "#ffd700"
        accent3     = "#00c47a"
        accent_dark = "#ff8a5c"
        bg_grad     = "linear-gradient(145deg, #0f0f0f, #1a1a1a)"
        card_grad   = "linear-gradient(145deg, #1a1a1a, #222222)"
    else:
        bg          = "#f6f4f0"
        surface     = "#ffffff"
        surface2    = "#f0ede8"
        border      = "#e0ddd8"
        text_h      = "#1a1a1a"
        text_body   = "#444444"
        text_muted  = "#888888"
        text_dim    = "#cccccc"
        input_bg    = "#ffffff"
        input_bdr   = "#d0cdc8"
        input_col   = "#1a1a1a"
        label_col   = "#555555"
        shadow      = "rgba(0,0,0,0.06)"
        toggle_icon = "🌙"
        toggle_tip  = "Mode Gelap"
        accent      = "#ff6b35"
        accent2     = "#ffd700"
        accent3     = "#00c47a"
        accent_dark = "#e05a2a"
        bg_grad     = "linear-gradient(145deg, #f6f4f0, #f0ede8)"
        card_grad   = "linear-gradient(145deg, #ffffff, #f8f6f2)"

    st.session_state._toggle_icon = toggle_icon
    st.session_state._toggle_tip  = toggle_tip

    st.markdown(f"""
    <style>
    /* ── FONTS ───────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
    .mono {{ font-family: 'JetBrains Mono', monospace !important; }}

    /* ── GLOBAL ───────────────────────────────────────────── */
    #MainMenu {{visibility:hidden;}}
    footer {{visibility:hidden;}}
    header {{visibility:hidden;}}
    .stApp {{
        background: {bg_grad};
        min-height: 100vh;
    }}
    .block-container {{
        max-width: 1200px !important;
        padding: 2rem 2.5rem !important;
    }}

    /* ── BENTO CARD ──────────────────────────────────────── */
    .bento {{
        background: {card_grad};
        border-radius: 28px;
        padding: 1.8rem 2rem;
        border: 1px solid {border};
        box-shadow: 0 8px 32px {shadow};
        transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
        margin-bottom: 1.25rem;
        backdrop-filter: blur(4px);
    }}
    .bento:hover {{
        transform: translateY(-6px) scale(1.01);
        box-shadow: 0 16px 48px {shadow};
        border-color: {accent};
    }}
    .bento .label {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {text_muted};
        margin-bottom: 0.4rem;
        font-weight: 600;
    }}
    .bento .value {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {text_h};
        line-height: 1.2;
        letter-spacing: -0.02em;
    }}
    .bento .value.accent {{ color: {accent}; }}
    .bento .value.green  {{ color: {accent3}; }}
    .bento .sub {{
        font-size: 0.8rem;
        color: {text_muted};
        margin-top: 0.4rem;
        font-weight: 400;
    }}

    /* ── HEADER ───────────────────────────────────────────── */
    .app-header {{
        text-align: center;
        padding: 1.5rem 0 2.5rem;
    }}
    .app-header .badge {{
        display: inline-block;
        background: {accent};
        color: #fff;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 0.3rem 1.8rem;
        border-radius: 60px;
        margin-bottom: 1rem;
        text-transform: uppercase;
        box-shadow: 0 4px 16px rgba(255,107,53,0.25);
    }}
    .app-header h1 {{
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        color: {text_h} !important;
        letter-spacing: -1.5px;
        margin: 0 !important;
    }}
    .app-header h1 span {{
        color: {accent};
        border-bottom: 4px solid {accent};
        padding-bottom: 4px;
    }}
    .app-header p {{
        color: {text_body};
        font-size: 1.05rem;
        margin-top: 0.5rem;
        font-weight: 400;
    }}

    /* ── BUTTONS ──────────────────────────────────────────── */
    .stButton > button {{
        background: linear-gradient(135deg, {accent}, {accent_dark}) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 60px !important;
        padding: 0.8rem 2.4rem !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 8px 24px rgba(255,107,53,0.35) !important;
        transition: all 0.25s ease !important;
        width: 100% !important;
        letter-spacing: 0.03em;
    }}
    .stButton > button:hover {{
        transform: scale(1.03) translateY(-2px);
        box-shadow: 0 12px 32px rgba(255,107,53,0.45) !important;
    }}
    .stButton > button:active {{
        transform: scale(0.97) translateY(0);
    }}

    .stDownloadButton > button {{
        background: {surface} !important;
        color: {accent3} !important;
        border: 2px solid {accent3} !important;
        border-radius: 60px !important;
        font-weight: 600 !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
    }}
    .stDownloadButton > button:hover {{
        background: {accent3} !important;
        color: #fff !important;
        transform: scale(1.02);
    }}

    /* ── TOP BAR BUTTONS (mini) ──────────────────────────── */
    .top-btn .stButton > button {{
        background: transparent !important;
        color: {text_muted} !important;
        border: 1px solid {border} !important;
        border-radius: 60px !important;
        padding: 0.25rem 1.2rem !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        box-shadow: none !important;
        width: auto !important;
        min-width: 60px;
        height: 34px !important;
        transition: all 0.2s ease;
        letter-spacing: 0.02em;
    }}
    .top-btn .stButton > button:hover {{
        background: {surface2} !important;
        color: {text_h} !important;
        border-color: {accent} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px {shadow} !important;
    }}

    /* ── FILE UPLOADER ────────────────────────────────────── */
    [data-testid="stFileUploader"] section {{
        background: {surface};
        border: 2px dashed {border};
        border-radius: 24px;
        padding: 2.5rem 2rem;
        transition: all 0.25s ease;
    }}
    [data-testid="stFileUploader"] section:hover {{
        border-color: {accent};
        background: {surface2};
        transform: scale(1.01);
    }}
    [data-testid="stFileUploaderDropzoneInstructions"] {{
        color: {text_muted} !important;
        font-size: 0.9rem !important;
    }}
    [data-testid="stFileUploaderDropzoneInstructions"] span {{
        color: {accent} !important;
        font-weight: 600 !important;
    }}

    /* ── TABS ────────────────────────────────────────────── */
    [data-testid="stTabs"] [data-testid="stTab"] {{
        border-radius: 60px !important;
        padding: 0.4rem 1.6rem !important;
        background: transparent !important;
        color: {text_muted} !important;
        border: 1px solid transparent !important;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.2s ease;
    }}
    [data-testid="stTabs"] [data-testid="stTab"]:hover {{
        background: {surface2} !important;
        color: {text_h} !important;
    }}
    [data-testid="stTabs"] [aria-selected="true"] {{
        background: {accent} !important;
        color: #fff !important;
        border-color: {accent} !important;
        box-shadow: 0 4px 16px rgba(255,107,53,0.25);
    }}

    /* ── INPUT (PIN) ──────────────────────────────────────── */
    .stTextInput > div > div > input {{
        background: {input_bg} !important;
        border: 2px solid {input_bdr} !important;
        border-radius: 16px !important;
        color: transparent !important;
        padding: 16px 20px !important;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 2px !important;
        caret-color: {accent} !important;
        font-size: 1rem !important;
        transition: all 0.2s ease;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 4px rgba(255,107,53,0.12) !important;
        outline: none !important;
        color: transparent !important;
    }}
    .stTextInput label {{
        color: {label_col} !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.05em;
    }}

    /* ── HIDE EYE ICON ───────────────────────────────────── */
    [data-testid="stTextInputHideShowButton"],
    button[aria-label="Show password"],
    button[aria-label="Hide password"],
    button[aria-label="Show password text"],
    button[aria-label="Hide password text"],
    [data-baseweb="input"] ~ button,
    [data-baseweb="input"] + div button {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
        pointer-events: none !important;
        position: absolute !important;
        opacity: 0 !important;
    }}

    /* ── DATAFRAME ────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border-radius: 20px !important;
        overflow: hidden !important;
        border: 1px solid {border} !important;
        box-shadow: 0 4px 16px {shadow};
    }}

    /* ── EXPANDER ─────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        border-radius: 20px !important;
        border: 1px solid {border} !important;
        background: {surface} !important;
        overflow: hidden;
        box-shadow: 0 4px 20px {shadow};
        transition: all 0.2s ease;
    }}
    [data-testid="stExpander"]:hover {{
        border-color: {accent};
        box-shadow: 0 8px 28px {shadow};
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 600 !important;
        padding: 0.8rem 1.4rem !important;
        color: {text_h} !important;
    }}

    /* ── ALERT ────────────────────────────────────────────── */
    [data-testid="stAlert"] {{
        border-radius: 16px !important;
        border-left: 5px solid !important;
        padding: 1rem 1.4rem !important;
        box-shadow: 0 2px 12px {shadow};
    }}

    /* ── LOG ITEMS ────────────────────────────────────────── */
    .log-item {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 20px;
        padding: 1rem 1.4rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 16px {shadow};
        transition: all 0.2s ease;
    }}
    .log-item:hover {{
        border-color: {accent};
        box-shadow: 0 4px 24px {shadow};
        transform: translateX(4px);
    }}

    /* ── REKAP CARD ───────────────────────────────────────── */
    .rekap-card {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 20px;
        padding: 1rem 1.5rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
        box-shadow: 0 2px 16px {shadow};
        transition: all 0.2s ease;
    }}
    .rekap-card:hover {{
        border-color: {accent};
        box-shadow: 0 4px 24px {shadow};
        transform: translateX(4px);
    }}

    /* ── STATUS BADGE ─────────────────────────────────────── */
    .status-selesai {{
        background: rgba(0,196,122,0.12);
        border: 1.5px solid {accent3};
        color: {accent3};
        padding: 2px 14px;
        border-radius: 60px;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        font-family: 'JetBrains Mono', monospace;
    }}
    .status-pending {{
        background: rgba(255,215,0,0.10);
        border: 1.5px solid {accent2};
        color: {accent2};
        padding: 2px 14px;
        border-radius: 60px;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* ── TINGKAT BADGE ────────────────────────────────────── */
    .tingkat-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 18px;
        border-radius: 60px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
        border: 1.5px solid;
    }}
    .tingkat-badge.ritl {{
        background: rgba(139,92,246,0.10);
        border-color: #a78bfa;
        color: #a78bfa;
    }}
    .tingkat-badge.rjtl {{
        background: rgba(59,130,246,0.10);
        border-color: #60a5fa;
        color: #60a5fa;
    }}

    /* ── SUSULAN BADGE ────────────────────────────────────── */
    .susulan-badge {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: rgba(255,107,53,0.12);
        border: 1.5px solid {accent};
        color: {accent};
        padding: 2px 14px;
        border-radius: 60px;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* ── SECTION TITLE ────────────────────────────────────── */
    .section-title {{
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: {text_muted};
        margin-bottom: 1.2rem;
        border-left: 4px solid {accent};
        padding-left: 12px;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* ── RADIO (Toggle Susulan) ──────────────────────────── */
    [data-testid="stRadio"] {{
        display: flex;
        gap: 0.5rem;
        background: {surface};
        border-radius: 60px;
        padding: 0.25rem;
        border: 1px solid {border};
        width: fit-content;
        margin: 0.5rem 0 1rem 0;
        box-shadow: 0 2px 8px {shadow};
    }}
    [data-testid="stRadio"] label {{
        border-radius: 60px !important;
        padding: 0.35rem 1.6rem !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        transition: all 0.2s ease;
        cursor: pointer;
        color: {text_muted} !important;
        background: transparent !important;
        border: none !important;
    }}
    [data-testid="stRadio"] label:hover {{
        color: {text_h} !important;
        background: {surface2} !important;
    }}
    [data-testid="stRadio"] label[data-baseweb="radio"] [aria-checked="true"] {{
        background: {accent} !important;
        color: #fff !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(255,107,53,0.25);
    }}
    [data-testid="stRadio"] label[data-baseweb="radio"] [aria-checked="true"]:hover {{
        background: {accent_dark} !important;
    }}

    /* ── TERMINAL ──────────────────────────────────────────── */
    .terminal-container {{
        border-radius: 20px;
        overflow: hidden;
        border: 1px solid {border};
        box-shadow: 0 8px 32px {shadow};
        background: #0d0d0d;
    }}
    .terminal-container .term-header {{
        background: #1a1a1a;
        padding: 0.5rem 1rem;
        border-bottom: 1px solid #2a2a2a;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .terminal-container .term-dot {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
    }}
    .terminal-container .term-dot.red {{ background: #ff5f57; }}
    .terminal-container .term-dot.yellow {{ background: #febc2e; }}
    .terminal-container .term-dot.green {{ background: #28c840; }}
    .terminal-container .term-title {{
        color: #555;
        font-size: 0.65rem;
        font-family: 'JetBrains Mono', monospace;
        margin-left: 8px;
        letter-spacing: 0.05em;
    }}

    /* ── SCROLLBAR ────────────────────────────────────────── */
    ::-webkit-scrollbar {{
        width: 4px;
        height: 4px;
    }}
    ::-webkit-scrollbar-track {{
        background: {surface};
        border-radius: 8px;
    }}
    ::-webkit-scrollbar-thumb {{
        background: {accent};
        border-radius: 8px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {accent_dark};
    }}

    /* ── MISC ────────────────────────────────────────────── */
    hr {{
        border: none !important;
        border-top: 1px solid {border} !important;
        margin: 2rem 0 !important;
        opacity: 0.4;
    }}
    [data-testid="stStatusWidget"] {{
        border-radius: 20px !important;
        border: 1px solid {border} !important;
        background: {surface} !important;
        padding: 1.25rem !important;
        box-shadow: 0 4px 20px {shadow};
    }}
    .stProgress > div > div > div > div {{
        background: {accent} !important;
        border-radius: 60px !important;
    }}
    .stProgress > div > div > div {{
        background: {border} !important;
        border-radius: 60px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── LOGIN ────────────────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

inject_css(st.session_state.dark_mode)

SESSION_TIMEOUT_HOURS = 8
if st.session_state.logged_in:
    login_time = st.session_state.get("login_time")
    if login_time:
        elapsed = (now_wib() - datetime.fromisoformat(login_time)).total_seconds() / 3600
        if elapsed > SESSION_TIMEOUT_HOURS:
            st.session_state.logged_in = False
            st.session_state.login_time = None
            st.rerun()

if not st.session_state.logged_in:
    _dark = st.session_state.get('dark_mode', True)
    _txt  = "#f5f5f5" if _dark else "#0a0a0a"
    _sub  = "#777777" if _dark else "#555555"
    _surf = "#1a1a1a" if _dark else "#ffffff"
    _bdr  = "#2a2a2a" if _dark else "#e0ddd8"
    _shadow = "rgba(0,0,0,0.5)" if _dark else "rgba(0,0,0,0.06)"

    st.markdown(f"""
    <div style="display:flex;justify-content:center;align-items:center;min-height:70vh;padding:1rem;">
        <div style="max-width:420px;width:100%;background:{_surf};border-radius:32px;padding:2.5rem 2rem;border:1px solid {_bdr};box-shadow:0 24px 64px {_shadow};text-align:center;">
            <div style="display:inline-block;background:#ff6b35;color:#fff;padding:0.3rem 1.8rem;border-radius:60px;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;margin-bottom:1.5rem;text-transform:uppercase;">FPK Converter · v1.0</div>
            <h1 style="font-size:2.8rem;font-weight:800;color:{_txt};line-height:1.05;margin:0 0 1rem;letter-spacing:-2px;text-transform:uppercase;">SELAMAT<br><span style="color:#ff6b35;border-bottom:5px solid #ff6b35;padding-bottom:4px;">DATANG</span></h1>
            <p style="color:{_sub};font-size:1rem;margin-bottom:0.3rem;">Aplikasi pribadi konversi data klaim BPJS Kesehatan</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:{_sub};opacity:0.5;letter-spacing:0.08em;margin:1.5rem 0 2rem;">// MASUKKAN PIN UNTUK MELANJUTKAN</p>
    """, unsafe_allow_html=True)

    locked_until = st.session_state.get("locked_until")
    is_locked_now = False
    if locked_until:
        if now_wib() < locked_until:
            is_locked_now = True
            sisa = int((locked_until - now_wib()).total_seconds() // 60) + 1
            st.error(f"🔒 Terlalu banyak percobaan salah. Coba lagi dalam **{sisa} menit**.")
        else:
            st.session_state.attempts = 0
            st.session_state.locked_until = None

    if not is_locked_now:
        pin_input = st.text_input("PIN AKSES", type="password", placeholder="", key="pin_login", autocomplete="off")
        if st.button("Masuk →", key="btn_masuk", use_container_width=True):
            ok, msg = check_pin(pin_input)
            if ok:
                st.session_state.logged_in = True
                st.session_state.login_time = now_wib().isoformat()
                st.rerun()
            else:
                st.error(msg)

    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# ── HELPERS ──────────────────────────────────────────────────
def panggil_api_proses(uf, timeout=60):
    endpoint = f"{API_URL}/api/proses"
    files    = {"file": (uf.name, uf.getvalue(), "application/pdf")}
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
    t_label = ("Rawat Inap (RITL)" if tingkat == "RITL"
               else "Rawat Jalan (RJTL)" if tingkat == "RJTL" else tingkat)
    total_rp = f"Rp {res['total']:,.0f}".replace(",", ".")
    jenis = res.get('jenis', 'Reguler')
    jenis_badge = '<span class="susulan-badge">📌 Susulan</span>' if jenis == "Susulan" else ''

    _dark   = st.session_state.get('dark_mode', True)
    surf    = "#1a1a1a" if _dark else "#ffffff"
    bdr     = "#2a2a2a" if _dark else "#e0ddd8"
    txt_h   = "#f0f0f0" if _dark else "#1a1a1a"
    txt_m   = "#777777" if _dark else "#888888"
    acc     = "#ff6b35"
    grn     = "#00c47a"
    yel     = "#ffd700"
    shadow  = "rgba(0,0,0,0.5)" if _dark else "rgba(0,0,0,0.06)"

    # File badge
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:10px;background:{surf};border:1px solid {bdr};border-radius:60px;padding:6px 20px;font-size:0.8rem;font-weight:600;font-family:JetBrains Mono,monospace;box-shadow:0 2px 16px {shadow};">📄 {res["filename"]} {jenis_badge}</div>',
        unsafe_allow_html=True
    )

    # Stats grid bento
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

    # API debug
    api_log = res.get('api_log')
    if api_log:
        req = api_log['request']
        resp = api_log['response']
        ok = 200 <= resp['status_code'] < 300
        status_color = "#00c47a" if ok else "#f87171"
        with st.expander(f"🔌 API Request/Response — {resp['status_code']} · {resp['latency_ms']} ms"):
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;margin-bottom:0.8rem;">
                <span style="color:#00b0ff;font-weight:700;">POST</span>
                <span style="opacity:0.8;"> {req['url']}</span>
                &nbsp;→&nbsp;
                <span style="color:{status_color};font-weight:700;">{resp['status_code']}</span>
                <span style="opacity:0.6;"> ({resp['latency_ms']} ms)</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("**Request**")
            st.code(json.dumps(req, indent=2, ensure_ascii=False), language="json")
            st.markdown("**Response**")
            st.code(json.dumps(resp, indent=2, ensure_ascii=False), language="json")

    # Preview + JSON
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
        if api_log and 'body' in resp:
            st.json(resp['body'])
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
    """Pure Python terminal animation — ketik No.SEP satu-satu sesuai kecepatan API."""
    acc = "#ff6b35"
    grn = "#00c47a"
    yel = "#ffd700"
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
        <div class="terminal-container">
            <div class="term-header">
                <span class="term-dot red"></span>
                <span class="term-dot yellow"></span>
                <span class="term-dot green"></span>
                <span class="term-title">FPK-CONVERTER — API RESPONSE</span>
            </div>
            <div style="padding:1rem 1.2rem;font-family:'JetBrains Mono',monospace;font-size:0.74rem;height:340px;overflow-y:auto;background:{surf};color:{txt};">
                {inner}
            </div>
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
    proc_ms = payload.get("processing_time_ms", 1000)
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
                     key=lambda x: (x.split()[-1], bulan_order.index(x.split()[0]) if x.split()[0] in bulan_order else 99))
    tingkats = sorted(set(k[1] for k in records))
    rows = []
    for p in periods:
        row = {'Periode': p}
        for tkt in tingkats:
            row[tkt] = round(records.get((p, tkt), 0) / 1_000_000, 2)
        rows.append(row)
    return pd.DataFrame(rows).set_index('Periode')


# ══════════════════════════════════════════════════════════════
# HALAMAN UTAMA — BENTO LAYOUT (tanpa ⚡)
# ══════════════════════════════════════════════════════════════

# Top bar — minimalis, tanpa ikon mencolok
col_sp, col_theme, col_pin, col_logout = st.columns([4, 1, 1, 1])

with col_theme:
    icon = st.session_state.get('_toggle_icon', '☀️')
    st.markdown('<div class="top-btn">', unsafe_allow_html=True)
    if st.button(icon, help=st.session_state.get('_toggle_tip', 'Ganti tema'), key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_pin:
    st.markdown('<div class="top-btn">', unsafe_allow_html=True)
    if st.button("PIN", help="Ganti PIN", key="open_pin"):
        st.session_state.show_pin_form = not st.session_state.get("show_pin_form", False)
    st.markdown('</div>', unsafe_allow_html=True)

with col_logout:
    st.markdown('<div class="top-btn">', unsafe_allow_html=True)
    if st.button("Keluar", help="Logout", key="logout_btn"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("show_pin_form"):
    with st.expander("Ganti PIN", expanded=True):
        st.info("💡 Untuk ganti PIN, ubah nilai **PIN** di **Streamlit Cloud → Settings → Secrets**, lalu klik **Reboot app**.")
        p_lama = st.text_input("PIN Lama", type="password", placeholder="", key="p_lama")
        p_baru = st.text_input("PIN Baru", type="password", placeholder="", key="p_baru")
        p_konfirm = st.text_input("Konfirmasi PIN Baru", type="password", placeholder="", key="p_konfirm")
        if st.button("Simpan PIN Baru", key="save_pin_btn"):
            ok, msg = change_pin(p_lama, p_baru, p_konfirm)
            st.warning(msg) if not ok else st.success(msg)

# Header
st.markdown("""
    <div class="app-header">
        <div class="badge">FPK Converter · v1.0</div>
        <h1>FPK <span>Converter</span></h1>
        <p>Konversi data klaim BPJS Kesehatan ke CSV</p>
    </div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────
tab_pdf, tab_csv = st.tabs(["Konversi PDF → CSV", "Kalkulator CSV"])

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
        # ── PILIHAN JENIS DATA (REGULER / SUSULAN) ──────────
        st.markdown('<div style="display:flex;align-items:center;gap:1rem;margin:0.5rem 0 1rem;">', unsafe_allow_html=True)
        st.markdown('<span style="font-weight:600;font-size:0.85rem;color:#888;">Jenis Data</span>', unsafe_allow_html=True)
        jenis_data = st.radio(
            "",
            ["Reguler", "Susulan"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key="jenis_radio"
        )
        st.markdown('</div>', unsafe_allow_html=True)
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
                    
                    # Jika Susulan, tambahkan _SUSULAN sebelum .csv
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

    # Tampilkan hasil
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
    _grn = "#00c47a"
    _acc = "#ff6b35"

    st.markdown(f"""
    <style>
    .csv-file-row {{
        background: {_surf_c};
        border: 1px solid {_bdr_c};
        border-radius: 20px;
        padding: 0.85rem 1.4rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 16px rgba(0,0,0,0.04);
        font-family: 'JetBrains Mono', monospace;
        transition: all 0.2s ease;
    }}
    .csv-file-row:hover {{
        border-color: {_acc};
        transform: translateX(4px);
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }}
    .csv-grand {{
        background: linear-gradient(135deg, {_acc}, #e05a2a);
        border: none;
        border-radius: 24px;
        padding: 1.25rem 2rem;
        margin-top: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 8px 32px rgba(255,107,53,0.3);
        font-family: 'JetBrains Mono', monospace;
        transition: all 0.2s ease;
    }}
    .csv-grand:hover {{
        transform: scale(1.01);
        box-shadow: 0 12px 40px rgba(255,107,53,0.4);
    }}
    .csv-grand-label {{
        color: #fff; font-size: 0.8rem; font-weight: 700;
        letter-spacing: 0.08em; text-transform: uppercase;
    }}
    .csv-grand-value {{
        color: #fff; font-size: 1.4rem; font-weight: 800;
    }}
    .csv-stat-grid {{
        display: grid; grid-template-columns: 1fr 1fr 1fr;
        gap: 0.75rem; margin: 1rem 0;
    }}
    .csv-stat {{
        background: {_surf_c}; border: 1px solid {_bdr_c};
        border-radius: 20px; padding: 1rem 1.2rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.04);
        font-family: 'JetBrains Mono', monospace;
        transition: all 0.2s ease;
    }}
    .csv-stat:hover {{
        border-color: {_acc};
        transform: translateY(-2px);
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }}
    .csv-stat-label {{
        color: {_mut_c}; font-size: 0.65rem; font-weight: 700;
        letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.3rem;
    }}
    .csv-stat-val {{
        color: {_txt_c}; font-size: 1.2rem; font-weight: 800;
    }}
    .csv-empty-box {{
        border: 2px dashed {_bdr_c};
        background: {_surf_c};
        border-radius: 24px;
        padding: 3rem 2rem;
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
                <div class="csv-grand-label">⚡ Grand Total Disetujui</div>
                <div class="csv-grand-value">{grand_fmt}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="csv-empty-box">
            <div style="font-size:2.5rem;margin-bottom:0.5rem;">📊</div>
            <div style="font-weight:700;font-size:1.1rem;margin-bottom:0.3rem;color:{_txt_c};">Upload file CSV di atas</div>
            <div style="color:{_mut_c};font-size:0.9rem;">Bisa multiple file — format: No.SEP, Disetujui</div>
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
        key=lambda x: (x.split()[-1], bulan_order.index(x.split()[0]) if x.split()[0] in bulan_order else 99),
        reverse=True)

    st.markdown('<div class="section-title">📅 Rekap Per Bulan</div>', unsafe_allow_html=True)
    for p in sorted_periods:
        r = rekap[p]
        total_rp = f"Rp {r['total']:,.0f}".replace(",", ".")
        tkt_str = " · ".join(sorted(t for t in r['tingkats'] if t))
        st.markdown(f"""
        <div class="rekap-card">
            <div><div class="mono" style="font-weight:800;font-size:0.9rem;color:{'#f0f0f0' if st.session_state.dark_mode else '#1a1a1a'};">{p}</div>
            <div style="color:#888;font-size:0.72rem;">{r['konversi']}x konversi · {r['count']} SEP · {tkt_str}</div></div>
            <div style="color:#00c47a;font-weight:800;font-size:0.85rem;font-family:JetBrains Mono,monospace;white-space:nowrap;">{total_rp}</div>
        </div>
        """, unsafe_allow_html=True)
    st.divider()

if log_data:
    st.markdown('<div class="section-title">📊 Rekap Per Periode</div>', unsafe_allow_html=True)
    df_chart = build_chart(log_data)
    if df_chart is not None:
        st.bar_chart(df_chart, use_container_width=True, height=220,
                     color=["#e040fb","#00b0ff","#00c47a","#ff6b35"][:len(df_chart.columns)])
    st.divider()

if log_data:
    total_entri = len(log_data)
    total_selesai = sum(1 for x in log_data if x.get('status') == 'Selesai')
    total_pending = total_entri - total_selesai
    total_nominal = sum(x['total'] for x in log_data)
    nominal_fmt = f"Rp {total_nominal:,.0f}".replace(",", ".")
    dark = st.session_state.dark_mode
    th = '#f0f0f0' if dark else '#1a1a1a'
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:1rem;">
        <div class="bento" style="padding:1rem 1.2rem;"><div class="label">Total Konversi</div><div class="value" style="font-size:1.2rem;">{total_entri}</div></div>
        <div class="bento" style="padding:1rem 1.2rem;"><div class="label">Selesai</div><div class="value" style="font-size:1.2rem;color:#00c47a;">{total_selesai}</div></div>
        <div class="bento" style="padding:1rem 1.2rem;"><div class="label">Pending</div><div class="value" style="font-size:1.2rem;color:#ffd700;">{total_pending}</div></div>
        <div class="bento" style="padding:1rem 1.2rem;"><div class="label">Total Nominal</div><div class="value" style="font-size:1rem;color:#e040fb;white-space:nowrap;">{nominal_fmt}</div></div>
    </div>
    """, unsafe_allow_html=True)

col_title, col_hapus = st.columns([4, 1])
with col_title:
    st.markdown('<div class="section-title">🕓 Riwayat Konversi</div>', unsafe_allow_html=True)
with col_hapus:
    if log_data:
        if st.button("Hapus Semua", key="hapus_log"):
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
        jenis_badge = '<span class="susulan-badge">📌 Susulan</span>' if jenis == "Susulan" else ''
        if status == 'Selesai':
            status_html = '<span class="status-selesai">✓ Selesai</span>'
            footer_extra = f'<span style="color:#888;font-size:0.7rem;">📥 {wkt_sel}</span>' if wkt_sel else ''
        else:
            status_html = '<span class="status-pending">⏳ Belum Diambil</span>'
            footer_extra = ''
        st.markdown(f"""
        <div class="log-item">
            <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:0.3rem;">
                <span style="font-weight:700;font-family:JetBrains Mono,monospace;font-size:0.82rem;color:{'#f0f0f0' if st.session_state.dark_mode else '#1a1a1a'};">📄 {item['nama_file']}</span>
                {badge} {jenis_badge} {status_html}
            </div>
            <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#888;">
                <span>🕓 {item['waktu']}</span>
                <span>·</span>
                <span style="color:#00c47a;font-weight:700;">{total_rp}</span>
                <span>·</span>
                <span>{item['jumlah']} SEP</span>
                {footer_extra}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if status != 'Selesai':
            if st.button("✓ Tandai", key=f"tandai_{i}"):
                update_log_status(item['nama_file'], 'Selesai')
                st.rerun()

# ── FOOTER ───────────────────────────────────────────────────
_dark = st.session_state.get('dark_mode', True)
ft_border = "rgba(255,255,255,0.05)" if _dark else "rgba(0,0,0,0.06)"
ft_dim = "#334155" if _dark else "#94a3b8"
ft_dimmer = "#1e293b" if _dark else "#cbd5e1"
ft_muted = "#475569" if _dark else "#64748b"

st.markdown(f"""
<div style="text-align:center;padding:2.5rem 1rem 1.5rem;margin-top:2.5rem;border-top:1px solid {ft_border};">
    <div style="margin-bottom:1rem;">
        <div style="display:inline-flex;align-items:center;gap:8px;background:#ff6b35;border-radius:60px;padding:0.4rem 2rem;box-shadow:0 4px 16px rgba(255,107,53,0.3);">
            <span style="font-family:JetBrains Mono,monospace;font-size:0.78rem;font-weight:700;color:#fff;letter-spacing:0.08em;">FPK CONVERTER</span>
        </div>
    </div>
    <div style="font-size:0.8rem;color:{ft_muted};font-weight:400;margin-bottom:1.2rem;">Solusi otomasi konversi data klaim BPJS Kesehatan</div>
    <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:1.2rem;">
        <div style="width:6px;height:6px;border-radius:50%;background:#ff6b35;"></div>
        <div style="width:6px;height:6px;border-radius:50%;background:#e040fb;"></div>
        <div style="width:6px;height:6px;border-radius:50%;background:#00c47a;"></div>
        <div style="width:6px;height:6px;border-radius:50%;background:#00b0ff;"></div>
    </div>
    <div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:{ft_dim};margin-bottom:0.4rem;">
        Dikembangkan oleh <strong style="color:#6366f1;">Isfan Fajar Anugrah</strong>
    </div>
    <div style="font-size:0.68rem;color:{ft_dimmer};margin-bottom:0.8rem;">Versi 1.0 · 2025 · All Rights Reserved</div>
    <div style="display:inline-block;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.12);border-radius:60px;padding:4px 20px;">
        <span style="font-size:0.6rem;color:#f87171;">⚠️ Hak Cipta Pribadi — Dilarang digandakan tanpa izin</span>
    </div>
</div>
""", unsafe_allow_html=True)
