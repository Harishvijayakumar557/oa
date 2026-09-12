from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
from flask import Blueprint, jsonify, request, session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask_app.models.database import db
from flask_app.models.patient import Patient
from flask_app.models.report import Report
from flask_app.models.screening import Screening
from flask_app.models_loader import FEATURE_NAMES, build_feature_analysis, load_model_bundle, validate_features

predict_bp = Blueprint("predict_bp", __name__)
RISK_LABELS = {0: "Low Risk", 1: "Moderate Risk", 2: "High Risk"}


def _create_report_record(screening: Screening, prediction: dict, patient_data: dict, feature_analysis: list[dict]) -> Report:
    report_prefix = f"OA-{dt.datetime.now().strftime('%Y%m%d')}"
    report_id = f"{report_prefix}-{screening.id:04d}"
    reports_dir = Path(__file__).resolve().parents[1] / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = reports_dir / f"{report_id}.pdf"

    from flask_app.report_generator import build_report_bytes

    pdf_bytes = build_report_bytes(
        patient_data=patient_data,
        prediction=prediction,
        feature_analysis=feature_analysis,
        report_id=report_id,
        language=session.get("language", "en"),
    )
    pdf_path.write_bytes(pdf_bytes)

    report = Report(screening_id=screening.id, report_id=report_id, pdf_path=str(pdf_path))
    db.session.add(report)
    db.session.commit()
    return report


@predict_bp.route("/api/predict", methods=["POST"])
def predict_api():
    """Predict OA risk from a feature payload and store the screening result."""
    data = request.get_json(silent=True) or {}
    features = data.get("features") or data
    mode = str(data.get("mode") or session.get("screening_mode") or "LIVE").upper()

    try:
        feature_values = validate_features(features)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    patient_id = data.get("patient_id") or session.get("patient_id")
    patient = Patient.query.get(patient_id) if patient_id else None
    if patient is None:
        patient_data = session.get("patient") or {}
        if not patient_data:
            return jsonify({"success": False, "error": "Patient registration is required before screening."}), 400
        patient = Patient.query.filter_by(name=patient_data.get("name")).first()
        if patient is None:
            patient = Patient(
                name=patient_data.get("name") or "Unknown Patient",
                age=patient_data.get("age"),
                gender=patient_data.get("gender"),
                phone=patient_data.get("phone"),
                email=patient_data.get("email"),
                address=patient_data.get("address"),
                medical_history=patient_data.get("medical_history"),
                state=patient_data.get("state"),
                district=patient_data.get("district"),
                village_town=patient_data.get("village_town"),
                occupation=patient_data.get("occupation"),
                screening_mode=mode,
            )
            db.session.add(patient)
            db.session.commit()

    model, scaler = load_model_bundle()
    frame = pd.DataFrame([feature_values], columns=FEATURE_NAMES)
    scaled = scaler.transform(frame)
    predicted_class = int(model.predict(scaled)[0])
    probabilities = model.predict_proba(scaled)[0]
    confidence = float(max(probabilities))
    analysis = build_feature_analysis(feature_values)

    screening = Screening(
        patient_id=patient.id,
        mode=mode,
        gait_speed=float(feature_values.get("gait_speed", 0.0)),
        stride_time=float(feature_values.get("stride_time", 0.0)),
        stride_length=float(feature_values.get("stride_length", 0.0)),
        cadence=float(feature_values.get("cadence", 0.0)),
        knee_rom=float(feature_values.get("knee_rom", 0.0)),
        step_time_std=float(feature_values.get("step_time_std", 0.0)),
        risk_class=predicted_class,
        risk_label=RISK_LABELS.get(predicted_class, "Low Risk"),
        confidence=round(confidence, 4),
        timestamp=dt.datetime.utcnow(),
    )
    db.session.add(screening)
    db.session.commit()

    report = _create_report_record(
        screening,
        {
            "class": predicted_class,
            "label": RISK_LABELS.get(predicted_class, "Low Risk"),
            "confidence": round(confidence, 4),
            "probabilities": {
                "low": round(float(probabilities[0]), 4),
                "moderate": round(float(probabilities[1]), 4),
                "high": round(float(probabilities[2]), 4),
            },
        },
        patient.to_dict(),
        analysis,
    )

    output = {
        "success": True,
        "patient": patient.to_dict(),
        "screening_id": screening.id,
        "report_id": report.report_id,
        "redirect_url": f"/report/{screening.id}",
        "prediction": {
            "class": predicted_class,
            "label": RISK_LABELS.get(predicted_class, "Low Risk"),
            "confidence": round(confidence, 4),
            "probabilities": {
                "low": round(float(probabilities[0]), 4),
                "moderate": round(float(probabilities[1]), 4),
                "high": round(float(probabilities[2]), 4),
            },
        },
        "features": feature_values,
        "feature_analysis": analysis,
        "timestamp": dt.datetime.utcnow().isoformat(),
    }
    return jsonify(output)


@predict_bp.route("/api/upload-csv", methods=["POST"])
def upload_csv():
    """Accept a CSV upload containing gait features and return a prediction."""
    file = request.files.get("file")
    if file is None:
        return jsonify({"success": False, "error": "CSV file missing."}), 400

    try:
        df = pd.read_csv(file)
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed to read CSV: {exc}"}), 400

    missing = [name for name in FEATURE_NAMES if name not in df.columns]
    if missing:
        return jsonify({"success": False, "error": f"CSV missing required columns: {missing}"}), 400

    sample = df.iloc[0].to_dict()
    try:
        feature_values = validate_features(sample)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    model, scaler = load_model_bundle()
    frame = pd.DataFrame([feature_values], columns=FEATURE_NAMES)
    scaled = scaler.transform(frame)
    prediction = int(model.predict(scaled)[0])
    probabilities = model.predict_proba(scaled)[0]

    return jsonify({
        "success": True,
        "prediction": {
            "class": prediction,
            "label": RISK_LABELS.get(prediction, "Low Risk"),
            "confidence": round(float(max(probabilities)), 4),
            "probabilities": {
                "low": round(float(probabilities[0]), 4),
                "moderate": round(float(probabilities[1]), 4),
                "high": round(float(probabilities[2]), 4),
            },
        },
        "features": feature_values,
    })


@predict_bp.route("/api/health")
def health_check():
    """Return the health status of the ML pipeline."""
    try:
        load_model_bundle()
        return jsonify({"status": "ok", "message": "Model and scaler loaded successfully."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 503
