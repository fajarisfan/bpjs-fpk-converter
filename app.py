import os
import json
import re
import time
import colorsys
import pandas as pd
import streamlit as st
import requests

from datetime import datetime, timezone, timedelta
from dummy_pdf import build_dummy_fpk_pdf, BULAN_LIST, TINGKAT_LIST

# â”€â”€ COLOR SYSTEM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def hsl_to_hex(h: int, s: int, l: int) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))

def hex_to_hsl(hex_color: str):
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return round(h * 360), round(s * 100), round(l * 100)

def derive_variants(hex_color: str) -> dict:
    h, s, l = hex_to_hsl(hex_color)
    return {
        "base":   hex_color,
        "dark":   hsl_to_hex(h, s, max(25, l - 12)),
        "glow":   hsl_to_hex(h, s, min(85, l + 18)),
        "bg_d":   hsl_to_hex(h, max(15, s - 35), 14),
        "bg_l":   hsl_to_hex(h, max(15, s - 35), 93),
    }

# Preset palette
_PRESETS_PALETTE = [
    ("ðŸŠ Oranye",   "#ff6b35",  "#00c47a",  "#ffd700",  "#a78bfa"),
    ("ðŸŸ¢ Hijau",    "#19f05a",  "#a121d4",  "#3eb8da",  "#f0a519"),
    ("ðŸ’œ Ungu",     "#a855f7",  "#22d3ee",  "#fb923c",  "#34d399"),
    ("ðŸ”µ Biru",     "#3b82f6",  "#10b981",  "#f59e0b",  "#e879f9"),
    ("ðŸ©µ Cyan",     "#06b6d4",  "#f59e0b",  "#ec4899",  "#84cc16"),
    ("ðŸ–¤ Mono",     "#e2e8f0",  "#94a3b8",  "#64748b",  "#475569"),
    ("ðŸ”´ Merah",    "#ef4444",  "#3b82f6",  "#fbbf24",  "#a78bfa"),
    ("ðŸŒ¿ Sage",     "#6db36d",  "#e07b39",  "#f0c030",  "#7b8fe0"),
]

_FONT_OPTIONS = [
    ("Inter",        "'Inter', sans-serif"),
    ("Poppins",      "'Poppins', sans-serif"),
    ("Roboto",       "'Roboto', sans-serif"),
    ("DM Sans",      "'DM Sans', sans-serif"),
    ("Nunito",       "'Nunito', sans-serif"),
    ("Plus Jakarta", "'Plus Jakarta Sans', sans-serif"),
    ("Sora",         "'Sora', sans-serif"),
    ("Outfit",       "'Outfit', sans-serif"),
]

_FONT_IMPORT = {
    "Inter":        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap",
    "Poppins":      "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap",
    "Roboto":       "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700;900&display=swap",
    "DM Sans":      "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap",
    "Nunito":       "https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap",
    "Plus Jakarta": "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap",
    "Sora":         "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap",
    "Outfit":       "https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap",
}

st.set_page_config(page_title="FPK Converter", page_icon="ðŸ“„", layout="wide")

# â”€â”€ SESSION STATE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
for _k, _v in {
    "logged_in": False, "dark_mode": True, "attempts": 0,
    "locked_until": None, "login_time": None,
    "show_pin_form": False, "show_theme_panel": False,
    "results": [], "errors": [], "show_done": False,
    "demo_mode": False, "demo_pdf_bytes": None, "demo_pdf_info": None,
    "c_primary":   "#ff6b35",
    "c_secondary": "#00c47a",
    "c_accent":    "#ffd700",
    "c_purple":    "#a78bfa",
    "c_bg":        "",
    "c_navbar":    "",
    "c_sidebar":   "",
    "c_header":    "",
    "c_footer":    "",
    "c_footer_txt":"",
    "font_body":   "Inter",
    "bot_history": [],
    "bot_ai_mode": False,
    "chat_input": "",
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# â”€â”€ ACTIVE PALETTE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_palette() -> dict:
    p  = derive_variants(st.session_state.c_primary)
    s  = derive_variants(st.session_state.c_secondary)
    a  = derive_variants(st.session_state.c_accent)
    pu = derive_variants(st.session_state.c_purple)
    return {
        "primary":      p["base"],
        "primary_d":    p["dark"],
        "primary_glow": p["glow"],
        "primary_bg":   p["bg_d"],
        "primary_bg_l": p["bg_l"],
        "secondary":    s["base"],
        "secondary_bg": s["bg_l"],
        "accent":       a["base"],
        "accent_bg":    a["bg_l"],
        "purple":       pu["base"],
        "purple_bg":    pu["bg_l"],
    }

_PAL          = build_palette()
PRIMARY_COLOR = _PAL["primary"]
SECONDARY     = _PAL["secondary"]
ACCENT        = _PAL["accent"]

# â”€â”€ CONFIG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
LOG_FILE  = "/tmp/log_konversi.json"
API_URL   = "https://fpk-converter-api--isfanfajara.replit.app"

@st.cache_data(ttl=30)
def cek_status_api():
    try:
        r = requests.get(f"{API_URL}/api/health", timeout=8)
        if r.status_code == 200:
            return "ok", None
        return "error", f"HTTP {r.status_code}"
    except requests.exceptions.RequestException as e:
        return "error", str(e)

_api_status, _api_error = cek_status_api()

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
            # Edit pesan Telegram jika ada message_id
            if status == "Selesai" and item.get('tele_message_id') and tele_configured():
                edit_notif_telegram(item)
            break
    with open(LOG_FILE, "w") as f:
        json.dump(log[:100], f, ensure_ascii=False, indent=2)

def unique_filename(base_filename: str, existing_names: set) -> str:
    if base_filename not in existing_names:
        return base_filename
    name, ext = os.path.splitext(base_filename)
    counter = 2
    while True:
        candidate = f"{name}_{counter}{ext}"
        if candidate not in existing_names:
            return candidate
        counter += 1

# â”€â”€ TELEGRAM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_tele_config():
    try:
        token   = str(st.secrets.get("TELEGRAM_TOKEN", ""))
        chat_id = str(st.secrets.get("TELEGRAM_CHAT_ID", ""))
        return token, chat_id
    except Exception:
        return "", ""

def tele_configured() -> bool:
    token, chat_id = get_tele_config()
    return bool(token and chat_id)

def kirim_notif_telegram(entry: dict) -> tuple[bool, str]:
    token, chat_id = get_tele_config()
    if not token or not chat_id:
        return False, "Token/Chat ID belum dikonfigurasi"
    nom = f"Rp {entry['total']:,}".replace(",", ".")
    jenis_label = f" Â· ðŸ“Œ {entry.get('jenis','Reguler')}" if entry.get('jenis') == 'Susulan' else ""
    msg = (
        f"ðŸ“„ *FPK Converter â€” Konversi Berhasil*\n\n"
        f"ðŸ¥ *File*: `{entry['nama_file']}`\n"
        f"ðŸ”– *Tingkat*: {entry.get('tingkat','â€“')}{jenis_label}\n"
        f"ðŸ”¢ *Jumlah SEP*: {entry['jumlah']:,}\n"
        f"ðŸ’° *Total Nominal*: {nom}\n"
        f"ðŸ•“ *Waktu*: {entry['waktu']}\n"
        f"ðŸ“Š *Status*: {'âœ… Selesai' if entry.get('status')=='Selesai' else 'â³ Belum Diambil'}\n"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "âœ… Tandai Selesai", "callback_data": f"done_{entry['nama_file']}"}],
        ]
    }
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(keyboard)
            },
            timeout=8
        )
        if resp.ok:
            msg_id = resp.json().get("result", {}).get("message_id")
            return True, "âœ… Notif terkirim ke Telegram", msg_id
        return False, f"âŒ Gagal: {resp.json().get('description','unknown error')}", None
    except Exception as e:
        return False, f"âŒ Error: {e}", None

def edit_notif_telegram(entry: dict) -> bool:
    """Edit pesan Telegram yang sudah ada â€” update status jadi Selesai."""
    token, chat_id = get_tele_config()
    if not token or not chat_id:
        return False
    msg_id = entry.get('tele_message_id')
    if not msg_id:
        return False
    nom = f"Rp {entry['total']:,}".replace(",", ".")
    waktu_selesai = entry.get('waktu_selesai', now_wib().strftime("%d %b %Y, %H:%M") + " WIB")
    jenis_label = f" Â· ðŸ“Œ {entry.get('jenis','Reguler')}" if entry.get('jenis') == 'Susulan' else ""
    msg = (
        f"ðŸ“„ *FPK Converter â€” Konversi Berhasil*\n\n"
        f"ðŸ¥ *File*: `{entry['nama_file']}`\n"
        f"ðŸ”– *Tingkat*: {entry.get('tingkat','â€“')}{jenis_label}\n"
        f"ðŸ”¢ *Jumlah SEP*: {entry['jumlah']:,}\n"
        f"ðŸ’° *Total Nominal*: {nom}\n"
        f"ðŸ•“ *Waktu*: {entry['waktu']}\n"
        f"ðŸ“Š *Status*: âœ… Selesai\n"
        f"ðŸ“¥ *Diambil*: {waktu_selesai}\n"
    )
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": msg,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": []})
            },
            timeout=8
        )
        return resp.ok
    except Exception:
        return False

def kirim_rekap_telegram(log_data: list) -> tuple[bool, str]:
    token, chat_id = get_tele_config()
    if not token or not chat_id:
        return False, "Token/Chat ID belum dikonfigurasi"
    if not log_data:
        return False, "Belum ada data konversi"
    total_nom = sum(x['total'] for x in log_data)
    total_sep = sum(x['jumlah'] for x in log_data)
    selesai   = sum(1 for x in log_data if x.get('status') == 'Selesai')
    nom_fmt   = f"Rp {total_nom:,}".replace(",", ".")
    rows = ""
    for i, x in enumerate(log_data[:20], 1):
        nom = f"Rp {x['total']:,}".replace(",",".")
        st_icon = "âœ…" if x.get('status') == 'Selesai' else "â³"
        rows += f"{i}. `{x['nama_file']}`\n   {st_icon} {x['jumlah']:,} SEP Â· {nom} Â· {x['waktu']}\n"
    if len(log_data) > 20:
        rows += f"\n_...dan {len(log_data)-20} lainnya_\n"
    msg = (
        f"ðŸ“Š *Rekap FPK Converter*\n\n"
        f"ðŸ“ Total file: *{len(log_data)}*\n"
        f"âœ… Selesai: *{selesai}* Â· â³ Pending: *{len(log_data)-selesai}*\n"
        f"ðŸ”¢ Total SEP: *{total_sep:,}*\n"
        f"ðŸ’° Total Nominal: *{nom_fmt}*\n\n"
        f"*Riwayat:*\n{rows}"
    )
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=8
        )
        if resp.ok:
            return True, "âœ… Rekap terkirim ke Telegram"
        return False, f"âŒ Gagal: {resp.json().get('description','unknown error')}"
    except Exception as e:
        return False, f"âŒ Error: {e}"

