from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_PATH = DATA_DIR / "sample_patients.csv"


def generate_samples() -> pd.DataFrame:
    """Generate five demo patients covering low, moderate, and high-risk gait values."""
    rows = [
        {
            "patient_id": "P001",
            "risk_level": "Low",
            "gait_speed": 1.38,
            "stride_time": 1.06,
            "stride_length": 1.40,
            "cadence": 116.0,
            "knee_rom": 60.0,
            "step_time_std": 0.028,
        },
        {
            "patient_id": "P002",
            "risk_level": "Low",
            "gait_speed": 1.30,
            "stride_time": 1.02,
            "stride_length": 1.36,
            "cadence": 114.0,
            "knee_rom": 58.0,
            "step_time_std": 0.031,
        },
        {
            "patient_id": "P003",
            "risk_level": "Moderate",
            "gait_speed": 1.12,
            "stride_time": 1.12,
            "stride_length": 1.22,
            "cadence": 107.0,
            "knee_rom": 52.0,
            "step_time_std": 0.050,
        },
        {
            "patient_id": "P004",
            "risk_level": "Moderate",
            "gait_speed": 1.08,
            "stride_time": 1.15,
            "stride_length": 1.18,
            "cadence": 104.0,
            "knee_rom": 49.0,
            "step_time_std": 0.061,
        },
        {
            "patient_id": "P005",
            "risk_level": "High",
            "gait_speed": 0.94,
            "stride_time": 1.24,
            "stride_length": 1.09,
            "cadence": 98.0,
            "knee_rom": 42.0,
            "step_time_std": 0.083,
        },
    ]
    return pd.DataFrame(rows)


def main() -> None:
    """Generate and save the sample patient dataset."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_samples()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved sample patient data to: {OUTPUT_PATH}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
