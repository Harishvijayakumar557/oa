from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from flask_app.models.database import db
from flask_app.models.patient import Patient
from flask_app.models.report import Report
from flask_app.models.screening import Screening
from flask_app.translations import LANGUAGE_OPTIONS, TRANSLATIONS

main_bp = Blueprint("main_bp", __name__)
SUPPORTED_LANGUAGE_CODES = set(LANGUAGE_OPTIONS)
COREX_STATES = [
    "Assam",
    "Arunachal Pradesh",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
]


@main_bp.before_request
def apply_requested_language():
    requested_language = request.args.get("lang")
    if requested_language in SUPPORTED_LANGUAGE_CODES:
        session["language"] = requested_language


def _lang_context(lang: str | None = None):
    active_lang = lang or session.get("language", "en")
    return {
        "language": active_lang,
        "languages": LANGUAGE_OPTIONS,
        "translations": TRANSLATIONS.get(active_lang, TRANSLATIONS["en"]),
    }


def _dashboard_payload() -> dict:
    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    recent_screenings = Screening.query.order_by(Screening.timestamp.desc()).limit(10).all()

    risk_distribution = {
        "low": Screening.query.filter(Screening.risk_class == 0).count(),
        "moderate": Screening.query.filter(Screening.risk_class == 1).count(),
        "high": Screening.query.filter(Screening.risk_class == 2).count(),
    }

    weekly_trend = []
    for offset in range(6, -1, -1):
        day = (datetime.utcnow().date() - timedelta(days=offset))
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
        value = Screening.query.filter(Screening.timestamp >= start, Screening.timestamp < end).count()
        weekly_trend.append({"label": day.strftime("%a"), "value": value})

    recent_rows = []
    for screening in recent_screenings:
        patient = screening.patient
        recent_rows.append({
            "id": screening.id,
            "patient_name": patient.name if patient else "Unassigned",
            "risk_label": screening.risk_label,
            "confidence": round(float(screening.confidence or 0), 2),
            "timestamp": screening.timestamp.strftime("%Y-%m-%d %H:%M") if screening.timestamp else "N/A",
        })

    return {
        "stats": {
            "today_screenings": Screening.query.filter(Screening.timestamp >= today_start).count(),
            "total_screenings": Screening.query.count(),
            "pending_reports": Screening.query.outerjoin(Report).filter(Report.id.is_(None)).count(),
            "low_risk": Screening.query.filter(Screening.risk_class == 0).count(),
            "moderate_risk": Screening.query.filter(Screening.risk_class == 1).count(),
            "high_risk_cases": Screening.query.filter(Screening.risk_class == 2).count(),
            "total_patients": Patient.query.count(),
        },
        "recent_screenings": recent_rows,
        "risk_distribution": risk_distribution,
        "weekly_trend": weekly_trend,
    }


@main_bp.route("/")
def index():
    """Render the clinical operations dashboard overview."""
    session.setdefault("language", "en")
    dashboard_data = _dashboard_payload()
    return render_template("index.html", dashboard_data=dashboard_data, **_lang_context())


@main_bp.route("/api/dashboard")
def dashboard_api():
    """Return structured dashboard data for the KPI widgets and charts."""
    return jsonify(_dashboard_payload())


