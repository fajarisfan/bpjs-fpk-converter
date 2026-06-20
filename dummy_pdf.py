"""
dummy_pdf.py
─────────────────────────────────────────────────────────────────
Generator PDF "RINCIAN DATA HASIL VERIFIKASI" (format FPK BPJS
Kesehatan) dengan DATA FIKTIF/ACAK — dipakai untuk keperluan
demo/simulasi (mis. rekam video tutorial) supaya tidak perlu
menampilkan data pasien asli.

Layout & struktur tabel dibuat semirip mungkin dengan dokumen asli
(judul, label Nama RS/Tingkat Pelayanan/Bulan Pelayanan, header
kolom No/No.SEP/Tgl. Verifikasi/Biaya Riil-Diajukan-Disetujui,
baris TOTAL, blok RESUME, tanda tangan) memakai garis tabel
(lattice) agar bisa dibaca ulang oleh pipeline ekstraksi yang sama
(tabula lattice=True) — jadi cocok untuk uji-coba end-to-end di
video tanpa menyentuh data rahasia pasien.

SEMUA nilai (Nama RS, No.SEP, tanggal, nominal) di-generate acak,
TIDAK merepresentasikan rumah sakit, pasien, atau klaim nyata.
"""

import random
import string
from datetime import date, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


BULAN_LIST = [
    "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
    "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER",
]

TINGKAT_LIST = ["RITL", "RJTL", "RITP", "RJTP"]

# Daftar nama RS fiktif (jelas-jelas bukan instansi nyata) untuk dummy data
NAMA_RS_DUMMY = [
    "RS CONTOH SEJAHTERA",
    "RS SIMULASI MEDIKA",
    "RS DEMO HUSADA",
    "RS PERAGAAN SEHAT",
    "RS UJI COBA UTAMA",
]

KOTA_DUMMY = [
    "KOTA CONTOH", "KOTA SIMULASI", "KOTA DEMO", "KOTA PERAGAAN",
]

DOKTER_DUMMY = [
    "dr. Contoh Simulasi, MPH",
    "dr. Demo Peragaan, M.Kes",
    "dr. Fiktif Uji Coba, Sp.PD",
]


def _random_kode_rs():
    return f"{random.randint(1000,9999)}D{random.randint(100,999):03d}"


def _random_sep(bulan_idx: int, tahun: int, urut: int) -> str:
    """
    Format mengikuti pola No.SEP asli: KODERS + MMYYYY + 'V' + urut,
    tapi kode RS & urutan acak -> tidak match nomor SEP nyata manapun.
    """
    kode_rs = f"{random.randint(1000,9999)}R{random.randint(100,999):03d}"
    mmyyyy = f"{bulan_idx+1:02d}{str(tahun)[2:]}"
    return f"{kode_rs}{mmyyyy}V{urut:06d}"


def _random_tanggal(bulan_idx: int, tahun: int) -> str:
    hari = random.randint(1, 27)
    bln = bulan_idx + 1
    return f"{tahun}-{bln:02d}-{hari:02d}"


def _rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def generate_dummy_fpk_data(jumlah_baris: int = 8, bulan: str = None,
                              tahun: int = None, tingkat: str = None,
                              seed: int = None):
    """Bangun struktur data dummy (dipakai juga untuk preview di Streamlit)."""
    if seed is not None:
        random.seed(seed)

    bulan = bulan or random.choice(BULAN_LIST)
    bulan_idx = BULAN_LIST.index(bulan)
    tahun = tahun or random.choice([2025, 2026])
    tingkat = tingkat or random.choice(TINGKAT_LIST)
    nama_rs = random.choice(NAMA_RS_DUMMY)
    kota = random.choice(KOTA_DUMMY)
    kode_rs = _random_kode_rs()
    dokter = random.choice(DOKTER_DUMMY)

    rows = []
    total_riil, total_diajukan, total_disetujui = 0, 0, 0
    for i in range(1, jumlah_baris + 1):
        sep = _random_sep(bulan_idx, tahun, random.randint(1, 999999))
        tgl = _random_tanggal(bulan_idx, tahun)
        riil = random.randint(50_000, 8_000_000)
        diajukan = random.randint(100_000, 2_000_000)
        # disetujui biasanya <= diajukan, kadang persis sama (umum di data asli)
        disetujui = diajukan if random.random() < 0.6 else random.randint(int(diajukan*0.5), diajukan)

        rows.append({
            "no": i,
            "sep": sep,
            "tanggal": tgl,
            "riil": riil,
            "diajukan": diajukan,
            "disetujui": disetujui,
        })
        total_riil += riil
        total_diajukan += diajukan
        total_disetujui += disetujui

    return {
        "nama_rs": nama_rs,
        "kode_rs": kode_rs,
        "kota": kota,
        "tingkat": tingkat,
        "bulan": bulan,
        "tahun": tahun,
        "dokter": dokter,
        "rows": rows,
        "total_riil": total_riil,
        "total_diajukan": total_diajukan,
        "total_disetujui": total_disetujui,
    }