# â”€â”€ AI CHAT (Groq) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_groq_api_key() -> str:
    try:
        return str(st.secrets.get("GROQ_API_KEY", ""))
    except Exception:
        return ""

def claude_configured() -> bool:
    return bool(get_groq_api_key())

def chat_with_claude(history: list, log_data: list) -> str:
    api_key = get_groq_api_key()
    if not api_key:
        return "âŒ GROQ_API_KEY belum dikonfigurasi. Daftar gratis di console.groq.com lalu tambahkan di Secrets."

    log_summary = ""
    if log_data:
        total_nom = sum(x['total'] for x in log_data)
        total_sep = sum(x['jumlah'] for x in log_data)
        selesai   = sum(1 for x in log_data if x.get('status') == 'Selesai')
        nom_fmt   = f"Rp {total_nom:,}".replace(",", ".")
        recent    = log_data[:5]
        detail    = "\n".join(
            f"  - {x['nama_file']} | {x['jumlah']} SEP | Rp {x['total']:,} | {x.get('status','?')}"
            for x in recent
        )
        log_summary = (
            f"\n\nData konversi FPK saat ini (realtime):\n"
            f"- Total file dikonversi: {len(log_data)}\n"
            f"- Selesai: {selesai} | Pending: {len(log_data)-selesai}\n"
            f"- Total SEP: {total_sep:,}\n"
            f"- Total Nominal: {nom_fmt}\n"
            f"- 5 File terbaru:\n{detail}"
        )

    system_prompt = (
        "Kamu adalah FPK Bot, asisten cerdas untuk aplikasi FPK Converter milik Isfan Fajar Anugrah. "
        "Aplikasi ini dipakai di RSUD Cilegon untuk konversi data klaim BPJS Kesehatan dari PDF ke CSV. "
        "Alur kerja: petugas upload PDF FPK â†’ sistem ekstrak No.SEP dan nominal Disetujui â†’ output CSV. "
        "Tingkat klaim: RITL (rawat inap tingkat lanjut) dan RJTL (rawat jalan tingkat lanjut). "
        "Jenis: Reguler (klaim normal) dan Susulan (klaim tambahan/perbaikan). "
        "Kamu paham konteks data konversi dan bisa menjawab pertanyaan tentang rekap, nominal, jumlah SEP, status pending. "
        "Kamu juga bisa diajak ngobrol santai, kasih motivasi Islami, atau bantu hal umum lainnya. "
        "Jawab pakai bahasa Indonesia yang ramah dan santai. "
        "Sesekali pakai kata Islami seperti Alhamdulillah, Insya Allah, Masya Allah. "
        "Jawaban singkat dan padat â€” maksimal 3-4 kalimat kecuali ditanya detail spesifik."
        + log_summary
    )

    messages = [{"role": "system", "content": system_prompt}]
    for role, msg in history[-20:]:
        if not msg.strip():
            continue
        api_role = "user" if role == "user" else "assistant"
        if messages and messages[-1]["role"] == api_role:
            messages[-1]["content"] += "\n" + msg.strip()
        else:
            messages.append({"role": api_role, "content": msg.strip()})

    while len(messages) > 1 and messages[-1]["role"] != "user":
        messages.pop()

    if len(messages) <= 1:
        return "Maaf, pesan tidak valid. Coba kirim ulang ya kak!"

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.7,
            },
            timeout=20,
        )
        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"].strip()
        try:
            err_detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            err_detail = resp.text
        return f"âŒ Groq API error {resp.status_code}: {err_detail}"
    except Exception as e:
        return f"âŒ Gagal menghubungi Groq: {e}"

# â”€â”€ BOT COMMAND HANDLER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_QUOTES = [
    'Sebaik-baik manusia adalah yang paling bermanfaat bagi orang lain. (HR. Thabrani)',
    'Barangsiapa yang beriman kepada Allah dan hari akhir, hendaklah ia berkata baik atau diam. (HR. Bukhari & Muslim)',
    'Senyummu di hadapan saudaramu adalah sedekah. (HR. Tirmidzi)',
    'Allah tidak melihat rupa dan harta kalian, tapi Dia melihat hati dan amal kalian. (HR. Muslim)',
]

_JOKES = [
    "Kenapa programmer FPK gak pernah sedih? Karena selalu ada try-catch ðŸ¤£",
    "Orang IT kalau turun hujan? Nunggu koneksi stabil dulu ðŸ˜„",
    "FPK Converter minta maaf ke PDF: 'Maaf ya, aku harus mengekstrak kamu' ðŸ˜‚",
]

def handle_bot_command(text: str, log_data: list) -> str:
    text_lower = text.strip().lower()

    if "zizah" in text_lower:
        return "Jangan di pikiran terus, doain aja yang terbaik buat dia ðŸ™âœ¨\nYang penting kamu tetap semangat dan sholat ya!"

    if text_lower in ["assalamualaikum", "assalamu'alaikum", "salam"]:
        return "Waalaikumsalam warahmatullahi wabarakatuh! ðŸ˜Š\nSemoga hari kakak penuh berkah dan dimudahkan segala urusan. Aamiin."

    if any(k in text_lower for k in ["halo", "hai", "hey", "hello"]):
        return "Halo kak! Senang ngobrol sama kakak ðŸ˜„\nKetik /help untuk lihat perintah, atau aktifkan Mode AI untuk chat cerdas!"

    if any(k in text_lower for k in ["kabar", "gimana", "apa kabar"]):
        return "Alhamdulillah, baik banget kak! ðŸ˜Š\nSemoga kakak juga selalu sehat dan bahagia ya."

    if text_lower in ["/quote", "quote"]:
        import random
        return f"ðŸ“– *Kutipan Hari Ini*\n\n{random.choice(_QUOTES)}"

    if text_lower in ["/joke", "joke"]:
        import random
        return f"ðŸ˜‚ *Candaan Santai*\n\n{random.choice(_JOKES)}"

    if text_lower in ["/rekap", "rekap"]:
        if not log_data:
            return "ðŸ“­ Belum ada data konversi."
        total_nom = sum(x['total'] for x in log_data)
        total_sep = sum(x['jumlah'] for x in log_data)
        selesai   = sum(1 for x in log_data if x.get('status') == 'Selesai')
        nom_fmt   = f"Rp {total_nom:,}".replace(",", ".")
        return (
            f"ðŸ“Š *Rekap FPK Converter*\n\n"
            f"ðŸ“ Total file: *{len(log_data)}*\n"
            f"âœ… Selesai: *{selesai}* Â· â³ Pending: *{len(log_data)-selesai}*\n"
            f"ðŸ”¢ Total SEP: *{total_sep:,}*\n"
            f"ðŸ’° Total Nominal: *{nom_fmt}*"
        )

    if text_lower in ["/riwayat", "riwayat"]:
        if not log_data:
            return "ðŸ“­ Belum ada riwayat."
        rows = ""
        for i, x in enumerate(log_data[:10], 1):
            nom = f"Rp {x['total']:,}".replace(",",".")
            st_icon = "âœ…" if x.get('status') == 'Selesai' else "â³"
            rows += f"{i}. `{x['nama_file']}` {st_icon}\n   {x['jumlah']:,} SEP Â· {nom}\n\n"
        return f"ðŸ“‹ *10 Konversi Terakhir*\n\n{rows}"

    if text_lower in ["/total", "total"]:
        if not log_data:
            return "ðŸ“­ Belum ada data."
        total_nom = sum(x['total'] for x in log_data)
        total_sep = sum(x['jumlah'] for x in log_data)
        return (
            f"ðŸ’° *Total Keseluruhan*\n\n"
            f"Nominal: *Rp {total_nom:,}*\n"
            f"SEP: *{total_sep:,}*\n"
            f"File: *{len(log_data)}*"
        ).replace(",", ".")

    if text_lower in ["/pending", "pending"]:
        pending = [x for x in log_data if x.get('status') != 'Selesai']
        if not pending:
            return "âœ… Semua file sudah diambil!"
        rows = ""
        for i, x in enumerate(pending, 1):
            nom = f"Rp {x['total']:,}".replace(",",".")
            rows += f"{i}. `{x['nama_file']}`\n   {x['jumlah']:,} SEP Â· {nom}\n\n"
        return f"â³ *{len(pending)} File Belum Diambil*\n\n{rows}"

    if text_lower in ["/top", "top"]:
        if not log_data:
            return "ðŸ“­ Belum ada data."
        sorted_data = sorted(log_data, key=lambda x: x['total'], reverse=True)[:5]
        rows = ""
        for i, x in enumerate(sorted_data, 1):
            nom = f"Rp {x['total']:,}".replace(",", ".")
            rows += f"{i}. `{x['nama_file']}` â†’ {nom}\n"
        return f"ðŸ† *Top 5 Konversi Terbesar*\n\n{rows}"

    if text_lower.startswith("/cari ") or text_lower.startswith("cari "):
        keyword = text.split(" ", 1)[1].strip().lower()
        hasil = [x for x in log_data if keyword in x.get('nama_file','').lower()
                 or keyword in x.get('waktu','').lower()
                 or keyword in x.get('tingkat','').lower()]
        if not hasil:
            return f"ðŸ” Tidak ada hasil untuk *{keyword}*"
        rows = ""
        for i, x in enumerate(hasil[:10], 1):
            nom = f"Rp {x['total']:,}".replace(",",".")
            st_icon = "âœ…" if x.get('status') == 'Selesai' else "â³"
            rows += f"{i}. `{x['nama_file']}` {st_icon}\n   {x['jumlah']:,} SEP Â· {nom}\n\n"
        return f"ðŸ” *Hasil cari '{keyword}'* ({len(hasil)} ditemukan)\n\n{rows}"

    if text_lower in ["/help", "help", "bantuan"]:
        return (
            "ðŸ¤– *FPK Bot â€” Asisten Konversi*\n\n"
            "ðŸ“Œ *Perintah:*\n"
            "`/rekap`   â†’ Ringkasan konversi\n"
            "`/riwayat` â†’ 10 konversi terakhir\n"
            "`/total`   â†’ Total nominal & SEP\n"
            "`/pending` â†’ File belum diambil\n"
            "`/top`     â†’ Top 5 terbesar\n"
            "`/cari <kata>` â†’ Cari file\n"
            "`/quote`   â†’ Kutipan islami\n"
            "`/joke`    â†’ Candaan santai\n\n"
            "ðŸ’¡ Aktifkan *Mode AI* untuk chat cerdas!"
        )

    return (
        "Maaf kak, belum paham ðŸ˜…\n"
        "Ketik `/help` untuk lihat perintah, atau aktifkan **Mode AI** untuk chat bebas!"
    )

# â”€â”€ PIN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            return False, f"ðŸ”’ Terlalu banyak percobaan. Coba lagi dalam **{sisa} menit**."
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
            return False, f"ðŸ”’ PIN salah {MAX_ATTEMPT}x. Dikunci selama **{LOCKOUT_MIN} menit**."
        return False, f"âŒ PIN salah. Sisa percobaan: **{sisa_attempt}x**."