@main_bp.route("/register", methods=["GET", "POST"])
def register_patient():
    """Render and process the patient registration workflow."""
    patient_session = session.get("patient", {})
    if request.method == "GET":
        return render_template("register.html", patient=patient_session, states=COREX_STATES, **_lang_context())

    payload = {
        "name": request.form.get("name", "").strip(),
        "age": request.form.get("age", "") or None,
        "gender": request.form.get("gender", "") or None,
        "height_cm": request.form.get("height_cm", "") or None,
        "weight_kg": request.form.get("weight_kg", "") or None,
        "phone": request.form.get("phone", "").strip() or None,
        "address": request.form.get("address", "").strip() or None,
        "state": request.form.get("state", "").strip() or None,
        "district": request.form.get("district", "").strip() or None,
        "village_town": request.form.get("village_town", "").strip() or None,
        "occupation": request.form.get("occupation", "").strip() or None,
        "screening_date": request.form.get("screening_date", "").strip() or None,
        "screening_mode": request.form.get("screening_mode", "LIVE").strip() or "LIVE",
        "pain_level": request.form.get("pain_level", "") or None,
        "mobility": request.form.get("mobility", "").strip() or None,
        "medical_history": request.form.get("medical_history", "").strip() or None,
        "knee_pain": request.form.get("knee_pain", "").strip() or None,
        "walking_difficulty": request.form.get("walking_difficulty", "").strip() or None,
        "stair_climbing_difficulty": request.form.get("stair_climbing_difficulty", "").strip() or None,
        "stiffness_after_rest": request.form.get("stiffness_after_rest", "").strip() or None,
        "chair_standing_difficulty": request.form.get("chair_standing_difficulty", "").strip() or None,
        "reduced_knee_movement": request.form.get("reduced_knee_movement", "").strip() or None,
        "symptom_duration": request.form.get("symptom_duration", "").strip() or None,
    }

    if not payload["name"]:
        flash("Patient name is required.", "error")
        return render_template("register.html", patient=payload, states=COREX_STATES, **_lang_context())

    patient = Patient(
        name=payload["name"],
        age=int(payload["age"]) if payload["age"] not in (None, "") else None,
        gender=payload["gender"],
        height_cm=float(payload["height_cm"]) if payload["height_cm"] not in (None, "") else None,
        weight_kg=float(payload["weight_kg"]) if payload["weight_kg"] not in (None, "") else None,
        phone=payload["phone"],
        address=payload["address"],
        state=payload["state"],
        district=payload["district"],
        village_town=payload["village_town"],
        occupation=payload["occupation"],
        screening_date=datetime.strptime(payload["screening_date"], "%Y-%m-%d").date() if payload["screening_date"] else None,
        screening_mode=payload["screening_mode"],
        pain_level=int(payload["pain_level"]) if payload["pain_level"] not in (None, "") else None,
        mobility=payload["mobility"],
        medical_history=payload["medical_history"],
        knee_pain=payload["knee_pain"],
        walking_difficulty=payload["walking_difficulty"],
        stair_climbing_difficulty=payload["stair_climbing_difficulty"],
        stiffness_after_rest=payload["stiffness_after_rest"],
        chair_standing_difficulty=payload["chair_standing_difficulty"],
        reduced_knee_movement=payload["reduced_knee_movement"],
        symptom_duration=payload["symptom_duration"],
    )
    db.session.add(patient)
    db.session.commit()

    session["patient"] = patient.to_dict()
    session["patient_id"] = patient.id
    session["screening_mode"] = payload["screening_mode"]
    session["language"] = request.form.get("language_preference", session.get("language", "en"))

    if request.is_json:
        return jsonify({"success": True, "patient_id": patient.id, "redirect": url_for("main_bp.analysis_page")})

    flash("Patient saved successfully.", "success")
    return redirect(url_for("main_bp.analysis_page"))


@main_bp.route("/register-page")
def register_page():
    """Backward-compatible alias for the patient registration page."""
    return redirect(url_for("main_bp.register_patient"))


@main_bp.route("/analysis")
def analysis_page():
    """Render the gait analysis page."""
    patient_id = session.get("patient_id")
    patient = session.get("patient", {})
    if patient_id:
        patient_record = Patient.query.get(patient_id)
        if patient_record:
            patient = patient_record.to_dict()
            session["patient"] = patient
    return render_template("analysis.html", patient=patient, screening_mode=session.get("screening_mode", "LIVE"), **_lang_context())


@main_bp.route("/history")
def history_page():
    """Render the patient history page using joined patient and screening records."""
    screenings = Screening.query.join(Patient, Screening.patient_id == Patient.id).order_by(Screening.timestamp.desc()).all()
    return render_template("history.html", history=screenings, **_lang_context())


@main_bp.route("/settings", methods=["GET", "POST"])
def settings_page():
    """Render the settings/preferences page."""
    if request.method == "POST":
        selected_language = request.form.get("language")
        if selected_language in SUPPORTED_LANGUAGE_CODES:
            session["language"] = selected_language
            flash("Language settings saved.", "success")
        else:
            flash("Unsupported language selected.", "error")
        return redirect(url_for("main_bp.settings_page"))

    return render_template("settings.html", **_lang_context())


@main_bp.route("/api/translations/<lang>")
def get_translations(lang: str):
    """Return the translation dictionary for the requested language."""
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return jsonify({"language": lang, "translations": translations})