def build_dummy_fpk_pdf(output_path: str, jumlah_baris: int = 8, bulan: str = None,
                          tahun: int = None, tingkat: str = None, seed: int = None) -> dict:
    """
    Generate file PDF dummy ke `output_path`, format meniru dokumen
    'RINCIAN DATA HASIL VERIFIKASI' BPJS Kesehatan, tapi 100% data fiktif.
    Return dict info data yang dipakai (untuk ditampilkan di UI).
    """
    data = generate_dummy_fpk_data(jumlah_baris, bulan, tahun, tingkat, seed)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=18*mm, bottomMargin=18*mm,
        leftMargin=16*mm, rightMargin=16*mm,
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Watermark/label DUMMY tegas di pojok ──
    style_watermark = ParagraphStyle(
        "watermark", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#cc0000"), alignment=TA_LEFT,
    )
    story.append(Paragraph("[DATA SIMULASI / DUMMY — BUKAN DATA ASLI]", style_watermark))
    story.append(Spacer(1, 6))

    # ── Header: logo teks + judul ──
    style_logo = ParagraphStyle(
        "logo", parent=styles["Normal"], fontSize=9, leading=11,
        textColor=colors.HexColor("#00529b"),
    )
    style_title = ParagraphStyle(
        "title", parent=styles["Heading2"], alignment=TA_CENTER,
        fontSize=13, spaceAfter=14, spaceBefore=2,
    )
    story.append(Paragraph("<b>BPJS</b> Kesehatan (Simulasi)", style_logo))
    story.append(Spacer(1, 4))
    story.append(Paragraph("RINCIAN DATA HASIL VERIFIKASI", style_title))

    # ── Info RS (tanpa tabel, mirip layout asli) ──
    style_info_label = ParagraphStyle("info_l", parent=styles["Normal"], fontSize=9.5)
    info_lines = [
        f"Nama RS&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {data['kode_rs']} - {data['nama_rs']} - {data['kota']}(Aktif)",
        f"Tingkat Pelayanan&nbsp;&nbsp;: {data['tingkat']}",
        f"Bulan Pelayanan&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {data['bulan'].capitalize()} {data['tahun']}",
    ]
    for line in info_lines:
        story.append(Paragraph(line, style_info_label))
    story.append(Spacer(1, 12))

    # ── Tabel utama (lattice / bergaris penuh, sama seperti dokumen asli) ──
    style_cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5, alignment=TA_CENTER)
    style_cell_l = ParagraphStyle("celll", parent=styles["Normal"], fontSize=8.5, alignment=TA_LEFT)

    table_data = []
    # baris header 1 (merge No/No.SEP/Tgl secara vertikal, Biaya merge horizontal -> disederhanakan jadi 2 baris header)
    table_data.append(["No", "No.SEP", "Tgl. Verifikasi", "Biaya", "", ""])
    table_data.append(["", "", "", "Riil RS", "Diajukan", "Disetujui"])

    for r in data["rows"]:
        table_data.append([
            str(r["no"]), r["sep"], r["tanggal"],
            _rupiah(r["riil"]), _rupiah(r["diajukan"]), _rupiah(r["disetujui"]),
        ])

    table_data.append([
        "TOTAL", "", "", _rupiah(data["total_riil"]),
        _rupiah(data["total_diajukan"]), _rupiah(data["total_disetujui"]),
    ])

    col_widths = [12*mm, 42*mm, 26*mm, 28*mm, 26*mm, 26*mm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=2)

    n_rows = len(table_data)
    total_row_idx = n_rows - 1

    tbl_style = [
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("SPAN", (0, 0), (0, 1)),       # No
        ("SPAN", (1, 0), (1, 1)),       # No.SEP
        ("SPAN", (2, 0), (2, 1)),       # Tgl. Verifikasi
        ("SPAN", (3, 0), (5, 0)),       # Biaya (merge 3 kolom)
        ("SPAN", (0, total_row_idx), (2, total_row_idx)),  # TOTAL label merge
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTNAME", (0, total_row_idx), (-1, total_row_idx), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 1), "CENTER"),
        ("ALIGN", (0, total_row_idx), (0, total_row_idx), "CENTER"),
        ("ALIGN", (3, 2), (5, -1), "RIGHT"),
        ("ALIGN", (0, 2), (0, -1), "CENTER"),
        ("ALIGN", (2, 2), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("RIGHTPADDING", (3, 0), (5, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)
    story.append(Spacer(1, 16))

    # ── RESUME ──
    style_resume_title = ParagraphStyle("resume_t", parent=styles["Normal"], fontSize=9.5, fontName="Helvetica-Bold")
    style_resume = ParagraphStyle("resume", parent=styles["Normal"], fontSize=9.5)
    story.append(Paragraph("RESUME", style_resume_title))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Total Bea.Diajukan&nbsp;&nbsp;: {_rupiah(data['total_diajukan'])}", style_resume))
    story.append(Paragraph(f"Total Bea.Disetujui&nbsp;&nbsp;: {_rupiah(data['total_disetujui'])}", style_resume))
    story.append(Spacer(1, 20))

    # ── Tanda tangan ──
    ttd_data = [
        ["Menyetujui", "Mengetahui"],
        ["Direktur RS", "BPJS KESEHATAN"],
        ["", ""],
        ["", ""],
        [data["dokter"], "____________________"],
    ]
    ttd_tbl = Table(ttd_data, colWidths=[80*mm, 80*mm])
    ttd_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 4), (0, 4), "Helvetica-Oblique"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(ttd_tbl)

    doc.build(story)

    return {
        "nama_rs": data["nama_rs"],
        "tingkat": data["tingkat"],
        "bulan": data["bulan"],
        "tahun": data["tahun"],
        "jumlah_baris": jumlah_baris,
        "total_disetujui": data["total_disetujui"],
        "rows": data["rows"],
    }


if __name__ == "__main__":
    info = build_dummy_fpk_pdf("/home/claude/dummy_fpk_test.pdf", jumlah_baris=6, seed=42)
    print("Generated:", info["nama_rs"], info["tingkat"], info["bulan"], info["tahun"])
    print("Total disetujui:", info["total_disetujui"])
