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
st.set_page_config(page_title="FPK Converter", page_icon="⚡", layout="centered")

LOG_FILE  = "/tmp/log_konversi.json"
API_PORT  = 8000
API_URL   = f"http://localhost:{API_PORT}"


def _port_terbuka(port: int) -> bool:
    """Cek apakah ada proses yang sudah listen di port ini."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("localhost", port)) == 0


@st.cache_resource
def start_api_backend():
    """
    Menjalankan api.py (FastAPI/uvicorn) sebagai background thread
    di dalam proses Streamlit yang sama. Ini membuat app.py bisa
    benar-benar mengirim HTTP request ke API meski hanya dideploy
    sebagai satu app di Streamlit Cloud (tanpa server terpisah
    seperti Railway).

    @st.cache_resource memastikan ini hanya dijalankan SEKALI per
    siklus hidup container, bukan setiap kali Streamlit rerun.
    """
    if _port_terbuka(API_PORT):
        # Sudah ada server jalan di port ini (misal saat development
        # lokal kamu sengaja jalankan `uvicorn api:app` manual)
        return "already_running"

    def _run():
        import uvicorn
        import api as api_module
        uvicorn.run(api_module.app, host="0.0.0.0", port=API_PORT, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    # Tunggu sampai API benar-benar siap menerima request (maks ~10 detik)
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
            item['status']        = status
            item['waktu_selesai'] = now_wib().strftime("%d %b %Y, %H:%M") + " WIB" if status == "Selesai" else None
            break
    with open(LOG_FILE, "w") as f:
        json.dump(log[:100], f, ensure_ascii=False, indent=2)

# ── PIN (via st.secrets) ─────────────────────────────────────
MAX_ATTEMPT = 5
LOCKOUT_MIN = 5

def get_correct_pin():
    try:
        return str(st.secrets["PIN"])
    except Exception:
        return "1234"

def check_pin(input_pin: str):
    correct_pin = get_correct_pin()

    # Cek lockout dari session_state
    locked_until = st.session_state.get("locked_until")
    if locked_until:
        if now_wib() < locked_until:
            sisa = int((locked_until - now_wib()).total_seconds() // 60) + 1
            return False, f"🔒 Terlalu banyak percobaan. Coba lagi dalam **{sisa} menit**."
        else:
            st.session_state.attempts    = 0
            st.session_state.locked_until = None

    if input_pin == correct_pin:
        st.session_state.attempts    = 0
        st.session_state.locked_until = None
        return True, ""
    else:
        st.session_state.attempts = st.session_state.get("attempts", 0) + 1
        sisa_attempt = MAX_ATTEMPT - st.session_state.attempts
        if st.session_state.attempts >= MAX_ATTEMPT:
            st.session_state.locked_until = now_wib() + timedelta(minutes=LOCKOUT_MIN)
            return False, f"🔒 PIN salah {MAX_ATTEMPT}x. Dikunci selama **{LOCKOUT_MIN} menit**."
        return False, f"❌ PIN salah. Sisa percobaan: **{sisa_attempt}x**."

def change_pin(pin_lama: str, pin_baru: str, pin_konfirm: str):
    correct_pin = get_correct_pin()
    if pin_lama != correct_pin:
        return False, "❌ PIN lama tidak cocok."
    if len(pin_baru) < 4:
        return False, "❌ PIN baru minimal 4 karakter."
    if pin_baru != pin_konfirm:
        return False, "❌ Konfirmasi PIN tidak cocok."
    return False, "⚠️ Untuk ganti PIN, ubah nilai **PIN** di Streamlit Secrets dashboard, lalu reboot app."

# ── THEME CSS ────────────────────────────────────────────────
def inject_css(dark: bool):
    if dark:
        bg          = "#0d0d0d"
        surface     = "#1a1a1a"
        surface2    = "#222222"
        border      = "#333333"
        border2     = "#2a2a2a"
        text_h      = "#f0f0f0"
        text_body   = "#aaaaaa"
        text_muted  = "#888888"
        text_dim    = "#444444"
        input_bg    = "#111111"
        input_bdr   = "#3a3a3a"
        input_col   = "#f0f0f0"
        label_col   = "#bbbbbb"
        exp_text    = "#aaaaaa"
        exp_detail  = "#888888"
        log_name    = "#dddddd"
        log_meta    = "#666666"
        toggle_icon = "☀️"
        toggle_tip  = "Light Mode"
        accent      = "#ff6b35"
        accent2     = "#ffd700"
        accent3     = "#00e5a0"
        shadow_col  = "#ff6b35"
    else:
        bg          = "#fffaf0"
        surface     = "#ffffff"
        surface2    = "#f5f0e8"
        border      = "#111111"
        border2     = "#333333"
        text_h      = "#111111"
        text_body   = "#333333"
        text_muted  = "#555555"
        text_dim    = "#999999"
        input_bg    = "#ffffff"
        input_bdr   = "#111111"
        input_col   = "#111111"
        label_col   = "#333333"
        exp_text    = "#333333"
        exp_detail  = "#555555"
        log_name    = "#111111"
        log_meta    = "#777777"
        toggle_icon = "🌙"
        toggle_tip  = "Dark Mode"
        accent      = "#ff6b35"
        accent2     = "#ffd700"
        accent3     = "#00c47a"
        shadow_col  = "#111111"

    st.session_state._toggle_icon = toggle_icon
    st.session_state._toggle_tip  = toggle_tip

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Space Grotesk', sans-serif !important; }}
#MainMenu {{visibility:hidden;}} footer {{visibility:hidden;}} header {{visibility:hidden;}}

.stApp {{ background-color: {bg}; }}
.block-container {{ padding-top: 1.5rem; max-width: 680px; }}

/* HEADER */
.app-header {{ text-align:center; padding:2.5rem 2rem 1.5rem; margin-bottom:0.5rem; }}
.app-header .badge {{
    display:inline-block;
    background:{accent}; border:3px solid {text_h};
    color:{text_h}; font-size:11px; font-weight:800; letter-spacing:2px;
    text-transform:uppercase; padding:6px 16px; border-radius:0px; margin-bottom:1.2rem;
    box-shadow: 3px 3px 0px {text_h};
    font-family:'JetBrains Mono',monospace;
}}
.app-header h1 {{
    font-size:3rem !important; font-weight:800 !important; color:{text_h} !important;
    line-height:1.1 !important; margin:0 !important; letter-spacing:-1.5px;
    text-transform:uppercase;
}}
.app-header h1 span {{
    color:{accent};
    text-decoration: underline;
    text-decoration-thickness: 4px;
    text-underline-offset: 4px;
}}
.app-header p {{ color:{text_body}; font-size:0.95rem; margin-top:0.8rem; font-weight:500; }}

/* EXPANDER */
[data-testid="stExpander"] {{
    background:{surface} !important; border:3px solid {border} !important;
    border-radius:0px !important; overflow:hidden !important; margin-bottom:1rem !important;
    box-shadow: 4px 4px 0px {shadow_col} !important;
}}
[data-testid="stExpander"] summary {{
    color:{exp_text} !important; font-size:0.85rem !important;
    font-weight:700 !important; padding:1rem 1.2rem !important;
    text-transform:uppercase !important; letter-spacing:1px !important;
}}
[data-testid="stExpanderDetails"] {{
    padding:0 1.2rem 1.2rem !important; color:{exp_detail} !important;
    font-size:0.9rem !important; line-height:1.7 !important;
}}

/* TABS */
[data-testid="stTabs"] [data-testid="stTab"] {{
    background:{surface} !important; border:2px solid {border} !important;
    border-radius:0px !important; color:{text_muted} !important;
    font-size:0.8rem !important; font-weight:700 !important;
    text-transform:uppercase !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background:{accent} !important;
    border-color:{text_h} !important; color:{text_h} !important;
}}

/* INPUT */
.stTextInput > div > div > input {{
    background:{input_bg} !important; border:3px solid {input_bdr} !important;
    border-radius:0px !important; color:{input_col} !important;
    padding:14px 18px !important; font-size:0.95rem !important;
    font-family:'JetBrains Mono',monospace !important;
    letter-spacing:4px !important; transition:border-color 0.15s !important;
    box-shadow: none !important;
}}
.stTextInput > div > div > input:focus {{
    border-color:{accent} !important;
    box-shadow: 4px 4px 0px {accent} !important;
    outline: none !important;
}}
.stTextInput label {{
    color:{label_col} !important; font-size:0.8rem !important;
    font-weight:700 !important; letter-spacing:2px !important;
    text-transform:uppercase !important; font-family:'JetBrains Mono',monospace !important;
}}

/* HIDE EYE ICON */
input[type="password"]::-ms-reveal,
input[type="password"]::-ms-clear {{
    display:none !important; visibility:hidden !important; pointer-events:none !important;
}}
[data-testid="stTextInputHideShowButton"],
button[data-testid="stTextInputHideShowButton"],
[data-baseweb="input"] ~ button,
[data-baseweb="input"] + div button,
button[aria-label="Show password text"],
button[aria-label="Hide password text"],
button[aria-label="Show password"],
button[aria-label="Hide password"] {{
    display:none !important; visibility:hidden !important;
    width:0 !important; height:0 !important; padding:0 !important;
    margin:0 !important; overflow:hidden !important;
    pointer-events:none !important; position:absolute !important; opacity:0 !important;
}}
input[type="password"],
input[type="password"]:focus,
input[type="password"]:active {{
    -webkit-text-security: none !important;
    color: transparent !important;
    caret-color: {accent} !important;
}}

/* FILE UPLOADER */
[data-testid="stFileUploader"] {{ position:relative !important; }}
[data-testid="stFileUploader"] section {{
    background:{surface} !important; border:3px dashed {border} !important;
    border-radius:0px !important; padding:2rem 1.5rem !important;
    transition:border-color 0.2s !important; position:relative !important; overflow:visible !important;
}}
[data-testid="stFileUploader"] section:hover {{
    border-color:{accent} !important; background:{surface2} !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    display:flex !important; flex-direction:column !important; align-items:center !important; gap:0.75rem !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] {{ color:{text_body} !important; text-align:center !important; }}
[data-testid="stFileUploaderDropzoneInstructions"] span {{ color:{accent} !important; font-weight:700 !important; }}
[data-testid="stFileUploader"] section button {{
    background:{accent} !important; border:3px solid {text_h} !important;
    color:{text_h} !important; border-radius:0px !important; padding:8px 20px !important;
    font-size:0.85rem !important; font-weight:800 !important; z-index:1 !important; position:relative !important;
    box-shadow: 3px 3px 0px {text_h} !important; text-transform:uppercase !important;
}}

/* BUTTONS */
.stButton > button {{
    background:{accent} !important;
    color:{text_h} !important; border:3px solid {text_h} !important; border-radius:0px !important;
    height:52px !important; font-size:0.9rem !important; font-weight:800 !important;
    transition:all 0.1s ease !important; box-shadow:4px 4px 0px {text_h} !important;
    width:100% !important; text-transform:uppercase !important; letter-spacing:1px !important;
    font-family:'Space Grotesk',sans-serif !important;
}}
.stButton > button:hover {{
    transform:translate(-2px,-2px) !important; box-shadow:6px 6px 0px {text_h} !important;
    filter:brightness(1.08) !important;
}}
.stButton > button:active {{
    transform:translate(2px,2px) !important; box-shadow:1px 1px 0px {text_h} !important;
}}
.reset-btn .stButton > button {{
    background:{surface} !important; border:3px solid {border} !important;
    color:{text_muted} !important; box-shadow:3px 3px 0px {border} !important; height:52px !important;
}}
.reset-btn .stButton > button:hover {{
    background:{surface2} !important; color:{text_h} !important;
    box-shadow:5px 5px 0px {border} !important;
}}
.toggle-btn .stButton > button {{
    background:{surface} !important; border:2px solid {border} !important;
    color:{text_muted} !important; box-shadow:2px 2px 0px {border} !important;
    height:36px !important; font-size:0.78rem !important; width:auto !important;
    padding:0 14px !important; border-radius:0px !important;
}}
.toggle-btn .stButton > button:hover {{
    background:{accent} !important; border-color:{text_h} !important; color:{text_h} !important;
}}
.danger-btn .stButton > button {{
    background:transparent !important; border:2px solid #cc2222 !important;
    color:#ff4444 !important; box-shadow:2px 2px 0px #cc2222 !important;
    height:38px !important; font-size:0.78rem !important;
}}
.danger-btn .stButton > button:hover {{
    background:#cc2222 !important; border-color:#cc2222 !important; color:#ffffff !important;
}}
.selesai-btn .stButton > button {{
    background:{surface} !important; border:2px solid {accent3} !important;
    color:{accent3} !important; box-shadow:2px 2px 0px {accent3} !important;
    height:34px !important; font-size:0.75rem !important;
}}
.selesai-btn .stButton > button:hover {{
    background:{accent3} !important; color:{text_h} !important;
}}

/* DOWNLOAD */
.stDownloadButton > button {{
    background:{surface} !important; border:3px solid {accent3} !important;
    color:{accent3} !important; box-shadow:4px 4px 0px {accent3} !important;
    border-radius:0px !important; height:52px !important; font-size:0.9rem !important;
    font-weight:800 !important; width:100% !important; transition:all 0.1s !important;
    text-transform:uppercase !important; letter-spacing:1px !important;
}}
.stDownloadButton > button:hover {{
    background:{accent3} !important; color:{text_h} !important;
    box-shadow:6px 6px 0px {border} !important; transform:translate(-2px,-2px) !important;
}}

/* STATS */
.stats-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin:1.5rem 0; }}
.stat-card {{
    background:{surface}; border:3px solid {border};
    border-radius:0px; padding:1.5rem; position:relative; overflow:hidden;
    box-shadow: 4px 4px 0px {shadow_col};
}}
.stat-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:5px; background:{accent};
}}
.stat-card.green-top::before {{ background:{accent3}; }}
.stat-card.blue-top::before  {{ background:{accent2}; }}
.stat-label {{ color:{text_muted}; font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; margin-bottom:0.5rem; font-family:'JetBrains Mono',monospace; }}
.stat-value {{ color:{text_h}; font-size:1.6rem; font-weight:800; letter-spacing:-0.5px; line-height:1; }}
.stat-value.green {{ color:{accent3}; }}
.stat-sub {{ color:{text_dim}; font-size:0.72rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }}

/* TINGKAT BADGE */
.tingkat-badge {{
    display:inline-flex; align-items:center; gap:6px;
    padding:4px 12px; border-radius:0px; font-size:0.72rem; font-weight:800;
    letter-spacing:2px; text-transform:uppercase; font-family:'JetBrains Mono',monospace; margin-top:0.4rem;
    border:2px solid;
}}
.tingkat-badge.ritl {{ background:rgba(139,92,246,0.15); border-color:#a78bfa; color:#a78bfa; }}
.tingkat-badge.rjtl {{ background:rgba(59,130,246,0.15); border-color:#60a5fa; color:#60a5fa; }}

/* FILE BADGE */
.file-badge {{
    display:inline-flex; align-items:center; gap:8px;
    background:{surface}; border:2px solid {accent3};
    color:{accent3}; padding:8px 16px; border-radius:0px;
    font-size:0.8rem; font-weight:700; font-family:'JetBrains Mono',monospace; margin:0.5rem 0;
    box-shadow: 3px 3px 0px {accent3};
}}

/* LOG */
.log-title {{ color:{text_muted}; font-size:10px; font-weight:800; letter-spacing:3px; text-transform:uppercase; font-family:'JetBrains Mono',monospace; }}
.log-item {{
    background:{surface}; border:2px solid {border};
    border-radius:0px; padding:0.9rem 1.1rem; margin-bottom:0.55rem;
    transition:border-color 0.15s; box-shadow:3px 3px 0px {border2};
}}
.log-item:hover {{ border-color:{accent}; box-shadow:3px 3px 0px {accent}; }}
.log-item-name {{
    color:{log_name}; font-size:0.82rem; font-weight:700;
    font-family:'JetBrains Mono',monospace;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:0.35rem;
}}
.log-item-footer {{
    display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; font-family:'JetBrains Mono',monospace;
}}
.log-item-time  {{ color:{log_meta}; font-size:0.7rem; }}
.log-item-sep   {{ color:{text_dim}; font-size:0.7rem; }}
.log-item-total {{ color:{accent3}; font-size:0.75rem; font-weight:700; }}
.log-item-count {{ color:{text_muted}; font-size:0.7rem; }}
.log-badge {{
    display:inline-flex; align-items:center;
    padding:2px 7px; border-radius:0px; font-size:0.62rem;
    font-weight:800; letter-spacing:1px; font-family:'JetBrains Mono',monospace; vertical-align:middle;
    border:1.5px solid;
}}
.log-badge.ritl  {{ background:rgba(139,92,246,0.1); border-color:#a78bfa; color:#a78bfa; }}
.log-badge.rjtl  {{ background:rgba(59,130,246,0.1); border-color:#60a5fa; color:#60a5fa; }}
.log-badge.other {{ background:rgba(100,116,139,0.1); border-color:#94a3b8; color:#94a3b8; }}

/* REKAP CARD */
.rekap-card {{
    background:{surface}; border:2px solid {border};
    border-radius:0px; padding:1rem 1.25rem; margin-bottom:0.55rem;
    display:flex; align-items:center; justify-content:space-between; gap:1rem;
    box-shadow: 3px 3px 0px {border2}; transition:all 0.15s;
}}
.rekap-card:hover {{ border-color:{accent}; box-shadow:3px 3px 0px {accent}; }}
.rekap-period {{
    color:{text_h}; font-size:0.9rem; font-weight:800;
    font-family:'JetBrains Mono',monospace; margin-bottom:0.25rem; text-transform:uppercase;
}}
.rekap-meta  {{ color:{text_muted}; font-size:0.72rem; font-family:'JetBrains Mono',monospace; }}
.rekap-total {{
    color:{accent3}; font-size:0.85rem; font-weight:800;
    font-family:'JetBrains Mono',monospace; white-space:nowrap; text-align:right;
}}

/* STATUS BADGE */
.status-selesai {{
    display:inline-flex; align-items:center; gap:4px;
    background:rgba(0,200,122,0.1); border:2px solid {accent3};
    color:{accent3}; padding:2px 10px; border-radius:0px;
    font-size:0.65rem; font-weight:800; letter-spacing:1px; font-family:'JetBrains Mono',monospace;
}}
.status-pending {{
    display:inline-flex; align-items:center; gap:4px;
    background:rgba(255,215,0,0.08); border:2px solid {accent2};
    color:{accent2}; padding:2px 10px; border-radius:0px;
    font-size:0.65rem; font-weight:800; letter-spacing:1px; font-family:'JetBrains Mono',monospace;
}}

.log-empty {{ color:{text_dim}; font-size:0.85rem; text-align:center; padding:2rem 0; font-style:italic; }}

/* SECTION TITLE */
.section-title {{
    color:{text_muted}; font-size:10px; font-weight:800;
    letter-spacing:3px; text-transform:uppercase; margin-bottom:1rem;
    font-family:'JetBrains Mono',monospace;
    border-left: 4px solid {accent}; padding-left: 10px;
}}

/* MISC */
[data-testid="stAlert"] {{ border-radius:0px !important; padding:0.85rem 1rem !important; border-left:4px solid !important; }}
hr {{ border-color:{border2} !important; margin:1.5rem 0 !important; }}
[data-testid="stDataFrame"] {{
    border-radius:0px !important; overflow:hidden !important; border:2px solid {border} !important;
    box-shadow: 4px 4px 0px {border} !important;
}}
h3, .stSubheader {{
    color:{label_col} !important; font-size:0.8rem !important;
    font-weight:800 !important; letter-spacing:2px !important; text-transform:uppercase !important;
    font-family:'JetBrains Mono',monospace !important;
}}
</style>
<script>
(function() {{
  function removeEyeIcons() {{
    var selectors = [
      '[data-testid="stTextInputHideShowButton"]',
      'button[aria-label="Show password text"]',
      'button[aria-label="Hide password text"]',
      'button[aria-label="Show password"]',
      'button[aria-label="Hide password"]'
    ];
    selectors.forEach(function(sel) {{
      document.querySelectorAll(sel).forEach(function(el) {{
        el.style.setProperty('display', 'none', 'important');
        el.style.setProperty('visibility', 'hidden', 'important');
        el.style.setProperty('width', '0', 'important');
        el.style.setProperty('height', '0', 'important');
        el.style.setProperty('opacity', '0', 'important');
        el.style.setProperty('pointer-events', 'none', 'important');
        el.style.setProperty('position', 'absolute', 'important');
      }});
    }});
    document.querySelectorAll('input[type="password"]').forEach(function(el) {{
      el.style.setProperty('color', 'transparent', 'important');
    }});
  }}
  removeEyeIcons();
  var observer = new MutationObserver(function() {{ removeEyeIcons(); }});
  observer.observe(document.body, {{ childList: true, subtree: true }});
}})();
</script>
""", unsafe_allow_html=True)

