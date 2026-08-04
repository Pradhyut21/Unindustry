"""
create_sample_pdf.py — generates a realistic industrial product datasheet PDF
for use as a demo fixture. Run once: python scripts/create_sample_pdf.py

Output: api/fixtures/sample_siemens_3rt2015_datasheet.pdf
Requires: PyMuPDF (pip install pymupdf)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_datasheet_pdf(output_path: Path) -> None:
    import fitz  # PyMuPDF

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # ── Colour palette ────────────────────────────────────────────────────────
    BLUE = (0.0, 0.27, 0.57)
    DARK = (0.1, 0.1, 0.1)
    MID = (0.35, 0.35, 0.35)
    LIGHT = (0.92, 0.94, 0.97)
    WHITE = (1.0, 1.0, 1.0)

    # ── Header bar ────────────────────────────────────────────────────────────
    page.draw_rect(fitz.Rect(0, 0, 595, 80), color=BLUE, fill=BLUE)
    page.insert_text((30, 35), "SIEMENS", fontsize=24, color=WHITE, fontname="helv")
    page.insert_text((30, 58), "Industry Automation Division", fontsize=10, color=WHITE)
    page.insert_text((350, 35), "PRODUCT DATASHEET", fontsize=14, color=WHITE)
    page.insert_text((350, 55), "3RT2 Series Contactors", fontsize=11, color=WHITE)

    # ── Product title ─────────────────────────────────────────────────────────
    page.insert_text((30, 105), "3RT2015-1AP01", fontsize=20, color=DARK)
    page.insert_text(
        (30, 130), "3-Pole Contactor for Motor Control Applications", fontsize=12, color=MID
    )

    # ── Divider ───────────────────────────────────────────────────────────────
    page.draw_line((30, 145), (565, 145), color=BLUE, width=1.5)

    # ── Description box ───────────────────────────────────────────────────────
    page.draw_rect(fitz.Rect(30, 155, 565, 210), color=LIGHT, fill=LIGHT)
    page.insert_text(
        (40, 175),
        "The Siemens 3RT2015 contactor is designed for switching three-phase",
        fontsize=10,
        color=DARK,
    )
    page.insert_text(
        (40, 190),
        "induction motors in industrial automation systems. DIN rail mountable,",
        fontsize=10,
        color=DARK,
    )
    page.insert_text(
        (40, 205),
        "suitable for AC-3 duty with integrated auxiliary contact capability.",
        fontsize=10,
        color=DARK,
    )

    # ── Specifications table ───────────────────────────────────────────────────
    page.insert_text(
        (30, 235), "TECHNICAL SPECIFICATIONS", fontsize=13, color=BLUE, fontname="helv"
    )
    page.draw_line((30, 242), (565, 242), color=BLUE, width=0.8)

    specs = [
        ("Rated Voltage:", "230V AC"),
        ("Rated Current:", "7A"),
        ("Rated Power (400V AC):", "3 kW"),
        ("Frequency:", "50/60 Hz"),
        ("IP Rating:", "IP20 (open); IP44 with enclosure"),
        ("Operating Temperature:", "-25°C to +60°C"),
        ("Dimensions (W×H×D):", "45 mm × 57 mm × 70 mm"),
        ("Weight:", "0.24 kg"),
        ("Housing Material:", "Thermoplastic (PA), self-extinguishing"),
    ]

    y = 258
    for i, (label, value) in enumerate(specs):
        bg = LIGHT if i % 2 == 0 else WHITE
        page.draw_rect(fitz.Rect(30, y - 3, 565, y + 14), color=bg, fill=bg)
        page.insert_text((35, y + 9), label, fontsize=10, color=MID)
        page.insert_text((230, y + 9), value, fontsize=10, color=DARK)
        y += 20

    # ── Certifications ─────────────────────────────────────────────────────────
    page.insert_text(
        (30, y + 20), "CERTIFICATIONS & STANDARDS", fontsize=13, color=BLUE, fontname="helv"
    )
    page.draw_line((30, y + 27), (565, y + 27), color=BLUE, width=0.8)
    page.insert_text(
        (35, y + 45), "CE  |  UL Listed  |  CSA  |  RoHS Compliant", fontsize=11, color=DARK
    )
    page.insert_text(
        (35, y + 62), "IEC 60947-4-1  |  EN 60947-4-1  |  VDE 0660", fontsize=11, color=DARK
    )

    # ── Ordering info ──────────────────────────────────────────────────────────
    page.insert_text((30, y + 90), "ORDERING INFORMATION", fontsize=13, color=BLUE, fontname="helv")
    page.draw_line((30, y + 97), (565, y + 97), color=BLUE, width=0.8)

    order_rows = [
        ("Model Number:", "3RT2015-1AP01"),
        ("Part Number:", "3RT2015-1AP01"),
        ("Catalog Number:", "3RT2015-1AP01"),
        ("Manufacturer:", "Siemens AG"),
        ("Product Category:", "Electromechanical Contactor / Motor Starter"),
    ]
    y2 = y + 112
    for i, (label, value) in enumerate(order_rows):
        bg = LIGHT if i % 2 == 0 else WHITE
        page.draw_rect(fitz.Rect(30, y2 - 3, 565, y2 + 14), color=bg, fill=bg)
        page.insert_text((35, y2 + 9), label, fontsize=10, color=MID)
        page.insert_text((230, y2 + 9), value, fontsize=10, color=DARK)
        y2 += 20

    # ── Footer ─────────────────────────────────────────────────────────────────
    page.draw_rect(fitz.Rect(0, 800, 595, 842), color=BLUE, fill=BLUE)
    page.insert_text(
        (30, 825),
        "Siemens AG · Industry Automation · Werner-von-Siemens-Str. 1 · 80333 Munich",
        fontsize=8,
        color=WHITE,
    )
    page.insert_text((430, 825), "Page 1 of 1 · DS-3RT2015-2024", fontsize=8, color=WHITE)

    # ── Nameplate simulation box ────────────────────────────────────────────────
    # Small "nameplate" in top-right corner — simulates what the vision agent reads
    plate_rect = fitz.Rect(380, 90, 565, 140)
    page.draw_rect(plate_rect, color=(0.85, 0.85, 0.85), fill=(0.95, 0.95, 0.95), width=1.0)
    page.insert_text((385, 108), "SIEMENS 3RT2015-1AP01", fontsize=7.5, color=DARK)
    page.insert_text((385, 120), "230V AC  7A  3kW  50/60Hz", fontsize=7.5, color=DARK)
    page.insert_text((385, 132), "IP20  CE  UL  -25+60°C", fontsize=7.5, color=DARK)

    doc.save(str(output_path))
    doc.close()
    print(f"Created: {output_path}")


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "api" / "fixtures" / "sample_siemens_3rt2015_datasheet.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    create_datasheet_pdf(out)
