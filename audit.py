import os
import re
import io
import tempfile
import pdfplumber
import pandas as pd
import streamlit as st

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Audit Jaspel BPJS", page_icon="🔍", layout="centered")

# ── CSS (Tetap Dipertahankan Sesuai Style Isfan) ──────────────────────────────
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

# ── KONSTANTA KANTONG BESAR ──────────────────────────────────────────────────
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
    """Extract No.SEP, Biaya Riil RS, Disetujui dari PDF FPK BPJS."""
    pattern = re.compile(
        r'\d+\s+(1028R\S+)\s+([\d-]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)'
    )
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
                        "No.SEP":       m.group(1).strip(),
                        "Biaya Riil RS": int(m.group(3).replace(",", "")),
                        "Disetujui":    int(m.group(5).replace(",", "")),
                    })
    except Exception as e:
        return None, None, str(e)
    finally:
        os.unlink(tmp_path)

    if not rows:
        return None, None, "Tidak ada data SEP ditemukan."

    df = pd.DataFrame(rows).drop_duplicates(subset=["No.SEP"]).reset_index(drop=True)
    return df, bulan_pel, None

def hitung_jaspel(df: pd.DataFrame, tarif: float, naik_kelas: float, df_icha_detail=None) -> dict:
    """Hitung jaspel per SEP sesuai rumus ICHA + Join Nama Pasien & No RM jika ada."""
    jasa_list, selisih_list, jaspel_sel_list, jaspel_list = [], [], [], []
    for _, row in df.iterrows():
        cbg   = float(row["Disetujui"])
        biaya = float(row["Biaya Riil RS"])
        jasa  = cbg * tarif
        sel   = max(0.0, cbg - biaya)
        jsel  = sel * 0.05
        jasa_list.append(jasa)
        selisih_list.append(sel)
        jaspel_sel_list.append(jsel)
        jaspel_list.append(jasa + jsel)

    subtotal = sum(jaspel_list)
    final    = subtotal + naik_kelas

    df_out = df.copy()
    df_out["Jasa Pelayanan"]  = jasa_list
    df_out["Selisih CBG"]     = selisih_list
    df_out["Jaspel Selisih"]  = jaspel_sel_list
    df_out["Total Jaspel"]    = jaspel_list

    # PROSES JOIN NAMA PASIEN & NO RM JIKA FILE DETAIL ICHA DIUPLOAD [MODIFIKASI]
    if df_icha_detail is not None:
        # Standardisasi nama kolom dan string No.SEP agar klop pas di-merge
        df_icha_detail.columns = df_icha_detail.columns.str.strip().str.upper()
        df_out['No.SEP'] = df_out['No.SEP'].astype(str).str.strip()
        
        # Cari kolom SEP di file Icha (biasanya bernama NO.SEP, NO_SEP, atau SEP)
        col_sep_icha = [c for c in df_icha_detail.columns if 'SEP' in c]
        col_nama_icha = [c for c in df_icha_detail.columns if 'NAMA' in c]
        col_rm_icha = [c for c in df_icha_detail.columns if 'RM' in c or 'REKAP' in c or 'MEDIS' in c]
        
        if col_sep_icha and col_nama_icha:
            df_icha_sub = df_icha_detail.rename(columns={
                col_sep_icha[0]: 'No.SEP',
                col_nama_icha[0]: 'Nama Pasien',
                col_rm_icha[0] if col_rm_icha else df_icha_detail.columns[0]: 'No. RM'
            })
            df_icha_sub['No.SEP'] = df_icha_sub['No.SEP'].astype(str).str.strip()
            
            # Kita amankan kolom yang mau ditarik aja
            kolom_tarik = ['No.SEP', 'Nama Pasien']
            if col_rm_icha:
                kolom_tarik.append('No. RM')
                
            df_icha_sub = df_icha_sub[kolom_tarik].drop_duplicates(subset=['No.SEP'])
            df_out = pd.merge(df_out, df_icha_sub, on='No.SEP', how='left')
            
            # Isi string kosong kalau pas di-merge datanya tidak ketemu
            df_out['Nama Pasien'] = df_out['Nama Pasien'].fillna("⚠️ GAK KETEMU DI ICHA")
            if 'No. RM' in df_out.columns:
                df_out['No. RM'] = df_out['No. RM'].fillna("------")

    return {
        "n_sep":          len(df),
        "total_cbg":      float(df["Disetujui"].sum()),
        "total_biaya":    float(df["Biaya Riil RS"].sum()),
        "tarif":          tarif,
        "jasa_pel":       sum(jasa_list),
        "jaspel_selisih": sum(jaspel_sel_list),
        "naik_kelas":     naik_kelas,
        "subtotal":       subtotal,
        "final":          final,
        "df_detail":      df_out,
    }

# ── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("""
    <div class="app-header">
        <div class="badge">🔍 Audit Tools</div>
        <h1>Audit <span>Jaspel BPJS</span></h1>
        <p>Upload PDF FPK → hitung jaspel akurat per SEP → bandingkan dengan ICHA</p>
    </div>