# ── LOGIN ────────────────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

inject_css(st.session_state.dark_mode)

# Session timeout — 8 jam
SESSION_TIMEOUT_HOURS = 8
if st.session_state.logged_in:
    login_time = st.session_state.get("login_time")
    if login_time:
        elapsed = (now_wib() - datetime.fromisoformat(login_time)).total_seconds() / 3600
        if elapsed > SESSION_TIMEOUT_HOURS:
            st.session_state.logged_in  = False
            st.session_state.login_time = None
            st.rerun()

if not st.session_state.logged_in:
    _dark   = st.session_state.get('dark_mode', True)
    _bg     = "#0a0a0a" if _dark else "#fafaf7"
    _txt    = "#f5f5f5" if _dark else "#0a0a0a"
    _sub    = "#777777" if _dark else "#555555"
    _surf   = "#141414" if _dark else "#ffffff"
    _bdr    = "#2a2a2a" if _dark else "#111111"

    st.markdown(f"""
        <div style="text-align:center; padding:3rem 2rem 0.5rem;">
            <div style="display:inline-flex; align-items:center; gap:8px;
                background:#ff6b35; border:3px solid {_txt};
                padding:6px 20px; margin-bottom:1.8rem;
                box-shadow:5px 5px 0px {_txt};">
                <span style="font-size:14px;">⚡</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:11px;
                    font-weight:800; color:{_txt}; letter-spacing:2px;">
                    FPK CONVERTER &nbsp;·&nbsp; V1.0
                </span>
            </div>
            <h1 style="font-family:'Space Grotesk',sans-serif; font-size:3.4rem; font-weight:800;
                color:{_txt}; line-height:1.05; margin:0 0 1rem; letter-spacing:-2.5px;
                text-transform:uppercase;">
                SELAMAT<br>
                <span style="color:#ff6b35; text-decoration:underline;
                    text-decoration-thickness:6px; text-underline-offset:6px;">DATANG</span>
            </h1>
            <p style="font-family:'Space Grotesk',sans-serif; color:{_sub};
                font-size:0.95rem; margin-bottom:0.3rem; font-weight:500;">
                Aplikasi pribadi konversi data klaim BPJS Kesehatan
            </p>
            <p style="font-family:'JetBrains Mono',monospace; font-size:0.72rem;
                color:{_sub}; opacity:0.5; letter-spacing:1.5px; margin-bottom:2rem;">
                // MASUKKAN PIN UNTUK MELANJUTKAN
            </p>
        </div>
        <div style="display:flex; justify-content:center; gap:1rem; margin-bottom:1rem; flex-wrap:wrap;">
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Multi-file upload</span>
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Auto-detect RITL / RJTL</span>
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Cek duplikat SEP</span>
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Riwayat & rekap</span>
        </div>
    """, unsafe_allow_html=True)

    # Cek lockout
    locked_until = st.session_state.get("locked_until")
    is_locked_now = False
    if locked_until:
        if now_wib() < locked_until:
            is_locked_now = True
            sisa = int((locked_until - now_wib()).total_seconds() // 60) + 1
            st.error(f"🔒 Terlalu banyak percobaan salah. Coba lagi dalam **{sisa} menit**.")
        else:
            st.session_state.attempts    = 0
            st.session_state.locked_until = None

    if not is_locked_now:
        pin_input = st.text_input("PIN AKSES", type="password", placeholder="", key="pin_login")
        if st.button("Masuk →", key="btn_masuk"):
            ok, msg = check_pin(pin_input)
            if ok:
                st.session_state.logged_in  = True
                st.session_state.login_time = now_wib().isoformat()
                st.rerun()
            else:
                st.error(msg)
    st.stop()


# ── HELPERS ──────────────────────────────────────────────────
def panggil_api_proses(uf, timeout=60):
    """
    Kirim file PDF ke backend API (/api/proses) dan kembalikan
    hasil parsing beserta detail request/response untuk ditampilkan
    di panel debug (ala Postman).
    """
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
        raise RuntimeError(
            f"Tidak bisa menghubungi API di {endpoint}. "
            f"Pastikan backend sudah berjalan (uvicorn api:app --port 8000)."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"API tidak merespons dalam {timeout} detik.")

    response_meta = {
        "status_code": resp.status_code,
        "latency_ms": latency_ms,
    }

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        response_meta["body"] = {"detail": detail}
        raise RuntimeError(detail, request_meta, response_meta)

    payload = resp.json()
    response_meta["body"] = {
        "success"           : payload.get("success"),
        "filename"          : payload.get("filename"),
        "original_filename" : payload.get("original_filename"),
        "tingkat"           : payload.get("tingkat"),
        "jumlah"            : payload.get("jumlah"),
        "total"             : payload.get("total"),
        "duplikat"          : payload.get("duplikat"),
        "processing_time_ms": payload.get("processing_time_ms"),
        "file_index"        : payload.get("file_index"),
        "total_files"       : payload.get("total_files"),
        "data"              : f"[{len(payload.get('data', []))} baris — lihat tab Preview Data]",
    }

    df_res = pd.DataFrame(payload["data"])
    return payload, df_res, request_meta, response_meta


def render_result(res, idx=0):
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
            <div class="stat-value orange">{res['count']}</div>
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

    # ── PANEL DEBUG API (ala Postman) ──────────────────────────
    api_log = res.get('api_log')
    if api_log:
        req  = api_log['request']
        resp = api_log['response']
        ok   = 200 <= resp['status_code'] < 300
        status_color = "#00e5a0" if ok else "#f87171"
        with st.expander(f"🔌 API Request/Response — {resp['status_code']} · {resp['latency_ms']} ms"):
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; margin-bottom:0.8rem;">
                <span style="color:#00b0ff; font-weight:700;">POST</span>
                <span style="opacity:0.8;"> {req['url']}</span>
                &nbsp;→&nbsp;
                <span style="color:{status_color}; font-weight:700;">{resp['status_code']}</span>
                <span style="opacity:0.6;"> ({resp['latency_ms']} ms)</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("**Request**")
            st.code(json.dumps(req, indent=2, ensure_ascii=False), language="json")
            st.markdown("**Response**")
            st.code(json.dumps(resp, indent=2, ensure_ascii=False), language="json")

    st.subheader("Preview Data")
    df_prev = res['df'].copy()
    df_prev.insert(0, 'No', range(1, 1 + len(df_prev)))
    # Eksplisit reorder: No → No.SEP → Disetujui (Nominal Cair)
    df_prev = df_prev[['No', 'No.SEP', 'Disetujui']]
    st.dataframe(df_prev, use_container_width=True, height=280, hide_index=True,
                 column_config={
                     "No"       : st.column_config.NumberColumn("No",           width=60),
                     "No.SEP"   : st.column_config.TextColumn("No.SEP"),
                     "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d"),
                 })

    dup = res['df'][res['df']['No.SEP'].duplicated(keep=False)]
    if not dup.empty:
        dup_list = ', '.join(dup['No.SEP'].unique().tolist())
        st.warning(f"⚠️ **{len(dup['No.SEP'].unique())} No.SEP duplikat ditemukan:** {dup_list}")

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        csv        = res['df'].to_csv(index=False).encode('utf-8')
        downloaded = st.download_button(label="⬇ Download CSV", data=csv,
                                        file_name=res['filename'], mime="text/csv",
                                        key=f"dl_{idx}")
        if downloaded:
            update_log_status(res['filename'], 'Selesai')
            st.rerun()
    with col2:
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("Reset", key=f"reset_{idx}"):
            st.session_state.results = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def animasi_terminal_proses(uf, dark: bool):
    """
    Step 1: Tampil spinner Python sambil nunggu API
    Step 2: Setelah API balik, inject data JSON ke JS typewriter
            yang ketik karakter per karakter kayak CMD beneran.
    Return: (payload, df_res, req_meta, resp_meta)
    """
    import streamlit.components.v1 as components

    surf  = "#0d0d0d" if dark else "#f5f0e8"
    bdr   = "#333333" if dark else "#222222"

    # ── Step 1: Spinner Python sambil panggil API ───────────────
    placeholder = st.empty()
    placeholder.markdown(f"""
    <div style="background:{surf}; border:2px solid {bdr}; padding:1rem 1.4rem;
        font-family:'JetBrains Mono',monospace; font-size:0.75rem;
        box-shadow:4px 4px 0 {bdr}; color:#888;">
        <span style="color:#ff6b35; font-weight:700; letter-spacing:2px;
            font-size:0.68rem;">⚡ FPK CONVERTER — API</span><br><br>
        <span style="color:#888;">$ POST /api/proses → localhost:8000</span><br>
        <span style="color:#555;">  menunggu response</span>
        <span style="color:#ff6b35; animation:blink 1s infinite;">█</span>
    </div>
    <style>@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}</style>
    """, unsafe_allow_html=True)

    # ── Panggil API beneran ─────────────────────────────────────
    payload, df_res, req_meta, resp_meta = panggil_api_proses(uf)

    placeholder.empty()

    tingkat  = payload.get("tingkat", "FPK")
    jumlah   = payload.get("jumlah", 0)
    total    = payload.get("total", 0)
    duplikat = payload.get("duplikat", [])
    lat_ms   = resp_meta.get("latency_ms", 0)
    proc_ms  = payload.get("processing_time_ms", 0)
    filename = payload.get("filename", "")
    sep_list = df_res[["No.SEP", "Disetujui"]].to_dict(orient="records")

    # ── Bangun string JSON yang akan diketik JS ─────────────────
    # Format: baris per baris biar keliatan natural
    total_fmt = f"Rp {total:,}".replace(",", ".")
    dup_str   = json.dumps(duplikat) if duplikat else "[]"

    # Bangun baris data — tiap row satu string
    data_lines = []
    for i, row in enumerate(sep_list):
        sep = row["No.SEP"]
        nom = int(row["Disetujui"])
        comma = "," if i < len(sep_list) - 1 else ""
        data_lines.append(
            f'    {{"No.SEP": "{sep}", "Disetujui": {nom}}}{comma}'
        )
    data_block = "\n".join(data_lines)

    json_text = f"""{{
  "request": {{
    "method": "POST",
    "endpoint": "/api/proses",
    "file": "{uf.name}",
    "size_kb": {round(len(uf.getvalue())/1024, 1)}
  }},
  "response": {{
    "status": 200,
    "latency_ms": {lat_ms},
    "processing_time_ms": {proc_ms},
    "tingkat": "{tingkat}",
    "jumlah": {jumlah},
    "filename": "{filename}",
    "duplikat": {dup_str},
    "total_disetujui": {total},
    "data": [
{data_block}
    ]
  }},
  "status": "DONE ✓"
}}"""

    # Kecepatan: makin banyak data makin cepet per karakter
    # Target: animasi data selesai ~5-8 detik
    total_chars = len(json_text)
    # delay per char dalam ms
    if total_chars < 500:
        char_delay = 18
    elif total_chars < 2000:
        char_delay = 8
    elif total_chars < 10000:
        char_delay = 3
    elif total_chars < 50000:
        char_delay = 1
    else:
        char_delay = 0.3   # super cepet buat data ribuan

    # Escape untuk JS string (newline → \n, quote → \")
    json_escaped = json_text.replace("\\", "\\\\").replace("`", "\\`")

    # ── Render JS Typewriter ────────────────────────────────────
    html_code = f"""
<div style="
    background:#0d0d0d; border:2px solid #333; padding:0;
    font-family:'JetBrains Mono',monospace; font-size:0.73rem;
    box-shadow:4px 4px 0 #333; overflow:hidden;
">
    <!-- Header bar -->
    <div style="background:#1a1a1a; border-bottom:1px solid #333;
        padding:0.5rem 1rem; display:flex; align-items:center; gap:8px;">
        <div style="width:10px;height:10px;border-radius:50%;background:#ff5f57;"></div>
        <div style="width:10px;height:10px;border-radius:50%;background:#febc2e;"></div>
        <div style="width:10px;height:10px;border-radius:50%;background:#28c840;"></div>
        <span style="color:#555; font-size:0.65rem; margin-left:8px; letter-spacing:1px;">
            FPK-CONVERTER — API RESPONSE
        </span>
    </div>

    <!-- Terminal body -->
    <div id="terminal" style="
        padding:1rem 1.2rem; height:380px; overflow-y:auto;
        color:#f0f0f0; white-space:pre; line-height:1.7;
        scrollbar-width:thin; scrollbar-color:#333 #0d0d0d;
    "><span id="output"></span><span id="cursor" style="
        color:#ff6b35; animation:blink 0.7s step-end infinite;">█</span></div>

    <!-- Progress bar -->
    <div style="background:#111; border-top:1px solid #222; padding:0.5rem 1rem;
        display:flex; align-items:center; gap:10px;">
        <span style="color:#555; font-size:0.65rem;">TYPING</span>
        <div style="flex:1; height:3px; background:#222;">
            <div id="pbar" style="height:3px; background:#ff6b35; width:0%;
                transition:width 0.1s;"></div>
        </div>
        <span id="pct" style="color:#ff6b35; font-size:0.65rem; font-weight:700;">0%</span>
    </div>
</div>

<style>
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0}} }}
#terminal::-webkit-scrollbar {{ width:4px; }}
#terminal::-webkit-scrollbar-track {{ background:#0d0d0d; }}
#terminal::-webkit-scrollbar-thumb {{ background:#333; }}
</style>

<script>
const RAW = `{json_escaped}`;
const DELAY = {char_delay};

// Syntax highlight tiap karakter
function colorChar(ch, idx, text) {{
    return ch;
}}

// Warnain output dengan regex setelah selesai
function highlight(str) {{
    return str
        .replace(/("No\.SEP")/g, '<span style="color:#00b0ff;">$1</span>')
        .replace(/("Disetujui")/g, '<span style="color:#00e5a0;">$1</span>')
        .replace(/("request"|"response"|"status"|"method"|"endpoint"|"file"|"size_kb"|"latency_ms"|"processing_time_ms"|"tingkat"|"jumlah"|"filename"|"duplikat"|"total_disetujui"|"data")/g,
            '<span style="color:#e040fb;">$1</span>')
        .replace(/:\s*(\d+\.?\d*)/g, ': <span style="color:#ffd700;">$1</span>')
        .replace(/:\s*"([^"]*)"/g, ': <span style="color:#ff6b35;">"$1"</span>')
        .replace(/(DONE ✓)/g, '<span style="color:#00e5a0; font-weight:700;">$1</span>')
        .replace(/(\[\]|\[)/g, '<span style="color:#888;">$1</span>')
        .replace(/(\])/g, '<span style="color:#888;">$1</span>');
}}

const out    = document.getElementById('output');
const cursor = document.getElementById('cursor');
const pbar   = document.getElementById('pbar');
const pct    = document.getElementById('pct');
const term   = document.getElementById('terminal');
const total  = RAW.length;

let i = 0;
let buf = '';

function typeNext() {{
    if (i >= total) {{
        // Selesai — highlight syntax, hilangkan cursor kedip
        out.innerHTML = highlight(buf);
        cursor.style.display = 'none';
        pbar.style.width = '100%';
        pct.textContent = '100%';
        pct.style.color = '#00e5a0';
        document.getElementById('pbar').style.background = '#00e5a0';
        // Banner DONE muncul setelah animasi selesai
        const banner = document.createElement('div');
        banner.style.cssText = 'background:#00e5a0;color:#0d0d0d;font-family:JetBrains Mono,monospace;font-size:0.72rem;font-weight:800;letter-spacing:2px;padding:0.5rem 1.2rem;text-align:center;border-top:2px solid #333;';
        banner.textContent = '\u2713 KONVERSI SELESAI — DATA SIAP DIDOWNLOAD';
        document.getElementById('terminal').parentElement.appendChild(banner);
        return;
    }}

    // Batch per tick biar smooth di data besar
    const batchSize = DELAY <= 1 ? 8 : 1;
    for (let b = 0; b < batchSize && i < total; b++) {{
        buf += RAW[i];
        i++;
    }}

    out.textContent = buf;
    term.scrollTop = term.scrollHeight;

    const p = Math.round((i / total) * 100);
    pbar.style.width = p + '%';
    pct.textContent = p + '%';

    setTimeout(typeNext, DELAY);
}}

typeNext();
</script>
"""

    components.html(html_code, height=460, scrolling=False)

    # Hitung waktu tunggu exact sesuai JS:
    # JS ngetik batch_size karakter per setTimeout(DELAY ms)
    batch_size    = 8 if char_delay <= 1 else 1
    total_ticks   = total_chars / batch_size
    estimated_sec = (total_ticks * char_delay) / 1000
    # Clamp + buffer 1.5 detik biar animasi highlight selesai dulu
    estimated_sec = max(1.0, min(estimated_sec, 14.0)) + 1.5
    time.sleep(estimated_sec)

    return payload, df_res, req_meta, resp_meta


