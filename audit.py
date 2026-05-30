import os
import re
import io
import tempfile
import pdfplumber
import pandas as pd
import streamlit as st

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Audit Jaspel BPJS", page_icon="🔍", layout="centered")

# ── CSS (Style Asli Isfan Dipertahankan) ──────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght=300;400;600;700;800&family=JetBrains+Mono:wght=400;600&display=swap');
    * { font-family: 'Sora', sans-serif !important; }
    #MainMenu {visibility:hidden;} footer {visibility:hidden;} header {visibility:hidden;}

    .stApp {
        background-color: #0a0a0f;
        background-image:
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.15), transparent),
            radial-gradient(ellipse 40% 40% at 80% 80%, rgba(139,92,246,0.08), transparent);
    }
    .block-container { padding-top: 2rem; max-width: 720px; }

    .app-header { text-align:center; padding:3rem 2rem 2rem; margin-bottom:0.5rem; }
    .app-header .badge {
        display:inline-block;
        background:rgba(99,102,241,0.15);
        border:1px solid rgba(99,102,241,0.3);
        color:#818cf8; font-size:11px; font-weight:600;
        letter-spacing:2px; text-transform:uppercase;
        padding:6px 16px; border-radius:100px; margin-bottom:1.2rem;
    }
    .app-header h1 {
        font-size:2.8rem !important; font-weight:800 !important;
        color:#f1f5f9 !important; line-height:1.1 !important;
        margin:0 !important; letter-spacing:-1.5px;
    }
    .app-header h1 span {
        background:linear-gradient(135deg,#6366f1,#a78bfa);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    }
    .app-header p { color:#64748b; font-size:0.95rem; margin-top:0.8rem; font-weight:300; }

    .login-container {
        background:rgba(255,255,255,0.03);
        border:1px solid rgba(255,255,255,0.07);
        border-radius:20px; padding:2.5rem;
        backdrop-filter:blur(10px); margin-top:1rem;
    }

    .stTextInput > div > div > input {
        background:rgba(255,255,255,0.04) !important;
        border:1px solid rgba(255,255,255,0.1) !important;
        border-radius:12px !important; color:#f1f5f9 !important;
        padding:14px 18px !important; font-size:0.95rem !important;
        font-family:'JetBrains Mono',monospace !important;
        letter-spacing:4px !important; transition:all 0.2s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color:rgba(99,102,241,0.6) !important;
        box-shadow:0 0 0 3px rgba(99,102,241,0.1) !important;
        background:rgba(99,102,241,0.05) !important;
    }
    .stTextInput label {
        color:#94a3b8 !important; font-size:0.8rem !important;
        font-weight:600 !important; letter-spacing:1px !important;
        text-transform:uppercase !important;
    }

    .stFileUploader > div {
        background:rgba(255,255,255,0.02) !important;
        border:1.5px dashed rgba(99,102,241,0.35) !important;
        border-radius:16px !important; padding:1.5rem !important;
        transition:all 0.3s !important;
    }
    .stFileUploader > div:hover {
        border-color:rgba(99,102,241,0.7) !important;
        background:rgba(99,102,241,0.05) !important;
    }
    .stFileUploader label { color:#94a3b8 !important; }

    .stButton > button {
        background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%) !important;
        color:white !important; border:none !important;
        border-radius:12px !important; height:52px !important;
        font-size:0.9rem !important; font-weight:700 !important;
        letter-spacing:0.5px !important; transition:all 0.2s ease !important;
        box-shadow:0 4px 20px rgba(99,102,241,0.25) !important;
    }
    .stButton > button:hover {
        transform:translateY(-2px) !important;
        box-shadow:0 8px 30px rgba(99,102,241,0.4) !important;
        filter:brightness(1.1) !important;
    }

    .stDownloadButton > button {
        background:rgba(16,185,129,0.1) !important;
        border:1px solid rgba(16,185,129,0.3) !important;
        color:#34d399 !important;
        box-shadow:0 4px 20px rgba(16,185,129,0.1) !important;
    }
    .stDownloadButton > button:hover {
        background:rgba(16,185,129,0.2) !important;
        border-color:rgba(16,185,129,0.5) !important;
        color:#6ee7b7 !important;
    }

    .metric-card {
        background:rgba(255,255,255,0.03);
        border:1px solid rgba(255,255,255,0.07);
        border-radius:16px; padding:1.2rem 1.5rem;
        position:relative; overflow:hidden;
    }
    .metric-card::before {
        content:''; position:absolute;
        top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg,#6366f1,#8b5cf6);
    }
    .metric-card.green::before { background:linear-gradient(90deg,#10b981,#34d399); }
    .metric-card.yellow::before { background:linear-gradient(90deg,#f59e0b,#fbbf24); }
    .metric-card.red::before { background:linear-gradient(90deg,#ef4444,#f87171); }
    .metric-label { color:#475569; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; margin-bottom:0.4rem; }
    .metric-value { color:#f1f5f9; font-size:1.3rem; font-weight:800; letter-spacing:-0.5px; }
    .metric-value.green { color:#34d399; }
    .metric-value.yellow { color:#fbbf24; }
    .metric-value.red { color:#f87171; }
    .metric-sub { color:#334155; font-size:0.72rem; margin-top:0.3rem; font-family:'JetBrains Mono',monospace; }

    .kantong-table {
        width:100%; border-collapse:collapse; margin-top:0.5rem;
    }
    .kantong-table th {
        background:rgba(99,102,241,0.15); color:#818cf8;
        font-size:11px; font-weight:700; letter-spacing:1.5px;
        text-transform:uppercase; padding:10px 14px; text-align:left;
        border-bottom:1px solid rgba(99,102,241,0.2);
    }
    .kantong-table td {
        padding:10px 14px; color:#cbd5e1; font-size:0.85rem;
        border-bottom:1px solid rgba(255,255,255,0.04);
    }
    .kantong-table tr:last-child td {
        background:rgba(99,102,241,0.08);
        color:#f1f5f9; font-weight:700;
        border-top:1px solid rgba(99,102,241,0.3);
        border-bottom:none;
    }
    .kantong-table tr:hover td { background:rgba(255,255,255,0.02); }
    .kantong-table td.nominal { font-family:'JetBrains Mono',monospace; text-align:right; }
    .kantong-table th.nominal { text-align:right; }

    .section-title {
        color:#94a3b8; font-size:0.75rem; font-weight:700;
        letter-spacing:2px; text-transform:uppercase;
        margin:1.5rem 0 0.8rem; display:flex; align-items:center; gap:8px;
    }
    .section-title::after {
        content:''; flex:1; height:1px;
        background:rgba(255,255,255,0.06);
    }

    .info-box {
        background:rgba(99,102,241,0.08);
        border:1px solid rgba(99,102,241,0.2);
        border-radius:12px; padding:1rem 1.2rem;
        color:#94a3b8; font-size:0.85rem; margin:0.5rem 0;
    }
    .warn-box {
        background:rgba(245,158,11,0.08);
        border:1px solid rgba(245,158,11,0.25);
        border-radius:12px; padding:1rem 1.2rem;
        color:#fbbf24; font-size:0.85rem; margin:0.5rem 0;
    }
    .ok-box {
        background:rgba(16,185,129,0.08);
        border:1px solid rgba(16,185,129,0.25);
        border-radius:12px; padding:1rem 1.2rem;
        color:#34d399; font-size:0.85rem; margin:0.5rem 0;
    }

    hr { border-color:rgba(255,255,255,0.06) !important; margin:1.5rem 0 !important; }

    .stDataFrame { border-radius:14px !important; overflow:hidden !important; border:1px solid rgba(255,255,255,0.07) !important; }
    [data-testid="stDataFrameResizable"] { background:rgba(255,255,255,0.02) !important; }
</style>
""", unsafe_allow_html=True)

# ── LOGIN ────────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("""
        <div class="app-header">
            <div class="badge">🔍 Audit Jaspel</div>
            <h1>Audit <span>Jaspel BPJS</span></h1>
            <p>Masukkan PIN untuk mengakses aplikasi</p>
        </div>
    """, unsafe_allow_html=True)
    pin = st.text_input("PIN AKSES", type="password", placeholder="••••")
    if st.button("Masuk →", use_container_width=True):
        if pin == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("❌ PIN salah.")
    st.stop()

# ── KONSTANTA KANTONG BESAR (Sesuai Bab B Dokumentasi Halaman 2) ─────────────
KANTONG = {
    "dr. Operator & dr. Spesialis": 34.29,
    "dr. Umum":                      6.12,
    "Perawat":                       24.81,
    "Management Struktural":         12.11,
    "Petugas Khusus":                 7.93,
    "Farmasi":                        4.12,
    "Management Administrasi":       10.62,
}

# ── HELPER ──────────────────────────────────────────────────────────────────
def fmt_rp(val: float) -> str:
    return f"Rp {val:,.0f}".replace(",", ".")

def extract_pdf(uploaded_file):
    """Mengekstrak No.SEP, Biaya Riil RS, dan Disetujui dari PDF Resmi BPJS."""
    pattern = re.compile(r'\d+\s+(1028R\S+)\s+([\d-]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)')
    rows = []
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
        
    try:
        with pdfplumber.open(tmp_path) as pdf:
            bulan_pel = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                if not bulan_pel:
                    m = re.search(r"Bulan Pelayanan\s*:\s*(.+)", text)
                    if m:
                        bulan_pel = m.group(1).strip()
                for m in pattern.finditer(text):
                    rows.append({
                        "No.SEP": m.group(1).strip(),
                        "Biaya Riil RS": int(m.group(3).replace(",", "")),
                        "Disetujui": int(m.group(5).replace(",", ""))
                    })
    except Exception as e:
        return None, None, str(e)
    finally:
        os.unlink(tmp_path)
        
    if not rows:
        return None, None, "Tidak ada data SEP yang valid ditemukan di PDF."
        
    df = pd.DataFrame(rows).drop_duplicates(subset=["No.SEP"]).reset_index(drop=True)
    return df, bulan_pel, None

# ── REVISI FUNGSI RUMUS JASPEL [SESUAI HALAMAN 11-12 DOKUMEN JASPEL] ─────────
def hitung_jaspel(df: pd.DataFrame, tarif: float, naik_kelas: float) -> dict:
    """Menghitung Jaspel murni berdasarkan aturan Bab D Dokumentasi Jaspel."""
    jasa_list = []
    selisih_list = []
    jaspel_sel_list = []
    total_jaspel_list = []
    
    for idx, row in df.iterrows():
        cbg = float(row["Disetujui"])
        biaya_riil = float(row["Biaya Riil RS"])
        
        # 1. Jasa Pelayanan Utama (30% RI atau 35% RJ)
        jasa = cbg * tarif
        
        # 2. Selisih Efisiensi = Klaim INA CBG - Biaya Riil RS (Jika minus dihitung 0)
        selisih_cbg = max(0.0, cbg - biaya_riil)
        
        # 3. Jaspel Selisih (Bonus Efisiensi 5%)
        jaspel_selisih = selisih_cbg * 0.05
        
        # 4. Total Jaspel per Pasien = Utama + Bonus Efisiensi
        total_jaspel = jasa + jaspel_selisih
        
        jasa_list.append(jasa)
        selisih_list.append(selisih_cbg)
        jaspel_sel_list.append(jaspel_selisih)
        total_jaspel_list.append(total_jaspel)
        
    subtotal = sum(total_jaspel_list)
    final_total = subtotal + naik_kelas
    
    df_out = df.copy()
    df_out["Jasa Pelayanan Utama"] = jasa_list
    df_out["Selisih CBG"] = selisih_list
    df_out["Jaspel Selisih (5%)"] = jaspel_sel_list
    df_out["Total Jaspel Bersih"] = total_jaspel_list
    
    return {
        "n_sep": len(df),
        "total_cbg": float(df["Disetujui"].sum()),
        "total_biaya": float(df["Biaya Riil RS"].sum()),
        "jasa_pel": sum(jasa_list),
        "jaspel_selisih": sum(jaspel_sel_list),
        "naik_kelas": naik_kelas,
        "subtotal": subtotal,
        "final": final_total,
        "df_detail": df_out
    }

# ── UI UTAMA ─────────────────────────────────────────────────────────────────
st.markdown("""
    <div class="app-header">
        <div class="badge">🔍 Verifikator Internal</div>
        <h1>Audit <span>Jaspel BPJS</span></h1>
        <p>Berdasarkan Aturan Resmi Dokumentasi Jaspel Halaman 11-12</p>
    </div>
""", unsafe_allow_html=True)

st.markdown('<div class="info-box">📋 <b>Cara Kerja:</b> Upload berkas PDF FPK Lampiran BPJS. Aplikasi akan mengurai data tagihan dan menghitung Jaspel Bersih + Bonus Efisiensi 5% sesuai dengan dokumentasi standar rumah sakit.</div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">📁 Upload PDF Berkas FPK BPJS</div>', unsafe_allow_html=True)

col_ri, col_rj = st.columns(2)
with col_ri:
    st.markdown("**🏥 Kelompok Rawat Inap (RITL)**")
    st.caption("Tarif Porsi Jaspel: **30%**")
    up_ri = st.file_uploader("PDF Lampiran Rawat Inap", type=["pdf"], key="up_ri")
    nk_ri = st.number_input("Jaspel Naik Kelas RI (Rp)", min_value=0, value=0, step=50000)

with col_rj:
    st.markdown("**🚶 Kelompok Rawat Jalan (RJTL)**")
    st.caption("Tarif Porsi Jaspel: **35%**")
    up_rj = st.file_uploader("PDF Lampiran Rawat Jalan", type=["pdf"], key="up_rj")
    nk_rj = st.number_input("Jaspel Naik Kelas RJ (Rp)", min_value=0, value=0, step=50000)

st.markdown('<div class="section-title">⚖️ Pembanding Hasil SIMRS Icha</div>', unsafe_allow_html=True)
icha_val = st.number_input("Input Nominal Total Jaspel Layar SIMRS Icha (Rp)", min_value=0, value=0, step=100000)

st.markdown("---")
btn = st.button("🚀 Jalankan Audit Perbandingan Data", type="primary", use_container_width=True)

if not btn:
    st.stop()

if up_ri is None and up_rj is None:
    st.warning("⚠️ Silakan upload minimal salah satu berkas PDF (RI atau RJ) untuk dihitung.")
    st.stop()

# ── EKSTRAK & PROSES DATA ────────────────────────────────────────────────────
hasil_ri = None
hasil_rj = None
bulan_info = ""

if up_ri:
    with st.spinner("Mengolah data Rawat Inap..."):
        df_ri, bl, err = extract_pdf(up_ri)
        if err: st.error(f"Gagal memproses PDF RI: {err}")
        else:
            if bl: bulan_info = bl
            hasil_ri = hitung_jaspel(df_ri, 0.30, float(nk_ri))
            st.success(f"✅ Berhasil menarik {hasil_ri['n_sep']:,} data Pasien Rawat Inap.")

if up_rj:
    with st.spinner("Mengolah data Rawat Jalan..."):
        df_rj, bl, err = extract_pdf(up_rj)
        if err: st.error(f"Gagal memproses PDF RJ: {err}")
        else:
            if bl: bulan_info = bl
            hasil_rj = hitung_jaspel(df_rj, 0.35, float(nk_rj))
            st.success(f"✅ Berhasil menarik {hasil_rj['n_sep']:,} data Pasien Rawat Jalan.")

if hasil_ri is None and hasil_rj is None:
    st.error("❌ Data kosong atau tidak ada yang berhasil diekstrak.")
    st.stop()

# ── AKUMULASI GLOBAL ─────────────────────────────────────────────────────────
total_ri = hasil_ri["final"] if hasil_ri else 0.0
total_rj = hasil_rj["final"] if hasil_rj else 0.0
total_all = total_ri + total_rj
icha_float = float(icha_val)

# ── DISPLAY METRIK RINGKASAN ─────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Hasil Ringkasan Perhitungan Mandiri</div>', unsafe_allow_html=True)
if bulan_info:
    st.caption(f"📅 **Periode Pelayanan Dokumen:** {bulan_info}")

cols = st.columns(4)
with cols[0]: st.markdown(f'<div class="metric-card"><div class="metric-label">Pasien RI</div><div class="metric-value">{hasil_ri["n_sep"] if hasil_ri else 0:,}</div></div>', unsafe_allow_html=True)
with cols[1]: st.markdown(f'<div class="metric-card"><div class="metric-label">Pasien RJ</div><div class="metric-value">{hasil_rj["n_sep"] if hasil_rj else 0:,}</div></div>', unsafe_allow_html=True)
with cols[2]: st.markdown(f'<div class="metric-card green"><div class="metric-label">Porsi RI</div><div class="metric-value green">{fmt_rp(total_ri)}</div></div>', unsafe_allow_html=True)
with cols[3]: st.markdown(f'<div class="metric-card green"><div class="metric-label">Porsi RJ</div><div class="metric-value green">{fmt_rp(total_rj)}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
c1.markdown(f'<div class="metric-card green"><div class="metric-label">💰 Jaspel Bersih Seharusnya</div><div class="metric-value green">{fmt_rp(total_all)}</div><div class="metric-sub">Sesuai Dokumen Resmi Hal. 11-12</div></div>', unsafe_allow_html=True)

if icha_float > 0:
    selisih = total_all - icha_float
    cls = "green" if abs(selisih) < 1000 else ("yellow" if selisih > 0 else "red")
    status_teks = "Lebih Besar (Sistem Icha nge-drop data)" if selisih > 0 else "Lebih Kecil"
    c2.markdown(f'<div class="metric-card {cls}"><div class="metric-label">⚖️ Selisih Hitungan vs ICHA</div><div class="metric-value {cls}">{fmt_rp(abs(selisih))}</div><div class="metric-sub">{status_teks}</div></div>', unsafe_allow_html=True)

# ── LOGIC VALIDASI / SENSOR BUALAN VENDOR ────────────────────────────────────
if icha_float > 0:
    st.markdown('<div class="section-title">📢 Analisis Validasi Sistem</div>', unsafe_allow_html=True)
    if selisih > 1000:
        st.markdown(f'<div class="warn-box">⚠️ <b>Ditemukan Selisih Ghaib!</b> Hasil hitung resmi berdasarkan berkas BPJS bernilai <b>{fmt_rp(total_all)}</b> sedangkan layar Icha mengunci data di angka <b>{fmt_rp(icha_float)}</b>. Alasan vendor mengenai "belum diproses rumus" tidak terbukti, karena rumus di atas sudah menyertakan bonus efisiensi 5% sesuai kesepakatan hitam di atas putih. Fix kodingan backend vendor yang nge-bug ngebatesin query limit!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ok-box">✅ Angka sinkron dengan toleransi wajar. Data pelayanan klop.</div>', unsafe_allow_html=True)

# ── DETAIL PER SEP EXPANDER ──────────────────────────────────────────────────
st.markdown('<div class="section-title">📄 Rincian Data Per Transaksi SEP Pasien</div>', unsafe_allow_html=True)
if hasil_ri:
    with st.expander("🔍 Lihat Detail Perhitungan Rawat Inap"):
        st.dataframe(hasil_ri["df_detail"], use_container_width=True, hide_index=True)
if hasil_rj:
    with st.expander("🔍 Lihat Detail Perhitungan Rawat Jalan"):
        st.dataframe(hasil_rj["df_detail"], use_container_width=True, hide_index=True)

# ── DISTRIBUSI KANTONG BESAR ──────────────────────────────────────────────────
st.markdown('<div class="section-title">🏦 Rekap Distribusi Alokasi Kantong Besar</div>', unsafe_allow_html=True)
rows_kb = []
baris_html = ""
for nama, pct in KANTONG.items():
    val_ri = total_ri * pct / 100
    val_rj = total_rj * pct / 100
    val_tot = val_ri + val_rj
    rows_kb.append((nama, val_ri, val_rj, val_tot))
    
    baris_html += f'<tr><td>{nama} ({pct}%)</td><td class="nominal">{fmt_rp(val_ri)}</td><td class="nominal">{fmt_rp(val_rj)}</td><td class="nominal">{fmt_rp(val_tot)}</td></tr>'

st.markdown(f"""
<table class="kantong-table">
    <thead><tr><th>Komponen Alokasi Jasa</th><th class="nominal">Porsi RI</th><th class="nominal">Porsi RJ</th><th class="nominal">Sub Total</th></tr></thead>
    <tbody>{baris_html}<tr><td><b>TOTAL DIBAGIKAN</b></td><td class="nominal"><b>{fmt_rp(total_ri)}</b></td><td class="nominal"><b>{fmt_rp(total_rj)}</b></td><td class="nominal"><b>{fmt_rp(total_all)}</b></td></tr></tbody>
</table>
""", unsafe_allow_html=True)

# ── DOWNLOAD EXCEL REKAP AUDIT ───────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">⬇️ Export Laporan Hasil Audit Resmi</div>', unsafe_allow_html=True)

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    df_kb = pd.DataFrame(rows_kb, columns=["Komponen Jasa Pelayanan", "Porsi RI", "Porsi RJ", "Total Alokasi"])
    df_kb.to_excel(w, index=False, sheet_name="Kantong Besar")
    if hasil_ri: hasil_ri["df_detail"].to_excel(w, index=False, sheet_name="Detail_Pasien_RI")
    if hasil_rj: hasil_rj["df_detail"].to_excel(w, index=False, sheet_name="Detail_Pasien_RJ")

st.download_button(
    "⬇️ Download File Excel Laporan Audit (.xlsx)",
    data=buf.getvalue(),
    file_name="LAPORAN_AUDIT_INTERNAL_JASPEL.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)
