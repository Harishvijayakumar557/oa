from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "oa_model.pkl"
SCALER_PATH = PROJECT_ROOT / "models" / "scaler.pkl"

FEATURE_NAMES = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
]

FEATURE_NORMALS = {
    "gait_speed": {"min": 1.20, "max": 1.40, "unit": "m/s", "label": "Gait Speed"},
    "stride_time": {"min": 1.00, "max": 1.10, "unit": "s", "label": "Stride Time"},
    "stride_length": {"min": 1.25, "max": 1.45, "unit": "m", "label": "Stride Length"},
    "cadence": {"min": 110.0, "max": 120.0, "unit": "steps/min", "label": "Cadence"},
    "knee_rom": {"min": 55.0, "max": 65.0, "unit": "°", "label": "Knee ROM"},
    "step_time_std": {"min": 0.02, "max": 0.04, "unit": "s", "label": "Step Time Std"},
}

FEATURE_INTERPRETATIONS = {
    "gait_speed": "Lower gait speed is a common indicator of knee OA-related mobility reduction.",
    "stride_time": "Longer stride time suggests reduced efficiency and slower walking rhythm.",
    "stride_length": "Shorter stride length often reflects pain, stiffness, or reduced confidence in gait.",
    "cadence": "Reduced cadence is associated with slower and less fluid walking patterns.",
    "knee_rom": "Restricted knee range of motion may indicate joint stiffness or structural limitation.",
    "step_time_std": "Higher variability in step timing suggests instability and less consistent gait control.",
}


def load_model_bundle() -> tuple[Any, Any]:
    """Load the trained OA model and scaler from disk."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
    if not SCALER_PATH.exists():
        raise FileNotFoundError(f"Scaler file not found: {SCALER_PATH}")

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return model, scaler


def validate_features(raw_features: dict[str, Any]) -> dict[str, float]:
    """Validate and normalize incoming gait feature values before ML prediction."""
    if not isinstance(raw_features, dict):
        raise ValueError("Feature payload must be a dictionary.")

    cleaned: dict[str, float] = {}
    for feature in FEATURE_NAMES:
        if feature not in raw_features:
            raise ValueError(f"Missing required feature: {feature}")

        try:
            value = float(raw_features[feature])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Feature {feature} must be numeric.") from exc

        if value <= 0:
            raise ValueError(f"Feature {feature} must be positive.")
        cleaned[feature] = value
    return cleaned


def _status_for_feature(name: str, value: float) -> str:
    bounds = FEATURE_NORMALS[name]
    low_limit = bounds["min"]
    high_limit = bounds["max"]
    if value < low_limit or value > high_limit:
        return "abnormal"
    return "normal"


def _deviation_percent(name: str, value: float) -> float:
    bounds = FEATURE_NORMALS[name]
    low = bounds["min"]
    high = bounds["max"]
    center = (low + high) / 2
    if value <= 0:
        return 0.0
    if value < low:
        return round(((low - value) / max(center, 1e-6)) * 100, 1)
    if value > high:
        return round(((value - high) / max(high, 1e-6)) * 100, 1)
    return 0.0


def build_feature_analysis(features: dict[str, float]) -> list[dict[str, Any]]:
    """Return structured feature analysis for the medical dashboard and report."""
    rows: list[dict[str, Any]] = []
    for name in FEATURE_NAMES:
        value = float(features.get(name, 0.0))
        bounds = FEATURE_NORMALS[name]
        status = _status_for_feature(name, value)
        deviation = _deviation_percent(name, value)
        row = {
            "feature": name,
            "label": bounds["label"],
            "value": round(value, 4),
            "unit": bounds["unit"],
            "normal_range": f"{bounds['min']} - {bounds['max']} {bounds['unit']}",
            "normal_min": bounds["min"],
            "normal_max": bounds["max"],
            "status": status,
            "status_label": "Normal" if status == "normal" else "Abnormal",
            "deviation_percent": deviation,
            "clinical_note": FEATURE_INTERPRETATIONS[name],
        }
        rows.append(row)
    return rows