def build_chart(log_data):
    if not log_data:
        return None
    bulan_order = ["JANUARI","FEBRUARI","MARET","APRIL","MEI","JUNI",
                   "JULI","AGUSTUS","SEPTEMBER","OKTOBER","NOVEMBER","DESEMBER"]
    records = {}
    for item in log_data:
        m      = re.search(r'FPK_(?:RITL|RJTL|RITP|RJTP|FPK)?_?([A-Z]+)_(\d{4})', item['nama_file'])
        period = f"{m.group(1)} {m.group(2)}" if m else "Lainnya"
        tkt    = item.get('tingkat', 'FPK')
        key    = (period, tkt)
        records[key] = records.get(key, 0) + item['total']
    if not records:
        return None
    periods  = sorted(set(k[0] for k in records),
                      key=lambda x: (x.split()[-1], bulan_order.index(x.split()[0])
                                     if x.split()[0] in bulan_order else 99))
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

# Top bar
col_sp, col_theme, col_pin, col_logout = st.columns([4, 1, 1, 1])

with col_theme:
    icon = st.session_state.get('_toggle_icon', '☀️')
    st.markdown('<div class="toggle-btn">', unsafe_allow_html=True)
    if st.button(icon, help="Ganti tema", key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_pin:
    st.markdown('<div class="toggle-btn">', unsafe_allow_html=True)
    if st.button("🔑", help="Ganti PIN", key="open_pin"):
        st.session_state.show_pin_form = not st.session_state.get("show_pin_form", False)
    st.markdown('</div>', unsafe_allow_html=True)

with col_logout:
    st.markdown('<div class="toggle-btn">', unsafe_allow_html=True)
    if st.button("🚪", help="Logout", key="logout_btn"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Form ganti PIN
if st.session_state.get("show_pin_form"):
    with st.expander("🔑 Ganti PIN", expanded=True):
        st.info("💡 Untuk ganti PIN, ubah nilai **PIN** di **Streamlit Cloud → Settings → Secrets**, lalu klik **Reboot app**.")
        p_lama    = st.text_input("PIN Lama",            type="password", placeholder="", key="p_lama")
        p_baru    = st.text_input("PIN Baru",            type="password", placeholder="", key="p_baru")
        p_konfirm = st.text_input("Konfirmasi PIN Baru", type="password", placeholder="", key="p_konfirm")
        if st.button("Simpan PIN Baru", key="save_pin_btn"):
            ok, msg = change_pin(p_lama, p_baru, p_konfirm)
            st.warning(msg) if not ok else st.success(msg)

# Header
st.markdown("""
    <div class="app-header">
        <div class="badge">⚡ Converter Tools &nbsp;·&nbsp; v1.0</div>
        <h1>FPK <span>Converter</span></h1>
        <p>Otomasi konversi data klaim BPJS Kesehatan ke CSV siap pakai</p>
        <div style="display:flex; justify-content:center; gap:1rem; margin-top:1rem; flex-wrap:wrap;">
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Multi-file upload</span>
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Auto-detect RITL / RJTL</span>
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Cek duplikat SEP</span>
            <span style="font-size:0.72rem; color:#475569; display:flex; align-items:center; gap:4px;">✦ Riwayat & rekap</span>
        </div>
    </div>
""", unsafe_allow_html=True)

with st.expander("ℹ️ Fitur & Cara Penggunaan"):
    st.markdown("""
    ### ⚡ Konversi PDF → CSV
    - Upload satu atau beberapa PDF FPK BPJS sekaligus (maks 200MB/file)
    - Klik **⚡ Proses Sekarang** — sistem otomatis membaca isi PDF
    - Nama file CSV terdeteksi otomatis dari PDF: **FPK_RITL_MARET_2026.csv** atau **FPK_RJTL_MARET_2026.csv**
    - Kalau upload lebih dari 1 PDF, hasil tiap file tampil di **tab terpisah**
    - Output CSV hanya berisi 2 kolom: **No.SEP** dan **Disetujui** — siap upload ke SIMRS

    ### ⚠️ Cek Duplikat No.SEP
    - Setelah diproses, sistem otomatis cek apakah ada **No.SEP yang muncul lebih dari sekali**
    - Kalau ada duplikat, muncul warning kuning beserta daftar No.SEP yang bermasalah

    ### 📥 Download & Status
    - Klik **⬇ Download CSV** untuk mengunduh hasil konversi
    - Status di log otomatis berubah jadi **✓ Selesai** setelah download
    - Kalau belum didownload, status **⏳ Belum Diambil**
    - Bisa juga tandai manual lewat tombol **✓ Tandai** di log

    ### 🔌 API Request/Response
    - Proses konversi sebenarnya menembak **backend API** (FastAPI) yang berjalan di proses yang sama, lewat HTTP request asli — bukan simulasi
    - Klik expander **🔌 API Request/Response** untuk lihat detail request yang dikirim, status code, dan response JSON dari API — mirip tampilan di Postman
    - Latency (waktu tempuh request) ditampilkan dalam milidetik

    ### 📅 Rekap Per Bulan
    - Di bawah chart ada rekap ringkas per periode
    - Tiap baris tampil: berapa kali konversi, total SEP, tingkat pelayanan, dan total nominal

    ### 📊 Chart Rekap Periode
    - Bar chart otomatis terbentuk dari riwayat konversi
    - Warna berbeda per tingkat: **ungu = RITL**, **biru = RJTL**
    - Sumbu Y dalam satuan juta rupiah (M)

    ### 🕓 Riwayat Konversi
    - Semua aktivitas konversi tersimpan otomatis (maks 100 entri)
    - Tampil: nama file, badge RITL/RJTL, waktu konversi, total nominal, jumlah SEP, status
    - Summary di atas log: total konversi, selesai, pending, total nominal kumulatif
    - Klik **Hapus Semua** untuk reset seluruh riwayat

    ### 🔑 Keamanan
    - **PIN tidak terlihat** saat diketik (seperti terminal Linux)
    - **Salah PIN 5x** → aplikasi dikunci otomatis 5 menit
    - **Session timeout 8 jam** → otomatis logout jika tidak aktif
    - **Ganti PIN** lewat Streamlit Cloud → Settings → Secrets → ubah nilai PIN → Reboot app
    - **Logout** lewat tombol 🚪 di pojok kanan atas

    ### 🌙 Tema
    - Toggle **dark/light mode** lewat tombol ☀️/🌙 di pojok kanan atas
    """)

# ── TABS: PDF CONVERTER  |  KALKULATOR CSV ───────────────────
tab_pdf, tab_csv = st.tabs(["⚡ Konversi PDF → CSV", "🧮 Kalkulator CSV"])

with tab_pdf:
    if _api_status == "timeout":
        st.error(
            "⚠️ Backend API gagal start dalam waktu yang ditentukan. "
            "Klik tombol Reset/Reboot app, atau coba refresh halaman."
        )
    elif _api_status == "started":
        st.caption(f"🟢 Backend API aktif di `{API_URL}`")
    elif _api_status == "already_running":
        st.caption(f"🟢 Backend API terdeteksi sudah berjalan di `{API_URL}`")

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
            total_f = len(uploaded_files)
            _dark   = st.session_state.get('dark_mode', True)

            for i, uf in enumerate(uploaded_files):
                # Header file ke-N
                if total_f > 1:
                    st.markdown(
                        f'<div style="font-family:\'JetBrains Mono\',monospace; '
                        f'font-size:0.75rem; color:#888; margin-bottom:4px;">'
                        f'FILE {i+1}/{total_f} — {uf.name}</div>',
                        unsafe_allow_html=True
                    )
                try:
                    payload, df_res, req_meta, resp_meta = animasi_terminal_proses(uf, dark=_dark)

                    filename = payload['filename']
                    tingkat  = payload['tingkat']
                    total    = payload['total']
                    jumlah   = payload['jumlah']

                    results.append({
                        'filename': filename,
                        'df'      : df_res,
                        'total'   : total,
                        'count'   : jumlah,
                        'tingkat' : tingkat,
                        'api_log' : {'request': req_meta, 'response': resp_meta},
                    })
                    save_log({
                        'waktu'        : now_wib().strftime("%d %b %Y, %H:%M") + " WIB",
                        'nama_file'    : filename,
                        'tingkat'      : tingkat,
                        'jumlah'       : jumlah,
                        'total'        : total,
                        'status'       : 'Belum Diambil',
                        'waktu_selesai': None,
                    })
                except RuntimeError as e:
                    msg = e.args[0] if e.args else str(e)
                    errors.append(f"❌ {uf.name}: {msg}")
                except Exception as e:
                    errors.append(f"❌ {uf.name}: {e}")

            st.session_state.results = results
            if errors:
                for err in errors:
                    st.error(err)
            # ✅ success message sengaja TIDAK ditampilkan di sini
            # biar nggak muncul sebelum animasi JS selesai ngetik.
            # render_result di bawah sudah cukup sebagai konfirmasi visual.

    # ── TAMPILKAN HASIL ──────────────────────────────────────────
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

# ── TAB KALKULATOR CSV ───────────────────────────────────────
with tab_csv:
    _dark_c = st.session_state.get('dark_mode', True)
    _surf_c = "#1a1a1a" if _dark_c else "#ffffff"
    _bdr_c  = "#333333" if _dark_c else "#111111"
    _txt_c  = "#f0f0f0" if _dark_c else "#111111"
    _mut_c  = "#888888" if _dark_c else "#555555"
    _bg2_c  = "#222222" if _dark_c else "#f5f0e8"
    _acc    = "#ff6b35"
    _grn    = "#00e5a0"

    st.markdown(f"""
    <style>
    .csv-file-row {{
        background: {_surf_c};
        border: 2px solid {_bdr_c};
        border-radius: 0px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 3px 3px 0px {_bdr_c};
        font-family: 'JetBrains Mono', monospace;
    }}
    .csv-grand {{
        background: {_acc};
        border: 3px solid {_txt_c};
        border-radius: 0px;
        padding: 1.25rem 1.5rem;
        margin-top: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 5px 5px 0px {_txt_c};
        font-family: 'JetBrains Mono', monospace;
    }}
    .csv-grand-label {{
        color: {_txt_c}; font-size: 0.78rem; font-weight: 800;
        letter-spacing: 2px; text-transform: uppercase;
    }}
    .csv-grand-value {{
        color: {_txt_c}; font-size: 1.3rem; font-weight: 800;
    }}
    .csv-stat-grid {{
        display: grid; grid-template-columns: 1fr 1fr 1fr;
        gap: 0.75rem; margin: 1rem 0;
    }}
    .csv-stat {{
        background: {_bg2_c}; border: 2px solid {_bdr_c};
        border-radius: 0px; padding: 1rem;
        box-shadow: 3px 3px 0px {_bdr_c};
        font-family: 'JetBrains Mono', monospace;
    }}
    .csv-stat-label {{
        color: {_mut_c}; font-size: 0.68rem; font-weight: 700;
        letter-spacing: 2px; text-transform: uppercase; margin-bottom: 0.4rem;
    }}
    .csv-stat-val {{
        color: {_txt_c}; font-size: 1.2rem; font-weight: 800;
    }}
    .csv-empty-box {{
        border: 3px dashed {_bdr_c};
        background: {_surf_c};
        padding: 2.5rem;
        text-align: center;
        margin-top: 0.5rem;
        font-family: 'Space Grotesk', sans-serif;
    }}
    </style>
    """, unsafe_allow_html=True)

    csv_files = st.file_uploader(
        "Upload CSV hasil konversi (No.SEP + Disetujui)",
        type=["csv"],
        accept_multiple_files=True,
        key="csv_uploader",
        label_visibility="collapsed",
    )

    if csv_files:
        rows_per_file = []
        total_grand   = 0
        total_sep     = 0
        errors_csv    = []

        for cf in csv_files:
            try:
                df_c = pd.read_csv(cf)
                col_disetujui = next(
                    (c for c in df_c.columns if 'disetujui' in c.lower()), None
                )
                if col_disetujui is None:
                    errors_csv.append(f"⚠️ {cf.name}: kolom 'Disetujui' tidak ditemukan.")
                    continue
                df_c[col_disetujui] = pd.to_numeric(
                    df_c[col_disetujui].astype(str).str.replace(r'[^0-9]', '', regex=True),
                    errors='coerce'
                ).fillna(0)
                subtotal  = int(df_c[col_disetujui].sum())
                count_sep = len(df_c)
                rows_per_file.append({
                    'nama'    : cf.name,
                    'sep'     : count_sep,
                    'subtotal': subtotal,
                })
                total_grand += subtotal
                total_sep   += count_sep
            except Exception as e:
                errors_csv.append(f"❌ {cf.name}: {e}")

        for err in errors_csv:
            st.warning(err)

        if rows_per_file:
            grand_fmt = f"Rp {total_grand:,.0f}".replace(",", ".")
            sep_fmt   = f"{total_sep:,}".replace(",", ".")

            st.markdown(f"""
            <div class="csv-stat-grid">
                <div class="csv-stat">
                    <div class="csv-stat-label">Total File</div>
                    <div class="csv-stat-val">{len(rows_per_file)}</div>
                </div>
                <div class="csv-stat">
                    <div class="csv-stat-label">Total SEP</div>
                    <div class="csv-stat-val">{sep_fmt}</div>
                </div>
                <div class="csv-stat">
                    <div class="csv-stat-label">Grand Total</div>
                    <div class="csv-stat-val" style="color:{_grn}; font-size:0.85rem;">{grand_fmt}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="section-title">📂 Rincian Per File</div>', unsafe_allow_html=True)
            for r in rows_per_file:
                subtotal_fmt = f"Rp {r['subtotal']:,.0f}".replace(",", ".")
                sep_r_fmt    = f"{r['sep']:,}".replace(",", ".")
                st.markdown(f"""
                <div class="csv-file-row">
                    <div>
                        <div style="color:{_txt_c}; font-size:0.8rem; font-weight:700;">📄 {r['nama']}</div>
                        <div style="color:{_mut_c}; font-size:0.7rem; margin-top:2px;">{sep_r_fmt} SEP</div>
                    </div>
                    <div style="color:{_grn}; font-size:0.85rem; font-weight:800;">{subtotal_fmt}</div>
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
            <div style="font-size:2rem; margin-bottom:0.5rem;">📊</div>
            <div style="color:{_txt_c}; font-weight:700; font-size:0.95rem; margin-bottom:0.3rem;">
                Upload file CSV di atas
            </div>
            <div style="color:{_mut_c}; font-size:0.8rem;">
                Bisa multiple file — format: No.SEP, Disetujui
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# LOG & REKAP
# ══════════════════════════════════════════════════════════════
st.divider()
log_data = load_log()

# Monthly rekap
if log_data:
    bulan_order = ["JANUARI","FEBRUARI","MARET","APRIL","MEI","JUNI",
                   "JULI","AGUSTUS","SEPTEMBER","OKTOBER","NOVEMBER","DESEMBER"]
    rekap = {}
    for item in log_data:
        m = re.search(r'FPK_(?:RITL|RJTL|RITP|RJTP|FPK)?_?([A-Z]+)_(\d{4})', item['nama_file'])
        period = f"{m.group(1)} {m.group(2)}" if m else "Lainnya"
        if period not in rekap:
            rekap[period] = {'total': 0, 'count': 0, 'konversi': 0, 'tingkats': set()}
        rekap[period]['total']    += item['total']
        rekap[period]['count']    += item['jumlah']
        rekap[period]['konversi'] += 1
        rekap[period]['tingkats'].add(item.get('tingkat', ''))

    sorted_periods = sorted(rekap.keys(),
        key=lambda x: (x.split()[-1], bulan_order.index(x.split()[0])
                       if x.split()[0] in bulan_order else 99), reverse=True)

    st.markdown('<div class="section-title">📅 Rekap Per Bulan</div>', unsafe_allow_html=True)
    for p in sorted_periods:
        r        = rekap[p]
        total_rp = f"Rp {r['total']:,.0f}".replace(",", ".")
        tkt_str  = " · ".join(sorted(t for t in r['tingkats'] if t))
        st.markdown(f"""
        <div class="rekap-card">
            <div>
                <div class="rekap-period">{p}</div>
                <div class="rekap-meta">{r['konversi']}x konversi &nbsp;·&nbsp; {r['count']} SEP &nbsp;·&nbsp; {tkt_str}</div>
            </div>
            <div class="rekap-total">{total_rp}</div>
        </div>
        """, unsafe_allow_html=True)
    st.divider()

# Chart
if log_data:
    st.markdown('<div class="section-title">📊 Rekap Per Periode</div>', unsafe_allow_html=True)
    df_chart = build_chart(log_data)
    if df_chart is not None:
        st.bar_chart(df_chart, use_container_width=True, height=220,
                     color=["#e040fb","#00b0ff","#00e5a0","#ff6b35"][:len(df_chart.columns)])
    st.divider()

# Log summary stats
if log_data:
    total_entri   = len(log_data)
    total_selesai = sum(1 for x in log_data if x.get('status') == 'Selesai')
    total_pending = total_entri - total_selesai
    total_nominal = sum(x['total'] for x in log_data)
    nominal_fmt   = f"Rp {total_nominal:,.0f}".replace(",", ".")

    dark = st.session_state.dark_mode
    th   = '#f1f5f9' if dark else '#0a0a0a'

    st.markdown(f"""
    <div class="summary-grid">
        <div class="summary-card s-konversi">
            <div style="color:#ff6b35; font-size:9px; font-weight:700; letter-spacing:2px;
                text-transform:uppercase; margin-bottom:4px; font-family:'JetBrains Mono',monospace;">
                Total Konversi
            </div>
            <div style="color:{th}; font-size:1.4rem; font-weight:800;">{total_entri}</div>
        </div>
        <div class="summary-card s-selesai">
            <div style="color:#00e5a0; font-size:9px; font-weight:700; letter-spacing:2px;
                text-transform:uppercase; margin-bottom:4px; font-family:'JetBrains Mono',monospace;">
                Selesai
            </div>
            <div style="color:#00e5a0; font-size:1.4rem; font-weight:800;">{total_selesai}</div>
        </div>
        <div class="summary-card s-pending">
            <div style="color:#ffd700; font-size:9px; font-weight:700; letter-spacing:2px;
                text-transform:uppercase; margin-bottom:4px; font-family:'JetBrains Mono',monospace;">
                Pending
            </div>
            <div style="color:#ffd700; font-size:1.4rem; font-weight:800;">{total_pending}</div>
        </div>
        <div class="summary-card s-nominal">
            <div style="color:#e040fb; font-size:9px; font-weight:700; letter-spacing:2px;
                text-transform:uppercase; margin-bottom:4px; font-family:'JetBrains Mono',monospace;">
                Total Nominal
            </div>
            <div style="color:#e040fb; font-size:0.78rem; font-weight:800; white-space:nowrap;
                overflow:hidden; text-overflow:ellipsis;">{nominal_fmt}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Log header
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
    for i, item in enumerate(log_data):
        tkt      = item.get('tingkat', '')
        t_cls    = tkt.lower() if tkt in ('RITL','RJTL','RITP','RJTP') else 'other'
        badge    = f'<span class="log-badge {t_cls}">{tkt}</span>' if tkt else ''
        total_rp = f"Rp {item['total']:,.0f}".replace(",", ".")
        status   = item.get('status', 'Belum Diambil')
        wkt_sel  = item.get('waktu_selesai')

        if status == 'Selesai':
            status_html  = '<span class="status-selesai">✓ Selesai</span>'
            footer_extra = f'<span class="log-item-sep">·</span><span class="log-item-time">📥 {wkt_sel}</span>' if wkt_sel else ''
        else:
            status_html  = '<span class="status-pending">⏳ Belum Diambil</span>'
            footer_extra = ''

        st.markdown(f"""
        <div class="log-item">
            <div class="log-item-name">📄 {item['nama_file']} {badge} {status_html}</div>
            <div class="log-item-footer">
                <span class="log-item-time">🕓 {item['waktu']}</span>
                <span class="log-item-sep">·</span>
                <span class="log-item-total">{total_rp}</span>
                <span class="log-item-sep">·</span>
                <span class="log-item-count">{item['jumlah']} SEP</span>
                {footer_extra}
            </div>
        </div>""", unsafe_allow_html=True)

        if status != 'Selesai':
            col_a, col_b = st.columns([5, 1])
            with col_b:
                st.markdown('<div class="selesai-btn" style="margin-top:-0.4rem;">', unsafe_allow_html=True)
                if st.button("✓ Tandai", key=f"tandai_{i}"):
                    update_log_status(item['nama_file'], 'Selesai')
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────────────────────
_dark     = st.session_state.get('dark_mode', True)
ft_border = "rgba(255,255,255,0.05)" if _dark else "rgba(0,0,0,0.07)"
ft_dim    = "#334155" if _dark else "#94a3b8"
ft_dimmer = "#1e293b" if _dark else "#cbd5e1"
ft_muted  = "#475569" if _dark else "#64748b"

st.markdown(f"""
<div style="text-align:center; padding:2.5rem 1rem 1.5rem; margin-top:2.5rem; border-top:1px solid {ft_border};">
    <div style="margin-bottom:1rem;">
        <div style="display:inline-flex; align-items:center; gap:8px;
            background:#ff6b35; border:3px solid #333;
            padding:6px 20px; margin-bottom:0.8rem; box-shadow:4px 4px 0px #333;">
            <span style="font-size:14px;">⚡</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:0.78rem;
                font-weight:800; color:#fff; letter-spacing:2px;">FPK CONVERTER</span>
        </div>
    </div>
    <div style="font-size:0.8rem; color:{ft_muted}; font-weight:400; margin-bottom:1.2rem; letter-spacing:0.3px;">
        Solusi otomasi konversi data klaim BPJS Kesehatan
    </div>
    <div style="display:flex; align-items:center; justify-content:center; gap:8px; margin-bottom:1.2rem;">
        <div style="width:6px; height:6px; background:#ff6b35; border:1px solid #ff6b35;"></div>
        <div style="width:6px; height:6px; background:#e040fb; border:1px solid #e040fb;"></div>
        <div style="width:6px; height:6px; background:#00e5a0; border:1px solid #00e5a0;"></div>
        <div style="width:6px; height:6px; background:#00b0ff; border:1px solid #00b0ff;"></div>
    </div>
    <div style="font-family:'JetBrains Mono',monospace; font-size:0.72rem;
        color:{ft_dim}; letter-spacing:1px; margin-bottom:0.4rem;">
        Dikembangkan oleh <strong style="color:#6366f1; font-size:0.78rem;">Isfan Fajar Anugrah</strong>
    </div>
    <div style="font-size:0.68rem; color:{ft_dimmer}; letter-spacing:0.5px; margin-bottom:0.8rem;">
        Versi 1.0 &nbsp;·&nbsp; 2025 &nbsp;·&nbsp; All Rights Reserved
    </div>
    <div style="display:inline-block; background:rgba(239,68,68,0.06);
        border:1px solid rgba(239,68,68,0.15); border-radius:0px; padding:6px 16px;">
        <span style="font-size:0.65rem; color:#f87171; letter-spacing:0.5px;">
            ⚠️ Hak Cipta Pribadi — Dilarang digandakan, dimodifikasi, atau digunakan tanpa izin tertulis dari pemilik
        </span>
    </div>
</div>
""", unsafe_allow_html=True)
