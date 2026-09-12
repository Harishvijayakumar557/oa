from __future__ import annotations

import datetime as dt
import io
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import qrcode

BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "static" / "fonts"


def register_fonts() -> dict[str, str]:
    """Register a safe default font stack and any available local fonts."""
    fonts = {"en": "Helvetica"}
    if FONTS_DIR.exists():
        registry = {
            "ta": "NotoSansTamil-Regular.ttf",
            "hi": "NotoSansDevanagari-Regular.ttf",
            "bn": "NotoSansBengali-Regular.ttf",
            "as": "NotoSansBengali-Regular.ttf",
        }
        for lang, file_name in registry.items():
            font_path = FONTS_DIR / file_name
            if font_path.exists():
                key = f"{lang}_font"
                pdfmetrics.registerFont(TTFont(key, str(font_path)))
                fonts[lang] = key
    return fonts


def build_qr_code(data: str, size: int = 48) -> Image:
    """Create a QR code used in the report verification section."""
    qr = qrcode.QRCode(version=1, box_size=3, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return Image(buffer, width=size, height=size)


def build_report_bytes(
    patient_data: dict,
    prediction: dict,
    feature_analysis: list[dict] | None = None,
    report_id: str | None = None,
    language: str = "en",
) -> bytes:
    """Generate a PDF report for the OA screening application."""
    now = dt.datetime.now()
    report_ref = report_id or f"OA-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    font_map = register_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontName=font_map.get(language, "Helvetica"),
        fontSize=18,
        textColor=colors.HexColor("#0d6efd"),
        alignment=1,
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontName=font_map.get(language, "Helvetica"),
        fontSize=11,
        textColor=colors.HexColor("#0d6efd"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName=font_map.get(language, "Helvetica"),
        fontSize=8.5,
        leading=11,
    )
    footer_style = ParagraphStyle(
        "FooterStyle",
        parent=styles["BodyText"],
        fontName=font_map.get(language, "Helvetica"),
        fontSize=7,
        textColor=colors.HexColor("#666666"),
        alignment=1,
    )

    story: list = []
    story.append(Paragraph("OA Screening Center", title_style))
    story.append(Paragraph("GAIT ANALYSIS & OA RISK ASSESSMENT REPORT", heading_style))
    story.append(Paragraph(f"Report ID: {report_ref}", body_style))
    story.append(Paragraph(f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    story.append(Spacer(1, 5 * mm))

    info_rows = [
        ["Patient ID", patient_data.get("patient_id") or "N/A"],
        ["Name", patient_data.get("name") or "N/A"],
        ["Age", str(patient_data.get("age") or "N/A")],
        ["Gender", patient_data.get("gender") or "N/A"],
        ["DOB", patient_data.get("dob") or "N/A"],
        ["Contact", patient_data.get("phone") or "N/A"],
        ["Medical History", patient_data.get("medical_history") or "N/A"],
        ["Chief Complaint", patient_data.get("chief_complaint") or "N/A"],
    ]
    patient_table = Table(info_rows, colWidths=[45 * mm, 100 * mm])
    patient_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2FF")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), font_map.get(language, "Helvetica")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(Paragraph("SECTION 1: PATIENT INFORMATION", heading_style))
    story.append(patient_table)
    story.append(Spacer(1, 6 * mm))

    if feature_analysis:
        feature_table = Table(
            [["Parameter", "Measured", "Normal Range", "Status"]] + [
                [
                    row.get("label") or row.get("feature") or "Feature",
                    f"{row.get('value')} {row.get('unit', '')}".strip(),
                    row.get("normal_range") or "N/A",
                    row.get("status_label") or ("Normal" if row.get("status") == "normal" else "Abnormal"),
                ]
                for row in feature_analysis
            ],
            colWidths=[40 * mm, 38 * mm, 40 * mm, 30 * mm],
        )
        feature_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2FF")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), font_map.get(language, "Helvetica")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(Paragraph("SECTION 2: GAIT ANALYSIS FINDINGS", heading_style))
        story.append(feature_table)
        story.append(Spacer(1, 6 * mm))

    risk_label = (prediction or {}).get("label") or (prediction or {}).get("risk_label") or "Moderate Risk"
    confidence = float((prediction or {}).get("confidence") or 0.0) * 100
    story.append(Paragraph("SECTION 3: RISK ASSESSMENT", heading_style))
    story.append(Paragraph(f"Risk Level: {risk_label}", body_style))
    story.append(Paragraph(f"Confidence: {confidence:.1f}%", body_style))
    story.append(Paragraph("ML Model: Random Forest, accuracy 83.67%", body_style))
    story.append(Paragraph("Clinical note: This is an early screening estimate, not a diagnosis.", body_style))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("SECTION 4: RECOMMENDATIONS", heading_style))
    recommendations = [
        "• Low Risk: Continue regular activity and annual screening.",
        "• Moderate Risk: Consider physiotherapy, knee strengthening, and a follow-up in 3 months.",
        "• High Risk: Clinical evaluation is recommended; orthopedic referral may be appropriate.",
    ]
    for line in recommendations:
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 8 * mm))

    qr = build_qr_code(f"https://example.com/report/{report_ref}")
    qr_row = Table([[qr, Paragraph("Verification QR\nhttps://example.com/report/" + report_ref, body_style)]], colWidths=[42 * mm, 85 * mm])
    story.append(Paragraph("SECTION 5: DISCLAIMER & SIGNATURE", heading_style))
    story.append(qr_row)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("This system is for early screening and risk assessment only. Not a medical diagnosis.", footer_style))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Clinician Signature: ______________________", body_style))
    story.append(Paragraph("Date: " + now.strftime("%Y-%m-%d"), body_style))

    doc.build(story)
    return buffer.getvalue()

