from __future__ import annotations

import sys
from pathlib import Path

from flask import Blueprint, make_response, render_template, session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask_app.models.database import db
from flask_app.models.report import Report
from flask_app.models.screening import Screening
from flask_app.report_generator import build_report_bytes
from flask_app.translations import LANGUAGE_OPTIONS, TRANSLATIONS

report_bp = Blueprint("report_bp", __name__)


def _feature_analysis_from_screening(screening: Screening) -> list[dict]:
    return [
        {"feature": "gait_speed", "label": "Gait Speed", "value": screening.gait_speed, "unit": "m/s", "normal_range": "1.20-1.40 m/s", "status": "normal" if screening.gait_speed >= 1.2 else "abnormal", "deviation_percent": 0},
        {"feature": "stride_time", "label": "Stride Time", "value": screening.stride_time, "unit": "s", "normal_range": "1.00-1.10 s", "status": "normal" if screening.stride_time <= 1.10 else "abnormal", "deviation_percent": 0},
        {"feature": "stride_length", "label": "Stride Length", "value": screening.stride_length, "unit": "m", "normal_range": "1.25-1.45 m", "status": "normal" if screening.stride_length >= 1.25 else "abnormal", "deviation_percent": 0},
        {"feature": "cadence", "label": "Cadence", "value": screening.cadence, "unit": "steps/min", "normal_range": "110-120 steps/min", "status": "normal" if 110 <= screening.cadence <= 120 else "abnormal", "deviation_percent": 0},
        {"feature": "knee_rom", "label": "Knee ROM", "value": screening.knee_rom, "unit": "°", "normal_range": "55-65 °", "status": "normal" if 55 <= screening.knee_rom <= 65 else "abnormal", "deviation_percent": 0},
        {"feature": "step_time_std", "label": "Step Time Std", "value": screening.step_time_std, "unit": "s", "normal_range": "0.02-0.04 s", "status": "normal" if 0.02 <= screening.step_time_std <= 0.04 else "abnormal", "deviation_percent": 0},
    ]


@report_bp.route("/report")
@report_bp.route("/report/")
def report_index():
    """Open the latest generated report."""
    screening = Screening.query.order_by(Screening.timestamp.desc()).first()
    if screening is None:
        return render_template("report.html", report={}, patient={}, prediction={}, feature_analysis=[], report_id="OA-DEMO", language=session.get("language", "en"), languages=LANGUAGE_OPTIONS, translations=TRANSLATIONS.get(session.get("language", "en"), TRANSLATIONS["en"]))
    return view_report(screening.id)


@report_bp.route("/report/<int:screening_id>")
def view_report(screening_id: int):
    """View a generated clinical report by screening ID."""
    screening = Screening.query.get_or_404(screening_id)
    patient = screening.patient
    report = screening.report
    report_id = report.report_id if report else f"OA-{screening.timestamp.strftime('%Y%m%d')}-{screening.id:04d}"

    prediction = {
        "class": screening.risk_class,
        "label": screening.risk_label,
        "confidence": screening.confidence,
    }
    feature_analysis = _feature_analysis_from_screening(screening)
    active_lang = session.get("language", "en")

    return render_template(
        "report.html",
        report={"report_id": report_id, "timestamp": screening.timestamp.isoformat()},
        patient=patient.to_dict() if patient else {},
        prediction=prediction,
        feature_analysis=feature_analysis,
        report_id=report_id,
        screening=screening,
        language=active_lang,
        languages=LANGUAGE_OPTIONS,
        translations=TRANSLATIONS.get(active_lang, TRANSLATIONS["en"]),
    )


@report_bp.route("/report/<int:screening_id>/pdf")
def download_report(screening_id: int):
    """Download the PDF version of a report for a screening."""
    screening = Screening.query.get_or_404(screening_id)
    patient = screening.patient
    report = screening.report
    report_id = report.report_id if report else f"OA-{screening.timestamp.strftime('%Y%m%d')}-{screening.id:04d}"
    patient_data = patient.to_dict() if patient else {}
    prediction = {"class": screening.risk_class, "label": screening.risk_label, "confidence": screening.confidence}
    feature_analysis = _feature_analysis_from_screening(screening)

    pdf_path = Path(__file__).resolve().parents[1] / "data" / "reports" / f"{report_id}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        pdf_bytes = build_report_bytes(
            patient_data=patient_data,
            prediction=prediction,
            feature_analysis=feature_analysis,
            report_id=report_id,
            language=session.get("language", "en"),
        )
        pdf_path.write_bytes(pdf_bytes)
        if report is None:
            report = Report(screening_id=screening.id, report_id=report_id, pdf_path=str(pdf_path))
            db.session.add(report)
            db.session.commit()
        else:
            report.pdf_path = str(pdf_path)
            db.session.commit()

    response = make_response(pdf_path.read_bytes())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={report_id}.pdf"
    return response
