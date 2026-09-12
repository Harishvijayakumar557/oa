from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import PROCESSED_DATA_DIR, ensure_directories


def generate_synthetic_gait_sample(
    rng: np.random.Generator,
    risk_label: str,
    sample_id: int,
    steps: int = 30,
) -> pd.DataFrame:
    risk_map = {
        "Low": {"amp": 0.9, "variance": 0.08, "asymmetry": 0.05, "cadence": 1.0},
        "Moderate": {"amp": 1.3, "variance": 0.15, "asymmetry": 0.12, "cadence": 1.2},
        "High": {"amp": 1.7, "variance": 0.22, "asymmetry": 0.2, "cadence": 1.5},
    }

    cfg = risk_map[risk_label]
    t = np.linspace(0, 2 * np.pi * steps, steps)

    left_accel_x = np.sin(t) * cfg["amp"] + rng.normal(0, cfg["variance"], size=steps)
    left_accel_y = np.cos(t * 1.5) * (cfg["amp"] * 0.7) + rng.normal(0, cfg["variance"], size=steps)
    right_accel_x = np.sin(t + 0.25) * (cfg["amp"] * (1 - cfg["asymmetry"])) + rng.normal(0, cfg["variance"], size=steps)
    right_accel_y = np.cos((t * 1.5) + 0.15) * (cfg["amp"] * 0.75) + rng.normal(0, cfg["variance"], size=steps)

    left_gyro_z = np.sin(t * 1.2) * (8 + cfg["cadence"] * 4) + rng.normal(0, 1.2, size=steps)
    right_gyro_z = np.sin(t * 1.2 + 0.3) * (8 + cfg["cadence"] * 4) + rng.normal(0, 1.2, size=steps)

    df = pd.DataFrame(
        {
            "sample_id": sample_id,
            "risk_label": risk_label,
            "left_accel_x": left_accel_x,
            "left_accel_y": left_accel_y,
            "right_accel_x": right_accel_x,
            "right_accel_y": right_accel_y,
            "left_gyro_z": left_gyro_z,
            "right_gyro_z": right_gyro_z,
            "step_index": np.arange(steps),
        }
    )

    return df


def generate_dataset(n_samples_per_class: int = 200, output_path: str | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    labels = ["Low", "Moderate", "High"]
    frames = []

    for risk_label in labels:
        for i in range(n_samples_per_class):
            sample_id = len(frames) + 1
            frames.append(generate_synthetic_gait_sample(rng, risk_label, sample_id))

    combined = pd.concat(frames, ignore_index=True)
    path = output_path or str(PROCESSED_DATA_DIR / "synthetic_gait_data.csv")
    combined.to_csv(path, index=False)
    return combined


if __name__ == "__main__":
    ensure_directories()
    df = generate_dataset()
    print(f"Generated synthetic gait dataset with {len(df)} rows.")
    print(f"Saved to: {PROCESSED_DATA_DIR / 'synthetic_gait_data.csv'}")
