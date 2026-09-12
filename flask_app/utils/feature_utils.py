from __future__ import annotations

from typing import Any

FEATURE_NAMES = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
]


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

        if value <= 0 and feature in {"gait_speed", "stride_time", "stride_length", "cadence", "knee_rom", "step_time_std"}:
            raise ValueError(f"Feature {feature} must be positive.")
        cleaned[feature] = value

    return cleaned


def FEATURE_NORMALS() -> dict[str, str]:
    """Return the expected normal bands used for UI display."""
    return {
        "gait_speed": "1.2-1.4",
        "stride_time": "1.0-1.1",
        "stride_length": "1.2-1.4",
        "cadence": "105-120",
        "knee_rom": "45-65",
        "step_time_std": "0.02-0.08",
    }


def build_feature_analysis(features: dict[str, float]) -> list[dict[str, Any]]:
    """Convert feature values into structured analysis rows for UI display."""
    normals = FEATURE_NORMALS()
    rows: list[dict[str, Any]] = []
    for name in FEATURE_NAMES:
        value = float(features.get(name, 0.0))
        normal = normals.get(name, "N/A")
        status = "normal"
        if name == "gait_speed":
            status = "low" if value < 1.2 else "high" if value > 1.4 else "normal"
        elif name == "stride_time":
            status = "low" if value < 1.0 else "high" if value > 1.1 else "normal"
        elif name == "stride_length":
            status = "low" if value < 1.2 else "high" if value > 1.4 else "normal"
        elif name == "cadence":
            status = "low" if value < 105 else "high" if value > 120 else "normal"
        elif name == "knee_rom":
            status = "low" if value < 45 else "high" if value > 65 else "normal"
        elif name == "step_time_std":
            status = "low" if value < 0.02 else "high" if value > 0.08 else "normal"

        rows.append({
            "name": name,
            "value": round(value, 4),
            "normal": normal,
            "status": status,
        })
    return rows