# â”€â”€ CSS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def inject_css(dark):
    c_bg      = st.session_state.get("c_bg", "")
    c_navbar  = st.session_state.get("c_navbar", "")
    c_sidebar = st.session_state.get("c_sidebar", "")
    c_header  = st.session_state.get("c_header", "")
    c_footer  = st.session_state.get("c_footer", "")
    c_footer_txt = st.session_state.get("c_footer_txt", "")
    font_key  = st.session_state.get("font_body", "Inter")
    font_css  = dict(_FONT_OPTIONS).get(font_key, "'Inter', sans-serif")
    font_url  = _FONT_IMPORT.get(font_key, _FONT_IMPORT["Inter"])

    if dark:
        bg          = c_bg      or "#0a0a0a"
        surface     = c_navbar  or "#141414"
        surface2    = "#1e1e1e"
        border      = "#242424"
        border2     = "#333333"
        text_h      = "#f0f0f0"
        text_body   = "#b0b0b0"
        text_muted  = "#666666"
        text_dim    = "#3a3a3a"
        input_bg    = "#0d0d0d"
        input_bdr   = "#2a2a2a"
        input_col   = "#f0f0f0"
        label_col   = "#888888"
        shadow      = "rgba(0,0,0,0.7)"
        toggle_icon = "â˜€ï¸"
        toggle_tip  = "Mode Terang"
        log_bg      = c_sidebar or "#141414"
        log_border  = "#242424"
        login_bg    = "#141414"
        hero_bg     = c_header  or "#141414"
        hero_stat   = "#1e1e1e"
        hero_stat_b = "#282828"
        bottom_bg   = c_footer  or "#0a0a0a"
        bottom_bdr  = "#1e1e1e"
        ft_txt      = c_footer_txt or "#888888"
        bubble_bot_bg  = "#1e1e1e"
        bubble_bot_bdr = "#2a2a2a"
        bubble_bot_txt = "#e0e0e0"
        chat_bg        = "#111111"
        chat_bdr       = "#242424"
    else:
        bg          = c_bg      or "#f5f4f2"
        surface     = c_navbar  or "#ffffff"
        surface2    = "#f0eee9"
        border      = "#e4e2dd"
        border2     = "#d0cec9"
        text_h      = "#1a1a1a"
        text_body   = "#444444"
        text_muted  = "#888888"
        text_dim    = "#cccccc"
        input_bg    = "#ffffff"
        input_bdr   = "#d5d3ce"
        input_col   = "#1a1a1a"
        label_col   = "#666666"
        shadow      = "rgba(0,0,0,0.07)"
        toggle_icon = "ðŸŒ™"
        toggle_tip  = "Mode Gelap"
        log_bg      = c_sidebar or "#ffffff"
        log_border  = "#e0ddd8"
        login_bg    = "#ffffff"
        hero_bg     = c_header  or "#ffffff"
        hero_stat   = "#f5f4f2"
        hero_stat_b = "#e8e6e1"
        bottom_bg   = c_footer  or "#ffffff"
        bottom_bdr  = "#e4e2dd"
        ft_txt      = c_footer_txt or "#888888"
        bubble_bot_bg  = "#f0f0f0"
        bubble_bot_bdr = "#e0ddd8"
        bubble_bot_txt = "#1a1a1a"
        chat_bg        = "#fafaf8"
        chat_bdr       = "#e4e2dd"

    st.session_state._toggle_icon = toggle_icon
    st.session_state._toggle_tip = toggle_tip

    # CSS tambahan untuk sembunyikan tombol mata di input password
    hide_eye_css = """
    /* Sembunyikan tombol show/hide password di semua input */
    .stTextInput button[data-testid="stTextInputHideShowButton"],
    .stTextInput button[aria-label="Show password"],
    .stTextInput button[aria-label="Hide password"],
    button[data-testid="stTextInputHideShowButton"],
    button[aria-label="Show password"],
    button[aria-label="Hide password"],
    div[data-testid="stTextInput"] button {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    /* Tambahan untuk mengatasi styling bawaan */
    .stTextInput div[data-baseweb="input"] button {
        display: none !important;
    }
    """

    st.markdown(f"""
    <style>
    @import url('{font_url}');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: {font_css} !important; }}
    #MainMenu {{visibility:hidden;}}
    footer {{visibility:hidden;}}
    header {{visibility:hidden;}}
    .stApp {{ background: {bg}; }}
    .block-container {{
        max-width: 560px !important;
        padding: 0 1rem 4rem !important;
        margin: 0 auto !important;
    }}
    .stTextInput input[type="password"] {{
        color: transparent !important;
        caret-color: {PRIMARY_COLOR} !important;
        -webkit-text-security: disc !important;
        background: {input_bg} !important;
    }}
    {hide_eye_css}
    .stRadio > div {{
        display: flex !important;
        gap: 0.75rem !important;
        flex-wrap: wrap !important;
        justify-content: center !important;
    }}
    .stRadio label {{
        background: {surface} !important;
        border: 1.5px solid {border} !important;
        border-radius: 50px !important;
        padding: 0.5rem 1.6rem !important;
        color: {text_h} !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        transition: all 0.18s ease !important;
        cursor: pointer !important;
    }}
    .stRadio label:hover {{ border-color: {PRIMARY_COLOR} !important; }}
    .stRadio div[role="radiogroup"] label[data-selected="true"] {{
        background: {PRIMARY_COLOR} !important;
        border-color: {PRIMARY_COLOR} !important;
        color: #fff !important;
    }}
    .stRadio div[role="radiogroup"] label svg {{ display: none !important; }}
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
    .bento:hover {{ transform: translateY(-3px); box-shadow: 0 8px 32px {shadow}; }}
    .bento .label {{
        font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1.5px;
        color: {text_muted}; margin-bottom: 0.3rem; font-weight: 700;
    }}
    .bento .value {{ font-size: 2rem; font-weight: 800; color: {text_h}; line-height: 1.2; }}
    .bento .value.accent {{ color: {PRIMARY_COLOR}; }}
    .bento .value.green  {{ color: {SECONDARY}; }}
    .bento .sub {{ font-size: 0.72rem; color: {text_muted}; margin-top: 0.25rem; }}
    .hero-card {{
        background: {hero_bg};
        border: 1px solid {border};
        border-radius: 28px;
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.25rem;
        position: relative;
        overflow: hidden;
    }}
    .hero-label {{
        font-size: 0.6rem; font-weight: 800; letter-spacing: 2.5px;
        color: {text_muted}; text-transform: uppercase; margin-bottom: 0.25rem;
    }}
    .hero-title {{
        font-size: 1.75rem; font-weight: 900; color: {text_h};
        letter-spacing: -1px; margin-bottom: 0.15rem; line-height: 1.1;
    }}
    .hero-title span {{ color: {PRIMARY_COLOR}; }}
    .hero-sub {{ font-size: 0.78rem; color: {text_muted}; margin-bottom: 1.1rem; }}
    .hero-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }}
    .hero-stat {{
        background: {hero_stat}; border: 1px solid {hero_stat_b};
        border-radius: 16px; padding: 0.75rem 0.9rem;
    }}
    .hero-stat-label {{
        font-size: 0.6rem; font-weight: 700; color: {text_muted};
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.2rem;
    }}
    .hero-stat-value {{ font-size: 1.3rem; font-weight: 800; color: {text_h}; line-height: 1.1; }}
    .top-nav {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.75rem 0 1rem;
    }}
    .top-nav-logo {{
        display: inline-flex; align-items: center; gap: 8px;
        background: {PRIMARY_COLOR}; border-radius: 40px; padding: 0.3rem 1rem;
    }}
    .top-nav-logo span {{
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
        font-weight: 800; color: #fff; letter-spacing: 2px;
    }}
    .icon-btn-wrap .stButton > button {{
        background: {surface} !important; color: {text_muted} !important;
        border: 1px solid {border} !important; border-radius: 50px !important;
        padding: 0 !important; width: 36px !important; height: 36px !important;
        min-width: 36px !important; font-size: 0.85rem !important;
        box-shadow: none !important; transition: all 0.15s ease !important;
    }}
    .icon-btn-wrap .stButton > button:hover {{
        border-color: {PRIMARY_COLOR} !important; color: {PRIMARY_COLOR} !important;
        background: {surface2} !important;
    }}
    .stButton > button {{
        background: {PRIMARY_COLOR} !important; color: #fff !important;
        border: none !important; border-radius: 50px !important;
        padding: 0.75rem 2rem !important; font-weight: 700 !important;
        font-size: 0.9rem !important; box-shadow: 0 4px 18px {PRIMARY_COLOR}44 !important;
        transition: all 0.2s ease !important; width: 100% !important;
    }}
    .stButton > button:hover {{ transform: translateY(-1px) !important; }}
    .stButton > button:active {{ transform: scale(0.98) !important; }}
    .stDownloadButton > button {{
        background: {surface} !important; color: {SECONDARY} !important;
        border: 2px solid {SECONDARY} !important; border-radius: 50px !important;
        font-weight: 700 !important; box-shadow: none !important;
    }}
    .stDownloadButton > button:hover {{
        background: {SECONDARY} !important; color: #fff !important;
    }}
    [data-testid="stFileUploader"] section {{
        background: {surface}; border: 2px dashed {border};
        border-radius: 24px; padding: 2.5rem 1.5rem; transition: all 0.2s;
    }}
    [data-testid="stFileUploader"] section:hover {{
        border-color: {PRIMARY_COLOR}; background: {surface2};
    }}
    [data-testid="stTabs"] [data-testid="stTab"] {{
        border-radius: 50px !important; padding: 0.4rem 1.4rem !important;
        background: transparent !important; color: {text_muted} !important;
        border: 1.5px solid {border} !important; font-weight: 700; font-size: 0.82rem;
    }}
    [data-testid="stTabs"] [aria-selected="true"] {{
        background: {PRIMARY_COLOR} !important; color: #fff !important;
        border-color: {PRIMARY_COLOR} !important;
    }}
    [data-testid="stDataFrame"] {{ border-radius: 18px !important; overflow: hidden !important; border: 1px solid {border} !important; }}
    [data-testid="stExpander"] {{
        border-radius: 18px !important; border: 1px solid {border} !important;
        background: {surface} !important; overflow: hidden; box-shadow: 0 2px 12px {shadow};
    }}
    .chat-wrapper {{
        background: {chat_bg};
        border: 1px solid {chat_bdr};
        border-radius: 20px;
        padding: 12px 10px;
        height: 300px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: 10px;
        scrollbar-width: thin;
        scrollbar-color: {border2} transparent;
    }}
    .bubble-row {{
        display: flex;
        align-items: flex-end;
        gap: 6px;
        margin-bottom: 2px;
    }}
    .bubble-row.user {{ flex-direction: row-reverse; }}
    .bubble-avatar {{
        width: 26px; height: 26px; border-radius: 50%;
        font-size: 0.85rem; display: flex; align-items: center;
        justify-content: center; flex-shrink: 0;
        background: {surface2};
    }}
    .bubble-bot {{
        background: {bubble_bot_bg};
        border: 1px solid {bubble_bot_bdr};
        color: {bubble_bot_txt};
        border-radius: 14px 14px 14px 3px;
        padding: 7px 11px;
        font-size: 0.77rem;
        line-height: 1.5;
        max-width: 78%;
        word-wrap: break-word;
        white-space: pre-wrap;
    }}
    .bubble-user {{
        background: {PRIMARY_COLOR};
        color: #fff;
        border-radius: 14px 14px 3px 14px;
        padding: 7px 11px;
        font-size: 0.77rem;
        line-height: 1.5;
        max-width: 78%;
        word-wrap: break-word;
    }}
    .bubble-time {{
        font-size: 0.58rem; color: {text_muted}; margin-top: 2px;
        padding: 0 4px;
    }}
    .log-item {{
        background: {log_bg} !important; border: 1px solid {log_border} !important;
        border-radius: 20px !important; padding: 1rem 1.25rem !important;
        margin-bottom: 0.65rem !important; box-shadow: 0 2px 10px {shadow} !important;
        transition: border-color 0.15s ease, transform 0.15s ease;
    }}
    .log-item:hover {{ border-color: {PRIMARY_COLOR} !important; transform: translateY(-1px); }}
    .log-item .log-name {{
        font-weight: 700; font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem; color: {text_h}; margin-bottom: 0.35rem;
    }}
    .log-item .log-meta {{
        display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: {text_muted};
    }}
    .log-badge {{
        display: inline-flex; align-items: center; padding: 2px 10px;
        border-radius: 40px; font-size: 0.58rem; font-weight: 800;
        letter-spacing: 0.5px; font-family: 'JetBrains Mono', monospace; border: 1.5px solid;
    }}
    .log-badge.ritl {{ border-color: #a78bfa; color: #a78bfa; background: rgba(139,92,246,0.08); }}
    .log-badge.rjtl {{ border-color: #60a5fa; color: #60a5fa; background: rgba(59,130,246,0.08); }}
    .log-badge.other {{ border-color: #94a3b8; color: #94a3b8; }}
    .status-selesai {{
        background: rgba(0,196,122,0.1); border: 1.5px solid {SECONDARY}; color: {SECONDARY};
        padding: 2px 12px; border-radius: 40px; font-size: 0.62rem; font-weight: 700;
        font-family: 'JetBrains Mono', monospace; display: inline-flex; align-items: center; gap: 4px;
    }}
    .status-pending {{
        background: rgba(180,130,0,0.08); border: 1.5px solid #b45309; color: #b45309;
        padding: 2px 12px; border-radius: 40px; font-size: 0.62rem; font-weight: 700;
        font-family: 'JetBrains Mono', monospace; display: inline-flex; align-items: center; gap: 4px;
    }}
    .section-title {{
        font-size: 0.65rem; font-weight: 800; letter-spacing: 2.5px;
        text-transform: uppercase; color: {text_muted}; margin-bottom: 1rem;
        border-left: 3px solid {PRIMARY_COLOR}; padding-left: 10px;
        font-family: 'JetBrains Mono', monospace;
    }}
    .tingkat-badge {{
        display: inline-flex; align-items: center; gap: 6px; padding: 5px 16px;
        border-radius: 40px; font-size: 0.72rem; font-weight: 700;
        letter-spacing: 1px; text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
        border: 1.5px solid;
    }}
    .tingkat-badge.ritl {{ background: rgba(139,92,246,0.10); border-color: #a78bfa; color: #a78bfa; }}
    .tingkat-badge.rjtl {{ background: rgba(59,130,246,0.10); border-color: #60a5fa; color: #60a5fa; }}
    hr {{ border-color: {border} !important; margin: 1.5rem 0 !important; opacity: 0.4; }}
    .fpk-footer {{
        background: {bottom_bg};
        border-top: 1px solid {bottom_bdr};
        padding: 1.5rem 0 0.5rem;
        margin-top: 1.5rem;
        text-align: center;
    }}
    .fpk-footer-txt {{ color: {ft_txt}; font-size: 0.65rem; font-family: 'JetBrains Mono', monospace; }}
    [data-testid="stDecoration"] {{
        background: linear-gradient(90deg, {PRIMARY_COLOR}, {SECONDARY}) !important;
        height: 3px !important;
    }}
    [data-testid="stHeader"] {{ background: {hero_bg} !important; border-bottom: 1px solid {border} !important; }}
    [data-testid="stSidebar"] {{ background: {log_bg} !important; border-right: 1px solid {border} !important; }}
    [data-testid="stSidebar"] * {{ color: {text_body} !important; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; display: none !important; }}
    [data-testid="stAppDeployButton"] {{ display: none !important; }}
    [data-testid="stToast"] {{
        background: {surface2} !important; border: 1px solid {border} !important;
        border-radius: 14px !important; color: {text_h} !important;
    }}
    ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
    ::-webkit-scrollbar-track {{ background: {bg}; }}
    ::-webkit-scrollbar-thumb {{ background: {border2}; border-radius: 99px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {PRIMARY_COLOR}; }}
    .stApp, .stApp p, .stApp span, .stApp div {{ color: {text_body} !important; }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: {text_h} !important; }}
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span {{ color: {text_body} !important; }}
    [data-baseweb="input"] input, .stTextInput input {{
        background: {input_bg} !important; color: {input_col} !important; border-color: {input_bdr} !important;
    }}
    .stTextInput label, .stSelectbox label {{ color: {label_col} !important; }}
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p {{ color: {text_muted} !important; }}
    [data-baseweb="select"] div, [data-baseweb="select"] span {{
        background: {input_bg} !important; color: {input_col} !important;
    }}
    code, pre {{ background: {surface2} !important; color: {text_h} !important; border: 1px solid {border} !important; }}
    /* Kustomisasi khusus login */
    .login-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 10px 0;
    }}
    .login-container .stTextInput {{
        width: 220px !important;
        margin: 0 auto !important;
    }}
    .login-container .stButton {{
        width: 220px !important;
        margin: 0 auto !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# â”€â”€ LOGIN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        icon = "â˜€ï¸" if st.session_state.dark_mode else "ðŸŒ™"
        if st.button(icon, help="Ganti tema", key="login_theme_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1rem;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;letter-spacing:3px;opacity:0.4;margin-bottom:1rem;">FPK CONVERTER</div>
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">ðŸ”</div>
        <h2 style="margin:0 0 0.25rem;">Selamat Datang</h2>
        <p style="opacity:0.5;font-size:0.85rem;">Masukkan PIN untuk melanjutkan</p>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        pin = st.text_input("", type="password", key="login_pin", placeholder="â— â— â— â—", label_visibility="collapsed")
        if st.button("Masuk â†’", key="login_btn", use_container_width=True):
            if pin:
                ok, msg = check_pin(pin)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.login_time = now_wib().isoformat()
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("PIN tidak boleh kosong")
        st.markdown('</div>', unsafe_allow_html=True)

    # Tombol biometrik
    if st.button("â˜ï¸ Sidik Jari / Face ID", key="bio_login", use_container_width=True):
        import streamlit.components.v1 as _comp
        bio_js = """
        <script>
        (async function() {
            if (!window.PublicKeyCredential) {
                alert('Browser tidak support biometrik');
                return;
            }
            try {
                const avail = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
                if (!avail) {
                    alert('Perangkat tidak punya sensor biometrik');
                    return;
                }
                let credId = localStorage.getItem('fpk_cred_id');
                if (!credId) {
                    alert('Belum ada sidik jari terdaftar. Daftarkan dulu di menu Pengaturan.');
                    return;
                }
                const chal2 = new Uint8Array(32);
                crypto.getRandomValues(chal2);
                const rawId = Uint8Array.from(atob(credId), c => c.charCodeAt(0));
                await navigator.credentials.get({
                    publicKey: {
                        challenge: chal2,
                        allowCredentials: [{ type: "public-key", id: rawId }],
                        userVerification: "required",
                        timeout: 60000
                    }
                });
                // Login berhasil, kita set PIN ke input dan submit
                const inputs = window.parent.document.querySelectorAll('input[type="password"]');
                let targetInput = null;
                for (let inp of inputs) {
                    if (inp.id && inp.id.includes('login_pin')) {
                        targetInput = inp;
                        break;
                    }
                }
                if (targetInput) {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(targetInput, '__BIO_OK__');
                    targetInput.dispatchEvent(new window.parent.Event('input', { bubbles: true }));
                }
                const btns = window.parent.document.querySelectorAll('button');
                let targetBtn = null;
                for (let btn of btns) {
                    if (btn.id && btn.id.includes('login_btn')) {
                        targetBtn = btn;
                        break;
                    }
                }
                if (targetBtn) {
                    targetBtn.click();
                } else {
                    alert('Error: tombol login tidak ditemukan');
                }
            } catch (e) {
                if (e.name === 'NotAllowedError') alert('Verifikasi dibatalkan');
                else alert('Error: ' + e.message);
            }
        })();
        </script>
        """
        _comp.html(bio_js, height=0)

    st.markdown('<div style="text-align:center;margin-top:0.5rem;"><span style="font-family:JetBrains Mono,monospace;font-size:0.62rem;opacity:0.35;">v1.0 Â· privasi terlindungi</span></div>', unsafe_allow_html=True)
    st.stop()

# â”€â”€ HELPERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def panggil_api_proses(uf, timeout=60):
    endpoint = f"{API_URL}/api/proses"
    files = {"file": (uf.name, uf.getvalue(), "application/pdf")}
    request_meta = {
        "method": "POST", "url": endpoint,
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
        "data": f"[{len(payload.get('data', []))} baris]",
    }
    df_res = pd.DataFrame(payload["data"])
    return payload, df_res, request_meta, response_meta

def render_result(res, idx=0):
    tingkat = res['tingkat']
    t_lower = tingkat.lower()
    t_label = ("ðŸ¥ Rawat Inap (RITL)" if tingkat == "RITL"
               else "ðŸƒ Rawat Jalan (RJTL)" if tingkat == "RJTL" else tingkat)
    total_rp = f"Rp {res['total']:,.0f}".replace(",", ".")
    jenis = res.get('jenis', 'Reguler')
    jenis_badge = '<span style="background:#fef3c7;border:1.5px solid #f59e0b;color:#92400e;padding:2px 10px;border-radius:40px;font-size:0.58rem;font-weight:800;">ðŸ“Œ Susulan</span>' if jenis == "Susulan" else ""
    _dark = st.session_state.get('dark_mode', True)
    surf = "#1a1a1a" if _dark else "#ffffff"
    bdr  = "#2a2a2a" if _dark else "#e0ddd8"
    shadow = "rgba(0,0,0,0.5)" if _dark else "rgba(0,0,0,0.06)"

    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:8px;background:{surf};border:1px solid {bdr};border-radius:40px;padding:6px 18px;font-size:0.8rem;font-weight:600;font-family:JetBrains Mono,monospace;box-shadow:0 2px 12px {shadow};">ðŸ“„ {res["filename"]} {jenis_badge}</div>',
        unsafe_allow_html=True
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="bento"><div class="label">Jumlah Data</div><div class="value">{res["count"]}</div><div class="sub">SEP records</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="bento"><div class="label">Total Nominal</div><div class="value green">{total_rp}</div><div class="sub">total disetujui</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="bento"><div class="label">Tingkat Pelayanan</div><div class="tingkat-badge {t_lower}">{t_label}</div><div class="sub" style="margin-top:0.5rem;">terdeteksi otomatis dari PDF</div></div>', unsafe_allow_html=True)
    st.divider()

    tab_preview, tab_json = st.tabs(["ðŸ“Š Preview Data", "ðŸ“¦ JSON Mentah"])
    with tab_preview:
        df_prev = res['df'].copy()
        df_prev.insert(0, 'No', range(1, 1 + len(df_prev)))
        df_prev = df_prev[['No', 'No.SEP', 'Disetujui']]
        st.dataframe(df_prev, use_container_width=True, height=280, hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", width=60),
                "No.SEP": st.column_config.TextColumn("No.SEP", width=200),
                "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d", width=150),
            })
    with tab_json:
        data_list = []
        for _, row in res['df'].iterrows():
            data_list.append({
                "type": "data",
                "No.SEP": str(row['No.SEP']),
                "Disetujui": int(row['Disetujui'])
            })
        st.json(data_list)

    dup = res['df'][res['df']['No.SEP'].duplicated(keep=False)]
    if not dup.empty:
        st.warning(f"âš ï¸ **{len(dup['No.SEP'].unique())} No.SEP duplikat ditemukan**")

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        csv = res['df'].to_csv(index=False).encode('utf-8')
        downloaded = st.download_button(label="â¬‡ Download CSV", data=csv,
            file_name=res['filename'], mime="text/csv", key=f"dl_{idx}")
        if downloaded:
            update_log_status(res['filename'], 'Selesai')
            st.toast("âœ… CSV didownload & status diperbarui!", icon="âœ…")
            st.rerun()
    with col2:
        if st.button("Reset", key=f"reset_{idx}"):
            st.session_state.results = []
            st.rerun()

def animasi_terminal_proses(uf, dark: bool):
    acc  = PRIMARY_COLOR
    grn  = SECONDARY
    yel  = ACCENT
    dim  = _PAL["primary_bg"] if dark else _PAL["primary_bg_l"]
    pur  = _PAL["purple"]
    surf = "#080808" if dark else "#fafaf8"
    bdr_pnl = PRIMARY_COLOR + "44"
    txt  = "#e0e0e0" if dark else "#1a1a1a"
    bar_bg = "#1a1a1a" if dark else "#e0e0e0"

    term = st.empty()

    def render(lines, done=False):
        visible = lines[-60:]
        inner = "".join(f'<div style="margin:0 0 1px 0;line-height:1.6;">{l}</div>' for l in visible)
        dot = f'<span style="color:{grn};">â—</span>' if not done else f'<span style="color:{acc};">âœ“</span>'
        label = "LIVE" if not done else "DONE"
        label_col = grn if not done else acc
        term.markdown(f"""
        <div style="background:{surf};border:2px solid {bdr_pnl};border-radius:16px;
                    padding:1rem 1.2rem;font-family:'JetBrains Mono',monospace;
                    font-size:0.74rem;box-shadow:0 8px 30px {PRIMARY_COLOR}22;">
            <div style="color:{PRIMARY_COLOR};font-weight:700;font-size:0.65rem;letter-spacing:2px;
                        border-bottom:1px solid {bdr_pnl};padding-bottom:0.35rem;margin-bottom:0.6rem;
                        display:flex;align-items:center;gap:6px;">
                {dot}&nbsp;API RESPONSE
                <span style="color:{label_col};margin-left:4px;">Â· {label}</span>
            </div>
            <div style="overflow-y:auto;height:280px;scrollbar-width:thin;" id="term-out">
                {inner}
            </div>
        </div>
        <script>
            setTimeout(function(){{
                var el=document.getElementById('term-out');
                if(el) el.scrollTop=el.scrollHeight;
            }},30);
        </script>
        """, unsafe_allow_html=True)

    def ln(text, color=None):
        col = color or txt
        return f'<span style="color:{col};">{text}</span>'

    lines = []
    lines.append(ln(f'$ POST /api/proses', acc))
    lines.append(ln(f'  file   : {uf.name}', dim))
    lines.append(ln(f'  size   : {round(len(uf.getvalue())/1024,1)} KB', dim))
    lines.append(ln(f'  status : connecting...', dim))
    render(lines)

    payload, df_res, req_meta, resp_meta = panggil_api_proses(uf)

    tingkat  = payload.get("tingkat", "FPK")
    jumlah   = payload.get("jumlah", 0)
    total    = payload.get("total", 0)
    duplikat = payload.get("duplikat", [])
    proc_ms  = payload.get("processing_time_ms", 1000) or 1000
    lat_ms   = resp_meta.get("latency_ms", 0)
    filename = payload.get("filename", "")
    sep_list = df_res[["No.SEP", "Disetujui"]].to_dict(orient="records")
    row_count = max(1, jumlah)

    lines[-1] = ln(f'  status : 200 OK Â· {lat_ms}ms', grn)
    lines.append(ln(f'  tingkat: {tingkat}', pur))
    lines.append(ln(f'  jumlah : {jumlah} SEP', grn))
    lines.append(ln(f'  proc   : {proc_ms}ms', acc))
    lines.append(ln('', txt))
    lines.append(ln(
        json.dumps({"type": "metadata", "filename": filename, "tingkat": tingkat,
                    "total_rows": jumlah, "total_nominal": total}),
        txt
    ))
    render(lines)
    time.sleep(0.2)

    WINDOW_SIZE  = 20
    RENDER_EVERY = 0.08
    TARGET_SEC   = max(4.0, row_count * 0.003)

    all_lines = []
    for i, row in enumerate(sep_list):
        no_urut = i + 1
        sep     = str(row["No.SEP"])
        nom     = int(row["Disetujui"])
        data_json = json.dumps({"type": "data", "No.SEP": sep, "Disetujui": nom})
        pct_line  = json.dumps({"type": "progress", "percent": int((no_urut / row_count) * 100)})
        all_lines.append((
            no_urut,
            f'<div style="color:{grn};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{data_json}</div>'
            f'<div style="color:{dim};white-space:nowrap;">{pct_line}</div>'
        ))

    prog = st.empty()
    sep_window = []
    last_render = time.time()
    per_row_sleep = TARGET_SEC / max(1, row_count)

    for i, (no_urut, html_line) in enumerate(all_lines):
        is_last = (i == row_count - 1)
        sep_window.append(html_line)
        if len(sep_window) > WINDOW_SIZE:
            sep_window.pop(0)
        now = time.time()
        if (now - last_render >= RENDER_EVERY) or is_last:
            last_render = now
            pct = 100 if is_last else int((no_urut / row_count) * 100)
            render(lines + sep_window)
            prog.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;'
                f'display:flex;align-items:center;gap:10px;margin-top:6px;">'
                f'<span style="color:{grn};font-weight:700;white-space:nowrap;">'
                f'{no_urut:,}/{row_count:,} SEP</span>'
                f'<div style="flex:1;height:4px;background:{bar_bg};border-radius:4px;">'
                f'<div style="width:{pct}%;height:4px;'
                f'background:linear-gradient(90deg,{acc},{grn});'
                f'border-radius:4px;transition:width 0.06s;"></div></div>'
                f'<span style="color:{"#00ff88" if is_last else acc};font-weight:700;">'
                f'{pct}%</span></div>',
                unsafe_allow_html=True
            )
        time.sleep(per_row_sleep)

    time.sleep(0.5)
    prog.empty()

    total_fmt = f"Rp {total:,}".replace(",", ".")
    footer_lines = list(sep_window)
    done_json = json.dumps({"type": "done", "total_nominal": total, "total_rows": jumlah})
    footer_lines.append(ln(done_json, acc))
    render(lines + footer_lines, done=True)
    time.sleep(0.8)
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

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# HALAMAN UTAMA
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

log_data_for_hero = load_log()
_total_konversi = len(log_data_for_hero)
_total_selesai  = sum(1 for x in log_data_for_hero if x.get('status') == 'Selesai')
_total_pending  = _total_konversi - _total_selesai
_total_nominal  = sum(x['total'] for x in log_data_for_hero)
_nominal_str    = f"Rp {_total_nominal:,.0f}".replace(",", ".")

_PAL          = build_palette()
PRIMARY_COLOR = _PAL["primary"]
SECONDARY     = _PAL["secondary"]
ACCENT        = _PAL["accent"]
inject_css(st.session_state.dark_mode)

# â”€â”€ TOP NAV â”€â”€
st.markdown("""
<div class="top-nav">
    <div class="top-nav-logo"><span>FPK CONVERTER</span></div>
</div>
""", unsafe_allow_html=True)

col_sp_nav, col_theme_nav, col_paint_nav, col_pin_nav, col_logout_nav = st.columns([4, 1, 1, 1, 1])
with col_theme_nav:
    st.markdown('<div class="icon-btn-wrap">', unsafe_allow_html=True)
    icon = st.session_state.get('_toggle_icon', 'â˜€ï¸')
    if st.button(icon, help=st.session_state.get('_toggle_tip', 'Ganti tema'), key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with col_paint_nav:
    st.markdown('<div class="icon-btn-wrap">', unsafe_allow_html=True)
    if st.button("ðŸŽ¨", help="Kustomisasi tampilan", key="open_theme"):
        st.session_state.show_theme_panel = not st.session_state.get("show_theme_panel", False)
        st.session_state.show_pin_form = False
    st.markdown('</div>', unsafe_allow_html=True)
with col_pin_nav:
    st.markdown('<div class="icon-btn-wrap">', unsafe_allow_html=True)
    if st.button("ðŸ”‘", help="Ganti PIN", key="open_pin"):
        st.session_state.show_pin_form = not st.session_state.get("show_pin_form", False)
        st.session_state.show_theme_panel = False
    st.markdown('</div>', unsafe_allow_html=True)
with col_logout_nav:
    st.markdown('<div class="icon-btn-wrap">', unsafe_allow_html=True)
    if st.button("ðŸšª", help="Keluar", key="logout_btn"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# â”€â”€ PANEL TEMA â”€â”€
if st.session_state.get("show_theme_panel"):
    _dark_p = st.session_state.dark_mode
    _bdr_p  = "#2a2a2a" if _dark_p else "#e4e2dd"
    _txt_p  = "#f0f0f0" if _dark_p else "#1a1a1a"
    _mut_p  = "#666"    if _dark_p else "#888"

    tab_warna, tab_section, tab_font = st.tabs(["ðŸŽ¨ Warna", "ðŸ–¼ Section", "ðŸ”¤ Font"])

    with tab_warna:
        st.markdown(f'<div style="font-size:0.68rem;font-weight:700;color:{_mut_p};margin:0.5rem 0 0.4rem;border-left:3px solid {PRIMARY_COLOR};padding-left:8px;">Custom 4 Warna Utama</div>', unsafe_allow_html=True)
        cp1, cp2, cp3, cp4 = st.columns(4)
        with cp1:
            st.caption("Primary")
            new_p = st.color_picker("", st.session_state.c_primary, key="pick_p", label_visibility="collapsed")
        with cp2:
            st.caption("Secondary")
            new_s = st.color_picker("", st.session_state.c_secondary, key="pick_s", label_visibility="collapsed")
        with cp3:
            st.caption("Accent")
            new_a = st.color_picker("", st.session_state.c_accent, key="pick_a", label_visibility="collapsed")
        with cp4:
            st.caption("Purple")
            new_pu = st.color_picker("", st.session_state.c_purple, key="pick_pu", label_visibility="collapsed")

        ba, bb = st.columns([3, 1])
        with ba:
            if st.button("âœ… Terapkan Warna", key="apply_color", use_container_width=True):
                st.session_state.c_primary   = new_p
                st.session_state.c_secondary = new_s
                st.session_state.c_accent    = new_a
                st.session_state.c_purple    = new_pu
                st.rerun()
        with bb:
            if st.button("â†º Reset", key="reset_color", use_container_width=True):
                st.session_state.c_primary   = "#ff6b35"
                st.session_state.c_secondary = "#00c47a"
                st.session_state.c_accent    = "#ffd700"
                st.session_state.c_purple    = "#a78bfa"
                st.rerun()

    with tab_section:
        st.caption("Kosongkan untuk ikut tema dark/light otomatis")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.caption("ðŸ–¼ Background")
            new_bg = st.color_picker("", st.session_state.c_bg or "#0a0a0a", key="pick_bg", label_visibility="collapsed")
            use_bg = st.checkbox("Aktifkan", value=bool(st.session_state.c_bg), key="use_bg")

            st.caption("ðŸ” Navbar/Surface")
            new_nb = st.color_picker("", st.session_state.c_navbar or "#141414", key="pick_nb", label_visibility="collapsed")
            use_nb = st.checkbox("Aktifkan", value=bool(st.session_state.c_navbar), key="use_nb")

            st.caption("ðŸ“‹ Sidebar/Log")
            new_sb = st.color_picker("", st.session_state.c_sidebar or "#141414", key="pick_sb", label_visibility="collapsed")
            use_sb = st.checkbox("Aktifkan", value=bool(st.session_state.c_sidebar), key="use_sb")

        with sc2:
            st.caption("ðŸ¦¸ Header/Hero")
            new_hd = st.color_picker("", st.session_state.c_header or "#141414", key="pick_hd", label_visibility="collapsed")
            use_hd = st.checkbox("Aktifkan", value=bool(st.session_state.c_header), key="use_hd")

            st.caption("ðŸ‘£ Footer BG")
            new_ft = st.color_picker("", st.session_state.c_footer or "#0a0a0a", key="pick_ft", label_visibility="collapsed")
            use_ft = st.checkbox("Aktifkan", value=bool(st.session_state.c_footer), key="use_ft")

            st.caption("ðŸ‘£ Footer Text")
            new_ft_txt = st.color_picker("", st.session_state.c_footer_txt or "#888888", key="pick_ft_txt", label_visibility="collapsed")
            use_ft_txt = st.checkbox("Aktifkan", value=bool(st.session_state.c_footer_txt), key="use_ft_txt")

        sc_a, sc_b = st.columns([3, 1])
        with sc_a:
            if st.button("âœ… Terapkan Section", key="apply_section", use_container_width=True):
                st.session_state.c_bg        = new_bg  if use_bg  else ""
                st.session_state.c_navbar    = new_nb  if use_nb  else ""
                st.session_state.c_sidebar   = new_sb  if use_sb  else ""
                st.session_state.c_header    = new_hd  if use_hd  else ""
                st.session_state.c_footer    = new_ft  if use_ft  else ""
                st.session_state.c_footer_txt= new_ft_txt if use_ft_txt else ""
                st.rerun()
        with sc_b:
            if st.button("â†º Reset", key="reset_section", use_container_width=True):
                for k in ["c_bg","c_navbar","c_sidebar","c_header","c_footer","c_footer_txt"]:
                    st.session_state[k] = ""
                st.rerun()

    with tab_font:
        st.caption("Pilih font untuk seluruh aplikasi")
        font_names = [f[0] for f in _FONT_OPTIONS]
        cols_font  = st.columns(4)
        for i, (fname, fcss) in enumerate(_FONT_OPTIONS):
            with cols_font[i % 4]:
                is_active = (fname == st.session_state.font_body)
                st.markdown(f'<div style="text-align:center;font-family:{fcss};font-size:0.75rem;margin-bottom:2px;font-weight:600;">{fname}</div>', unsafe_allow_html=True)
                if st.button(fname, key=f"font_{fname}", use_container_width=True):
                    st.session_state.font_body = fname
                    st.rerun()

# â”€â”€ PANEL PIN â”€â”€
if st.session_state.get("show_pin_form"):
    with st.expander("ðŸ”‘ Ganti PIN", expanded=True):
        st.info("ðŸ’¡ Ubah nilai **PIN** di **Streamlit Cloud â†’ Settings â†’ Secrets**, lalu klik **Reboot app**.")

# â”€â”€ HERO CARD â”€â”€
st.markdown(f"""
<div class="hero-card">
    <div class="hero-label">FPK Converter Â· v1.0</div>
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

# â”€â”€ 3 TABS â”€â”€
tab_pdf, tab_csv, tab_pengaturan = st.tabs(["ðŸ“„ Konversi PDF â†’ CSV", "ðŸ§® Kalkulator CSV", "ðŸ” Pengaturan"])

with tab_pdf:
    if _api_status == "ok":
        st.caption(f"ðŸŸ¢ Backend API aktif di `{API_URL}`")
    else:
        st.error(f"âš ï¸ Backend API tidak bisa dihubungi: {_api_error}")
        st.caption(
            "Kalau ini deployment Replit, kemungkinan app-nya lagi sleep â€” "
            "buka link API-nya langsung di tab baru dulu buat 'membangunkan', lalu refresh halaman ini."
        )

    _dark_demo = st.session_state.get('dark_mode', True)
    _demo_bg  = "#1a1410" if _dark_demo else "#fff8ec"
    _demo_bdr = "#3a2a14" if _dark_demo else "#f0d9a8"
    _demo_txt = "#f0c674" if _dark_demo else "#7a5a10"

    col_demo_toggle, col_demo_label = st.columns([1, 6])
    with col_demo_toggle:
        st.session_state.demo_mode = st.toggle(
            "Mode Demo", value=st.session_state.demo_mode,
            key="toggle_demo_mode", label_visibility="collapsed"
        )
    with col_demo_label:
        st.markdown(f'<div style="font-size:0.85rem;font-weight:700;padding-top:2px;">ðŸŽ­ Mode Demo {"â€” AKTIF" if st.session_state.demo_mode else ""}</div>', unsafe_allow_html=True)

    if st.session_state.demo_mode:
        st.markdown(
            f'<div style="background:{_demo_bg};border:1px solid {_demo_bdr};border-radius:14px;'
            f'padding:0.9rem 1.1rem;margin:0.5rem 0 1rem;font-size:0.8rem;color:{_demo_txt};">'
            f'âš ï¸ <b>Mode Demo aktif.</b> Data fiktif/acak untuk simulasi.</div>',
            unsafe_allow_html=True
        )
        with st.expander("âš™ï¸ Generator PDF Dummy", expanded=(st.session_state.demo_pdf_bytes is None)):
            colg1, colg2, colg3 = st.columns(3)
            with colg1:
                gen_bulan = st.selectbox("Bulan", ["(acak)"] + BULAN_LIST, index=0, key="gen_bulan")
            with colg2:
                gen_tahun = st.selectbox("Tahun", ["(acak)", 2025, 2026], index=0, key="gen_tahun")
            with colg3:
                gen_tingkat = st.selectbox("Tingkat", ["(acak)"] + TINGKAT_LIST, index=0, key="gen_tingkat")
            gen_jumlah = st.slider("Jumlah baris SEP", min_value=2, max_value=30, value=8, key="gen_jumlah")
            if st.button("ðŸŽ² Generate PDF Dummy", use_container_width=True, key="btn_gen_dummy"):
                tmp_out = "/tmp/_demo_fpk_dummy.pdf"
                info = build_dummy_fpk_pdf(
                    tmp_out,
                    jumlah_baris=gen_jumlah,
                    bulan=None if gen_bulan == "(acak)" else gen_bulan,
                    tahun=None if gen_tahun == "(acak)" else int(gen_tahun),
                    tingkat=None if gen_tingkat == "(acak)" else gen_tingkat,
                )
                with open(tmp_out, "rb") as f:
                    st.session_state.demo_pdf_bytes = f.read()
                st.session_state.demo_pdf_info = info
                st.rerun()
            if st.session_state.demo_pdf_bytes:
                info = st.session_state.demo_pdf_info
                total_fmt = f"Rp {info['total_disetujui']:,}".replace(",", ".")
                st.success(f"âœ… PDF dummy siap â€” {info['tingkat']} Â· {info['bulan'].capitalize()} {info['tahun']} Â· {info['jumlah_baris']} SEP")
                fname_demo = f"DUMMY_FPK_{info['tingkat']}_{info['bulan'].upper()}_{info['tahun']}.pdf"
                st.download_button("â¬‡ Download PDF Dummy", data=st.session_state.demo_pdf_bytes,
                    file_name=fname_demo, mime="application/pdf",
                    use_container_width=True, key="dl_demo_pdf")
        st.divider()

    uploaded_files = st.file_uploader(
        "Upload PDF FPK (bisa lebih dari satu)", type=['pdf'],
        accept_multiple_files=True, label_visibility="collapsed"
    )

    if uploaded_files:
        jenis_data = st.radio("Jenis Data", ["Reguler", "Susulan"], index=0, horizontal=True)
        is_susulan = (jenis_data == "Susulan")
        if st.button("Proses Sekarang", use_container_width=True):
            results = []
            errors = []
            total_f = len(uploaded_files)
            _dark = st.session_state.get('dark_mode', True)
            for i, uf in enumerate(uploaded_files):
                if total_f > 1:
                    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:0.75rem;color:#888;margin-bottom:4px;">FILE {i+1}/{total_f} â€” {uf.name}</div>', unsafe_allow_html=True)
                try:
                    payload, df_res, req_meta, resp_meta = animasi_terminal_proses(uf, dark=_dark)
                    filename = payload['filename']
                    if is_susulan:
                        base, ext = os.path.splitext(filename)
                        filename = f"{base}_SUSULAN{ext}"
                    existing_names = ({x['nama_file'] for x in load_log()} | {r['filename'] for r in results})
                    filename = unique_filename(filename, existing_names)
                    tingkat = payload['tingkat']
                    total   = payload['total']
                    jumlah  = payload['jumlah']
                    results.append({
                        'filename': filename, 'df': df_res, 'total': total,
                        'count': jumlah, 'tingkat': tingkat,
                        'jenis': 'Susulan' if is_susulan else 'Reguler',
                        'api_log': {'request': req_meta, 'response': resp_meta},
                    })
                    entry = {
                        'waktu': now_wib().strftime("%d %b %Y, %H:%M") + " WIB",
                        'nama_file': filename, 'tingkat': tingkat,
                        'jumlah': jumlah, 'total': total,
                        'jenis': 'Susulan' if is_susulan else 'Reguler',
                        'status': 'Belum Diambil', 'waktu_selesai': None,
                    }
                    save_log(entry)
                    if tele_configured():
                        ok_tele, _, msg_id = kirim_notif_telegram(entry)
                        if ok_tele and msg_id:
                            entry['tele_message_id'] = msg_id
                            # Update log dengan message_id
                            log = load_log()
                            for item in log:
                                if item.get('nama_file') == entry['nama_file']:
                                    item['tele_message_id'] = msg_id
                                    break
                            with open(LOG_FILE, "w") as f:
                                json.dump(log[:100], f, ensure_ascii=False, indent=2)
                except RuntimeError as e:
                    msg = e.args[0] if e.args else str(e)
                    errors.append(f"âŒ {uf.name}: {msg}")
                except Exception as e:
                    errors.append(f"âŒ {uf.name}: {e}")
            st.session_state.results = results
            st.session_state.errors  = errors
            st.session_state.show_done = True
            st.rerun()

    if st.session_state.get('show_done'):
        errors  = st.session_state.pop('errors', [])
        results = st.session_state.get('results', [])
        st.session_state.show_done = False
        for err in errors:
            st.error(err)
        if results:
            total_sep = sum(r['count'] for r in results)
            total_nom = sum(r['total'] for r in results)
            nom_fmt   = f"Rp {total_nom:,}".replace(",", ".")
            st.success(f"âœ… {len(results)} file berhasil diproses â€” {total_sep} SEP â€” {nom_fmt}")

    if st.session_state.get('results'):
        results = st.session_state.results
        if len(results) == 1:
            render_result(results[0], idx=0)
        else:
            tab_labels = [f"{'ðŸ¥' if r['tingkat']=='RITL' else 'ðŸƒ'} {r['tingkat']}" for r in results]
            tabs_hasil = st.tabs(tab_labels)
            for i, (tab_h, res) in enumerate(zip(tabs_hasil, results)):
                with tab_h:
                    render_result(res, idx=i)

with tab_csv:
    _dark_c = st.session_state.get('dark_mode', True)
    _surf_c = "#1a1a1a" if _dark_c else "#ffffff"
    _bdr_c  = "#2a2a2a" if _dark_c else "#e0ddd8"
    _txt_c  = "#f0f0f0" if _dark_c else "#1a1a1a"
    _mut_c  = "#777777" if _dark_c else "#888888"

    csv_files = st.file_uploader(
        "Upload CSV hasil konversi", type=["csv"],
        accept_multiple_files=True, key="csv_uploader", label_visibility="collapsed"
    )
    if csv_files:
        rows_per_file = []
        total_grand   = 0
        total_sep_csv = 0
        for cf in csv_files:
            try:
                df_c = pd.read_csv(cf)
                col_d = next((c for c in df_c.columns if 'disetujui' in c.lower()), None)
                if col_d is None:
                    st.warning(f"âš ï¸ {cf.name}: kolom 'Disetujui' tidak ditemukan.")
                    continue
                df_c[col_d] = pd.to_numeric(df_c[col_d].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0)
                subtotal = int(df_c[col_d].sum())
                rows_per_file.append({'nama': cf.name, 'sep': len(df_c), 'subtotal': subtotal})
                total_grand   += subtotal
                total_sep_csv += len(df_c)
            except Exception as e:
                st.error(f"âŒ {cf.name}: {e}")
        if rows_per_file:
            grand_fmt = f"Rp {total_grand:,.0f}".replace(",", ".")
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:0.75rem;margin:1rem 0;">
                <div style="background:{_surf_c};border:1px solid {_bdr_c};border-radius:16px;padding:1rem;font-family:'JetBrains Mono',monospace;min-width:0;">
                    <div style="color:{_mut_c};font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:0.3rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Total File</div>
                    <div style="color:{_txt_c};font-size:1.2rem;font-weight:800;word-break:break-word;">{len(rows_per_file)}</div>
                </div>
                <div style="background:{_surf_c};border:1px solid {_bdr_c};border-radius:16px;padding:1rem;font-family:'JetBrains Mono',monospace;min-width:0;">
                    <div style="color:{_mut_c};font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:0.3rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Total SEP</div>
                    <div style="color:{_txt_c};font-size:1.2rem;font-weight:800;word-break:break-word;">{total_sep_csv:,}</div>
                </div>
                <div style="background:{_surf_c};border:1px solid {_bdr_c};border-radius:16px;padding:1rem;font-family:'JetBrains Mono',monospace;min-width:0;">
                    <div style="color:{_mut_c};font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:0.3rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Grand Total</div>
                    <div style="color:{SECONDARY};font-size:1.2rem;font-weight:800;word-break:break-word;">{grand_fmt}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            for r in rows_per_file:
                st.markdown(f"""
                <div style="background:{_surf_c};border:1px solid {_bdr_c};border-radius:16px;padding:0.75rem 1.2rem;margin-bottom:0.5rem;font-family:'JetBrains Mono',monospace;">
                    <div style="font-weight:700;color:{_txt_c};word-break:break-all;overflow-wrap:anywhere;">ðŸ“„ {r['nama']}</div>
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px;gap:0.5rem;flex-wrap:wrap;">
                        <div style="color:{_mut_c};font-size:0.7rem;white-space:nowrap;">{r['sep']:,} SEP</div>
                        <div style="color:{SECONDARY};font-weight:800;white-space:nowrap;">Rp {r['subtotal']:,}</div>
                    </div>
                </div>
                """.replace(",", "."), unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:{PRIMARY_COLOR};border-radius:20px;padding:1.1rem 1.4rem;margin-top:1rem;display:flex;align-items:center;justify-content:space-between;font-family:'JetBrains Mono',monospace;gap:0.75rem;flex-wrap:wrap;">
                <div style="color:#fff;font-size:0.75rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;">Grand Total Disetujui</div>
                <div style="color:#fff;font-size:1.3rem;font-weight:800;white-space:nowrap;">{grand_fmt}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="border:2px dashed {("#2a2a2a" if _dark_c else "#e0ddd8")};background:{_surf_c};border-radius:20px;padding:2.5rem;text-align:center;margin-top:0.5rem;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">ðŸ“Š</div>
            <div style="font-weight:700;font-size:1rem;margin-bottom:0.3rem;color:{_txt_c};">Upload file CSV di atas</div>
            <div style="color:{_mut_c};font-size:0.85rem;">Bisa multiple file â€” format: No.SEP, Disetujui</div>
        </div>
        """, unsafe_allow_html=True)

# â”€â”€ TAB PENGATURAN â”€â”€
with tab_pengaturan:
    st.markdown("### ðŸ” Pengelolaan Sidik Jari / Face ID")
    st.caption("Kelola autentikasi biometrik untuk login cepat tanpa PIN.")

    import streamlit.components.v1 as _bio_comp

    status_html = """
    <div id="bio_status_container" style="margin: 0.5rem 0; padding: 0.75rem 1rem; border-radius: 12px; border: 1px solid #333;">
        <span id="bio_status_text">ðŸ” Memeriksa status...</span>
    </div>
    <script>
    function updateBioStatus() {
        var el = document.getElementById('bio_status_text');
        var cred = localStorage.getItem('fpk_cred_id');
        if (cred) {
            el.innerHTML = 'âœ… Sidik jari/Face ID sudah terdaftar.';
            el.style.color = '#4ade80';
        } else {
            el.innerHTML = 'âŒ Belum ada data biometrik terdaftar.';
            el.style.color = '#f87171';
        }
    }
    updateBioStatus();
    // Tampilkan pesan dari sessionStorage jika ada
    var msg = sessionStorage.getItem('bio_msg');
    if (msg) {
        var msgEl = document.createElement('div');
        msgEl.style.cssText = 'margin-top: 0.5rem; padding: 0.5rem; border-radius: 8px; background: #1e1e1e; color: #e0e0e0; text-align:center;';
        msgEl.textContent = msg;
        var container = document.getElementById('bio_status_container');
        container.parentNode.insertBefore(msgEl, container.nextSibling);
        sessionStorage.removeItem('bio_msg');
    }
    </script>
    """
    _bio_comp.html(status_html, height=100)

    col_reg, col_del = st.columns(2)
    with col_reg:
        if st.button("ðŸ“Œ Daftarkan Sidik Jari", use_container_width=True, key="bio_register"):
            reg_script = """
            <script>
            (async function() {
                if (!window.PublicKeyCredential) {
                    sessionStorage.setItem('bio_msg', 'âŒ Browser tidak mendukung WebAuthn');
                    location.reload();
                    return;
                }
                try {
                    const avail = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
                    if (!avail) {
                        sessionStorage.setItem('bio_msg', 'âŒ Perangkat tidak memiliki sensor biometrik');
                        location.reload();
                        return;
                    }
                    let credId = localStorage.getItem('fpk_cred_id');
                    if (credId) {
                        if (!confirm('Sidik jari sudah terdaftar. Ingin mendaftar ulang?')) {
                            return;
                        }
                        localStorage.removeItem('fpk_cred_id');
                    }
                    const chal = new Uint8Array(32);
                    crypto.getRandomValues(chal);
                    const reg = await navigator.credentials.create({
                        publicKey: {
                            challenge: chal,
                            rp: { name: "FPK Converter", id: location.hostname },
                            user: {
                                id: new TextEncoder().encode("isfan"),
                                name: "isfan",
                                displayName: "Isfan"
                            },
                            pubKeyCredParams: [
                                { type: "public-key", alg: -7 },
                                { type: "public-key", alg: -257 }
                            ],
                            authenticatorSelection: {
                                authenticatorAttachment: "platform",
                                userVerification: "required"
                            },
                            timeout: 60000
                        }
                    });
                    localStorage.setItem('fpk_cred_id', btoa(String.fromCharCode(...new Uint8Array(reg.rawId))));
                    sessionStorage.setItem('bio_msg', 'âœ… Sidik jari berhasil didaftarkan!');
                    location.reload();
                } catch (e) {
                    let msg = 'âŒ Gagal: ';
                    if (e.name === 'NotAllowedError') msg += 'Dibatalkan oleh user';
                    else if (e.name === 'InvalidStateError') msg += 'Credential sudah ada, coba hapus dulu';
                    else msg += e.message;
                    sessionStorage.setItem('bio_msg', msg);
                    location.reload();
                }
            })();
            </script>
            """
            _bio_comp.html(reg_script, height=0)
            st.info("Proses registrasi dimulai. Ikuti instruksi dari browser.")

    with col_del:
        if st.button("ðŸ—‘ï¸ Hapus Sidik Jari", use_container_width=True, key="bio_delete"):
            del_script = """
            <script>
            if (localStorage.getItem('fpk_cred_id')) {
                localStorage.removeItem('fpk_cred_id');
                sessionStorage.setItem('bio_msg', 'âœ… Data biometrik telah dihapus.');
            } else {
                sessionStorage.setItem('bio_msg', 'â„¹ï¸ Belum ada data biometrik.');
            }
            location.reload();
            </script>
            """
            _bio_comp.html(del_script, height=0)
            st.info("Menghapus data biometrik...")

    st.markdown("---")
    st.markdown("""
    **â„¹ï¸ Cara Penggunaan:**
    - Klik **Daftarkan Sidik Jari** untuk mengaktifkan login biometrik.
    - Setelah terdaftar, pada halaman login cukup klik tombol **Sidik Jari / Face ID** dan verifikasi.
    - Gunakan **Hapus Sidik Jari** untuk menghapus data biometrik yang tersimpan.
    """)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TELEGRAM BOT + AI CHAT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
st.divider()

_dark_tele = st.session_state.get('dark_mode', True)
_surf_tele = "#141414" if _dark_tele else "#ffffff"
_bdr_tele  = "#242424" if _dark_tele else "#e4e2dd"
_txt_tele  = "#f0f0f0" if _dark_tele else "#1a1a1a"
_mut_tele  = "#666"    if _dark_tele else "#888"

_tele_ok  = tele_configured()
_ai_ok    = claude_configured()
_ai_mode  = st.session_state.get("bot_ai_mode", False)

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
    <div style="font-size:0.7rem;font-weight:800;letter-spacing:2px;color:{_mut_tele};
                text-transform:uppercase;border-left:3px solid {PRIMARY_COLOR};
                padding-left:10px;font-family:'JetBrains Mono',monospace;">
        ðŸ¤– {"FPK AI Bot" if _ai_mode else "FPK Bot"}
    </div>
    <div style="display:flex;gap:8px;align-items:center;">
        <span style="font-size:0.65rem;font-family:'JetBrains Mono',monospace;
              color:{'#00c47a' if _tele_ok else '#f87171'};">
            {'â— Telegram' if _tele_ok else 'â—‹ Telegram'}
        </span>
        <span style="font-size:0.65rem;font-family:'JetBrains Mono',monospace;
              color:{'#00c47a' if _ai_ok else '#f87171'};">
            {'â— Claude AI' if _ai_ok else 'â—‹ Claude AI'}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

col_ai_toggle, col_ai_label = st.columns([1, 5])
with col_ai_toggle:
    new_ai_mode = st.toggle("AI", value=_ai_mode, key="toggle_ai_mode", label_visibility="collapsed")
    if new_ai_mode != _ai_mode:
        st.session_state.bot_ai_mode = new_ai_mode
        st.rerun()
with col_ai_label:
    if _ai_mode:
        st.markdown(f'<div style="font-size:0.78rem;font-weight:700;color:{PRIMARY_COLOR};padding-top:2px;">âœ¨ Mode AI Aktif â€” Chat cerdas dengan Groq</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="font-size:0.78rem;color:{_mut_tele};padding-top:2px;">Mode AI â€” Aktifkan untuk chat cerdas (Groq)</div>', unsafe_allow_html=True)

if not _ai_ok and _ai_mode:
    st.warning("âš ï¸ Tambahkan `GROQ_API_KEY` di Secrets untuk mengaktifkan Mode AI.")

if not st.session_state.bot_history:
    st.session_state.bot_history = [
        ("bot", "Assalamualaikum kak! ðŸ˜Š\nGua FPK Bot â€” siap bantu.\nKetik /help untuk perintah, atau aktifkan Mode AI untuk chat cerdas!")
    ]

_log_for_bot = load_log()

# â”€â”€ RENDER BUBBLE CHAT â”€â”€
for role, msg in st.session_state.bot_history[-15:]:
    if role == "bot":
        st.markdown(
            f"""
            <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;">
                <div style="min-width:28px;font-size:1.2rem;">ðŸ¤–</div>
                <div style="background:#1e1e1e;border:1px solid #2a2a2a;color:#e0e0e0;
                            border-radius:12px 12px 12px 4px;padding:8px 12px;
                            max-width:80%;font-size:0.85rem;line-height:1.5;
                            word-break:break-word;">
                    {msg.replace(chr(10), '<br>')}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style="display:flex;align-items:flex-start;justify-content:flex-end;gap:8px;margin-bottom:8px;">
                <div style="background:{PRIMARY_COLOR};color:#fff;
                            border-radius:12px 12px 4px 12px;padding:8px 12px;
                            max-width:80%;font-size:0.85rem;line-height:1.5;
                            word-break:break-word;">
                    {msg.replace(chr(10), '<br>')}
                </div>
                <div style="min-width:28px;font-size:1.2rem;">ðŸ‘¤</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# â”€â”€ INPUT CHAT â”€â”€
with st.container():
    cols = st.columns([6, 1])
    with cols[0]:
        placeholder_text = "Tanya Groq AI..." if _ai_mode else "Ketik pesan atau /help..."
        user_input = st.text_input("", key="chat_input", placeholder=placeholder_text, label_visibility="collapsed")
    with cols[1]:
        send_btn = st.button("âž¤", use_container_width=True)

if send_btn and user_input:
    _msg = user_input.strip()
    if _msg:
        st.session_state.bot_history.append(("user", _msg))
        _cmd_keywords = ["/rekap","/riwayat","/total","/pending","/top","/cari",
                         "/quote","/joke","/help","rekap","riwayat","total",
                         "pending","quote","joke","help","bantuan",
                         "assalamualaikum","halo","hai","hey","kabar"]
        _is_cmd = any(_msg.lower().startswith(k) for k in _cmd_keywords)
        if _ai_mode and _ai_ok and not _is_cmd:
            _hist = [(r, m) for r, m in st.session_state.bot_history[:-1]]
            _reply = chat_with_claude(_hist, _log_for_bot)
        else:
            _reply = handle_bot_command(_msg, _log_for_bot)
        st.session_state.bot_history.append(("bot", _reply))
        st.session_state.chat_input = ""
        st.rerun()

if _tele_ok:
    if st.button("ðŸ“¤ Kirim Rekap ke Telegram", key="bot_send_rekap", use_container_width=True):
        _ok_tele, _msg_tele = kirim_rekap_telegram(_log_for_bot)
        st.session_state["_tele_notif"] = (_ok_tele, _msg_tele)
        st.rerun()

_tele_notif = st.session_state.pop("_tele_notif", None)
if _tele_notif:
    _ok_tele, _msg_tele = _tele_notif
    if _ok_tele:
        st.success(_msg_tele)
    else:
        st.error(_msg_tele)

st.divider()

# â”€â”€ RIWAYAT & REKAP â”€â”€
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
        rekap[period]['total']    += item['total']
        rekap[period]['count']    += item['jumlah']
        rekap[period]['konversi'] += 1
        rekap[period]['tingkats'].add(item.get('tingkat', ''))

    sorted_periods = sorted(rekap.keys(),
        key=lambda x: (x.split()[-1] if len(x.split())>1 else "0000",
                       bulan_order.index(x.split()[0]) if x.split()[0] in bulan_order else 99),
        reverse=True)

    st.markdown("### ðŸ“… Rekap Per Bulan")
    for p in sorted_periods:
        r = rekap[p]
        total_rp = f"Rp {r['total']:,.0f}".replace(",", ".")
        tkt_str  = " Â· ".join(sorted(t for t in r['tingkats'] if t))
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{p}**  \n{r['konversi']}x konversi Â· {r['count']} SEP Â· {tkt_str}")
        with col2:
            st.markdown(f"**{total_rp}**")
        st.divider()

if log_data:
    st.markdown("### ðŸ“Š Rekap Per Periode")
    df_chart = build_chart(log_data)
    if df_chart is not None:
        st.bar_chart(df_chart, use_container_width=True, height=220,
                     color=["#e040fb","#00b0ff", SECONDARY, PRIMARY_COLOR][:len(df_chart.columns)])
    st.divider()

col_title, col_hapus = st.columns([4, 1])
with col_title:
    st.markdown("### ðŸ•“ Riwayat Konversi")
with col_hapus:
    if log_data:
        if st.button("ðŸ—‘ï¸ Hapus", key="hapus_log"):
            hapus_log()
            st.session_state.results = []
            st.rerun()

if not log_data:
    st.info("Belum ada riwayat konversi.")
else:
    for i, item in enumerate(log_data):
        nama_file    = item['nama_file']
        tkt          = item.get('tingkat', '')
        status       = item.get('status', 'Belum Diambil')
        waktu        = item['waktu']
        total_rp     = f"Rp {item['total']:,.0f}".replace(",", ".")
        jumlah_sep   = item['jumlah']
        waktu_selesai = item.get('waktu_selesai', '')

        cols = st.columns([3, 1.2, 1.5, 0.8])
        with cols[0]:
            st.markdown(f"**ðŸ“„ {nama_file}**")
        with cols[1]:
            if tkt:
                st.markdown(f"`{tkt}`")
        with cols[2]:
            if status == "Selesai":
                st.success("âœ… Selesai")
            else:
                st.warning("â³ Belum Diambil")
        with cols[3]:
            if status != "Selesai":
                if st.button("âœ“", key=f"tandai_{i}", help="Tandai selesai"):
                    update_log_status(nama_file, 'Selesai')
                    st.toast("âœ… Status diperbarui!", icon="âœ…")
                    st.rerun()

        detail_cols = st.columns([3, 2])
        with detail_cols[0]:
            st.caption(f"ðŸ•“ {waktu}  Â·  {total_rp}  Â·  {jumlah_sep} SEP")
        with detail_cols[1]:
            if status == "Selesai" and waktu_selesai:
                st.caption(f"ðŸ“¥ {waktu_selesai}")
        st.divider()

# â”€â”€ FOOTER â”€â”€
_dark_ft  = st.session_state.get('dark_mode', True)
_ft_c_bg  = st.session_state.get("c_footer", "")
_ft_c_txt = st.session_state.get("c_footer_txt", "")
_ft_txt1  = _ft_c_txt or ("#888" if _dark_ft else "#555")

st.markdown(f"""
<div class="fpk-footer">
    <div class="fpk-footer-txt">
        Dikembangkan oleh <strong style="color:#6366f1;">Isfan Fajar Anugrah</strong>
    </div>
    <div style="font-size:0.6rem;color:{_ft_txt1};margin-top:0.25rem;">Versi 1.0 Â· 2025 Â· All Rights Reserved</div>
    <div style="display:inline-block;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.1);border-radius:40px;padding:3px 14px;margin-top:0.5rem;">
        <span style="font-size:0.58rem;color:#f87171;">âš ï¸ Hak Cipta Pribadi â€” Dilarang digandakan tanpa izin</span>
    </div>
</div>
""", unsafe_allow_html=True)