""", unsafe_allow_html=True)

st.markdown('<div class="info-box">📋 Upload PDF <b>Rincian Data Hasil Verifikasi</b> BPJS serta <b>File CSV Hasil Export Detail ICHA</b>. Sistem akan otomatis melakukan VLOOKUP untuk mencocokkan Nominal Jaspel dengan Nama & No.RM Pasien.</div>', unsafe_allow_html=True)

# ── UPLOAD FILE UTAMA ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📁 Upload PDF FPK BPJS</div>', unsafe_allow_html=True)

col_ri, col_rj = st.columns(2)
with col_ri:
    st.markdown("**🏥 Rawat Inap (RI)**")
    st.caption("Tarif BPJS: **30%**")
    up_ri = st.file_uploader("PDF FPK Rawat Inap", type=["pdf"], key="up_ri")
    nk_ri = st.number_input("Jaspel Naik Kelas RI (Rp)", min_value=0, value=0, step=100_000, key="nk_ri")

with col_rj:
    st.markdown("**🚶 Rawat Jalan (RJ)**")
    st.caption("Tarif BPJS: **35%**")
    up_rj = st.file_uploader("PDF FPK Rawat Jalan", type=["pdf"], key="up_rj")
    nk_rj = st.number_input("Jaspel Naik Kelas RJ (Rp)", min_value=0, value=0, step=100_000, key="nk_rj")

# ── UPLOAD CSV DETIL ICHA [BARU] ─────────────────────────────────────────────
st.markdown('<div class="section-title">👤 Data Pasien SIMRS Icha (VLOOKUP Otomatis)</div>', unsafe_allow_html=True)
up_icha_csv = st.file_uploader("Upload CSV Detail Pasien dari ICHA (Optional untuk sinkron Nama & No.RM)", type=["csv"], key="up_icha_csv")

st.markdown('<div class="section-title">⚖️ Perbandingan Global</div>', unsafe_allow_html=True)
icha_val = st.number_input(
    "Nilai Jaspel Global ICHA (Rp) — opsional",
    min_value=0, value=0, step=100_000, key="icha_val"
)

st.markdown("---")
btn = st.button("🧮  Jalankan Audit & Pencocokan Pasien", type="primary", use_container_width=True)

if not btn:
    st.stop()

# ── VALIDASI ────────────────────────────────────────────────────────────────
if up_ri is None and up_rj is None:
    st.warning("⚠️ Upload minimal satu PDF FPK (RI atau RJ).")
    st.stop()

# Ngebaca data CSV Icha detail terlebih dahulu jika di-upload
df_icha_detail = None
if up_icha_csv is not None:
    try:
        df_icha_detail = pd.read_csv(up_icha_csv)
    except Exception as e:
        st.error(f"❌ Gagal membaca CSV Detail ICHA: {e}")

# ── EKSTRAK PDF & PROSES HITUNG ──────────────────────────────────────────────
hasil_ri = hasil_rj = None
bulan_info = ""

if up_ri:
    with st.spinner("📄 Membaca PDF Rawat Inap..."):
        df_ri, bl, err = extract_pdf(up_ri)
    if err:
        st.error(f"❌ PDF RI: {err}")
    else:
        if bl: bulan_info = bl
        hasil_ri = hitung_jaspel(df_ri, 0.30, float(nk_ri), df_icha_detail)
        st.success(f"✅ RI: {hasil_ri['n_sep']:,} SEP berhasil diverifikasi")

if up_rj:
    with st.spinner("📄 Membaca PDF Rawat Jalan..."):
        df_rj, bl, err = extract_pdf(up_rj)
    if err:
        st.error(f"❌ PDF RJ: {err}")
    else:
        if bl: bulan_info = bl
        hasil_rj = hitung_jaspel(df_rj, 0.35, float(nk_rj), df_icha_detail)
        st.success(f"✅ RJ: {hasil_rj['n_sep']:,} SEP berhasil diverifikasi")

if hasil_ri is None and hasil_rj is None:
    st.error("❌ Tidak ada data yang berhasil diekstrak.")
    st.stop()

# ── TOTAL ────────────────────────────────────────────────────────────────────
total_ri  = hasil_ri["final"] if hasil_ri else 0.0
total_rj  = hasil_rj["final"] if hasil_rj else 0.0
total_all = total_ri + total_rj
icha_float = float(icha_val)

# ── RINGKASAN METRIK ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Ringkasan Perhitungan</div>', unsafe_allow_html=True)
if bulan_info: st.caption(f"📅 Periode Pelayanan: **{bulan_info}**")

cols = st.columns(4)
metrics = [
    ("SEP RI",       f"{hasil_ri['n_sep']:,}" if hasil_ri else "—",       ""),
    ("SEP RJ",       f"{hasil_rj['n_sep']:,}" if hasil_rj else "—",       ""),
    ("Jaspel RI",    fmt_rp(total_ri) if hasil_ri else "—",               "green"),
    ("Jaspel RJ",    fmt_rp(total_rj) if hasil_rj else "—",               "green"),
]
for col, (label, val, cls) in zip(cols, metrics):
    col.markdown(f'<div class="metric-card {cls}"><div class="metric-label">{label}</div><div class="metric-value {cls}">{val}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
c1.markdown(f'<div class="metric-card green"><div class="metric-label">💰 Total Jaspel Seharusnya</div><div class="metric-value green">{fmt_rp(total_all)}</div><div class="metric-sub">Sesuai Aturan Jaspel.pdf</div></div>', unsafe_allow_html=True)

if icha_float > 0:
    sel = total_all - icha_float
    cls = "green" if abs(sel) < 1_000_000 else ("yellow" if sel > 0 else "red")
    arah = "lebih besar" if sel > 0 else "lebih kecil"
    c2.markdown(f'<div class="metric-card {cls}"><div class="metric-label">⚖️ Selisih Sistem ICHA</div><div class="metric-value {cls}">{fmt_rp(abs(sel))}</div><div class="metric-sub">{arah} {abs(sel/icha_float*100):.2f}% dari ICHA</div></div>', unsafe_allow_html=True)

# ── DETAIL PER SEP + NAMA PASIEN LENGKAP ─────────────────────────────────────
st.markdown('<div class="section-title">📄 Detail Data per Pasien</div>', unsafe_allow_html=True)

for label, h in [("Rawat Inap", hasil_ri), ("Rawat Jalan", hasil_rj)]:
    if h is None:
        continue
    with st.expander(f"🔍 Lihat Tabel {label} ({h['n_sep']:,} data Pasien)"):
        # Susun urutan kolom biar rapi. Kalau ada Nama Pasien ditaruh di depan.
        kolom_tampil = ["No.SEP"]
        if "No. RM" in h["df_detail"].columns: kolom_tampil.append("No. RM")
        if "Nama Pasien" in h["df_detail"].columns: kolom_tampil.append("Nama Pasien")
        kolom_tampil += ["Biaya Riil RS", "Disetujui", "Jasa Pelayanan", "Jaspel Selisih", "Total Jaspel"]
        
        df_show = h["df_detail"][kolom_tampil].copy()
        st.dataframe(df_show, use_container_width=True, hide_index=True,
                     column_config={
                         "Biaya Riil RS":   st.column_config.NumberColumn(format="Rp %d"),
                         "Disetujui":       st.column_config.NumberColumn(format="Rp %d"),
                         "Jasa Pelayanan":  st.column_config.NumberColumn(format="Rp %.0f"),
                         "Jaspel Selisih":  st.column_config.NumberColumn(format="Rp %.0f"),
                         "Total Jaspel":    st.column_config.NumberColumn(format="Rp %.0f"),
                     })

# ── KANTONG BESAR REKAP ──────────────────────────────────────────────────────
st.markdown('<div class="section-title">🏦 Distribusi Kantong Besar</div>', unsafe_allow_html=True)
rows_kb = []
baris_html = ""
for nama, pct in KANTONG.items():
    val_ri  = total_ri  * pct / 100
    val_rj  = total_rj  * pct / 100
    val_tot = val_ri + val_rj
    rows_kb.append((nama, val_ri, val_rj, val_tot))
    
    ri_str  = fmt_rp(val_ri)  if hasil_ri else "—"
    rj_str  = fmt_rp(val_rj)  if hasil_rj else "—"
    baris_html += f'<tr><td>{nama}</td><td class="nominal">{ri_str}</td><td class="nominal">{rj_str}</td><td class="nominal">{fmt_rp(val_tot)}</td></tr>'

st.markdown(f"""
<table class="kantong-table">
    <thead><tr><th>Jenis Jasa Pelayanan</th><th class="nominal">Jaspel RI</th><th class="nominal">Jaspel RJ</th><th class="nominal">Total</th></tr></thead>
    <tbody>{baris_html}<tr><td>TOTAL</td><td class="nominal">{fmt_rp(total_ri) if hasil_ri else "—"}</td><td class="nominal">{fmt_rp(total_rj) if hasil_rj else "—"}</td><td class="nominal">{fmt_rp(total_all)}</td></tr></tbody>
</table>
""", unsafe_allow_html=True)

# ── DOWNLOAD EXCEL REKAP AUDIT LENGKAP ────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">⬇️ Export Hasil Audit Lengkap</div>', unsafe_allow_html=True)

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    df_kb = pd.DataFrame(rows_kb, columns=["Jenis Jasa Pelayanan","Jaspel RI","Jaspel RJ","Total"])
    df_kb.to_excel(w, index=False, sheet_name="Kantong Besar")
    if hasil_ri:
        hasil_ri["df_detail"].to_excel(w, index=False, sheet_name="Detail RI_Pasien")
    if hasil_rj:
        hasil_rj["df_detail"].to_excel(w, index=False, sheet_name="Detail RJ_Pasien")

st.download_button(
    "⬇️ Download File Excel Audit Pasien (.xlsx)",
    data=buf.getvalue(),
    file_name=f"HASIL_AUDIT_JASPEL_LENGKAP.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
