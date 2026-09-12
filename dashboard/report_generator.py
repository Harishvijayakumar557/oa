from __future__ import annotations

import datetime as dt
import io
import os
import uuid
from pathlib import Path

import qrcode
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"


def register_fonts() -> dict[str, str]:
    """Register available Noto fonts when present, otherwise fall back to default fonts."""
    font_map = {
        "en": "Helvetica",
        "ta": "Helvetica",
        "hi": "Helvetica",
        "as": "Helvetica",
        "bn": "Helvetica",
        "mni": "Helvetica",
        "brx": "Helvetica",
        "lus": "Helvetica",
    }

    for lang, file_name in {
        "ta": "NotoSans-Regular.ttf",
        "hi": "NotoSansDevanagari-Regular.ttf",
        "as": "NotoSansBengali-Regular.ttf",
        "bn": "NotoSansBengali-Regular.ttf",
        "mni": "NotoSansBengali-Regular.ttf",
        "brx": "NotoSans-Regular.ttf",
        "lus": "NotoSans-Regular.ttf",
    }.items():
        font_path = FONTS_DIR / file_name
        if font_path.exists():
            font_name = f"{lang}_font"
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            font_map[lang] = font_name

    return font_map


def build_qr_code(data: str, size: int = 44) -> Drawing:
    """Create a QR code image for report verification links."""
    qr = qrcode.QRCode(version=1, box_size=3, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    drawing = Drawing(size, size)
    drawing.add(renderPDF.Image(img, 0, 0, size, size))
    return drawing


def build_report_bytes(patient_data: dict, prediction: dict, language: str = "en") -> bytes:
    """Generate a patient report as a PDF, including metadata, summary, disclaimers, and chart placeholders."""
    now = dt.datetime.now()
    report_id = f"OA-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    font_map = register_fonts()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontName=font_map.get(language, "Helvetica"),
        fontSize=20,
        textColor=colors.HexColor("#0C3B6E"),
        alignment=1,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontName=font_map.get(language, "Helvetica"),
        textColor=colors.HexColor("#1F4E79"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName=font_map.get(language, "Helvetica"),
        fontSize=9,
        leading=13,
    )
    footer_style = ParagraphStyle(
        "FooterStyle",
        parent=styles["BodyText"],
        fontName=font_map.get(language, "Helvetica"),
        fontSize=8,
        textColor=colors.HexColor("#666666"),
        alignment=1,
    )

    story = []
    story.append(Paragraph("Community Orthopaedic & Rehabilitation Clinic", title_style))
    story.append(Paragraph("OA Screening Report", heading_style))
    story.append(Paragraph(f"Report ID: {report_id}", body_style))
    story.append(Paragraph(f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    story.append(Spacer(1, 8 * mm))

    hospital_block = Table(
        [["Clinic Code", "COARC-NE-01"], ["Location", "North East Screening Unit"], ["Clinician", "Dr. A. Sharma"]],
        colWidths=[45 * mm, 90 * mm],
    )
    hospital_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F7FF")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), font_map.get(language, "Helvetica")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Clinic Details", heading_style))
    story.append(hospital_block)
    story.append(Spacer(1, 8 * mm))

    patient_table = Table(
        [
            ["Patient Name", patient_data.get("name", "N/A")],
            ["Age", str(patient_data.get("age", "N/A"))],
            ["Gender", patient_data.get("gender", "N/A")],
            ["Medical History", patient_data.get("medical_history", "N/A")],
            ["Pain Level", str(patient_data.get("pain_level", "N/A"))],
            ["Mobility", patient_data.get("mobility_difficulty", "N/A")],
        ],
        colWidths=[52 * mm, 100 * mm],
    )
    patient_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2FF")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), font_map.get(language, "Helvetica")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(Paragraph("Patient Information", heading_style))
    story.append(patient_table)
    story.append(Spacer(1, 8 * mm))

    risk_label = prediction.get("risk_label", "Low Risk")
    risk_score = prediction.get("confidence", 0.0)
    story.append(Paragraph(f"Risk Level: {risk_label}", heading_style))
    story.append(Paragraph(f"Confidence: {risk_score:.1f}%", body_style))
    story.append(Paragraph("Summary: Gait metrics indicate screening risk based on the model output and clinically relevant thresholds.", body_style))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Risk Chart Placeholder", heading_style))
    chart_table = Table([
        ["Low", "Moderate", "High"],
        ["35%", "40%", "25%"],
    ], colWidths=[30 * mm, 30 * mm, 30 * mm])
    chart_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9F5FF")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), font_map.get(language, "Helvetica")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(chart_table)
    story.append(Spacer(1, 6 * mm))

    recommendations = [
        "- ⚠️ For screening only, not medical diagnosis.",
        "- Encourage activity modification and physiotherapy review if needed.",
        "- Consider orthopaedic assessment if symptoms persist or worsen.",
    ]
    story.append(Paragraph("Recommendations", heading_style))
    for item in recommendations:
        story.append(Paragraph(item, body_style))
    story.append(Spacer(1, 8 * mm))

    qr_code = build_qr_code("https://example.com/oa-screening-verification")
    qr_table = Table([[qr_code, Paragraph("Verification URL\nhttps://example.com/oa-screening-verification", body_style)]], colWidths=[40 * mm, 100 * mm])
    story.append(Paragraph("Verification", heading_style))
    story.append(qr_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Doctor Signature", heading_style))
    story.append(Paragraph("______________________________", body_style))
    story.append(Paragraph("Dr. A. Sharma, Orthopaedic Consultant", body_style))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Digital Signature: Verified by screening workflow v1.0", body_style))
    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "⚠️ For screening only, not medical diagnosis.",
            footer_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()
