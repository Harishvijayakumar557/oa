from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_generation import generate_dataset
from src.feature_engineering import prepare_training_data
from src.train_model import FEATURE_COLUMNS
from src.utils import MODEL_DIR, PROCESSED_DATA_DIR


def evaluate_model() -> dict:
    raw_path = PROCESSED_DATA_DIR / "synthetic_gait_data.csv"
    if not raw_path.exists():
        generate_dataset()

    raw_df = pd.read_csv(raw_path)
    processed = prepare_training_data(raw_df)
    model = joblib.load(MODEL_DIR / "oa_gait_model.joblib")

    features = processed[FEATURE_COLUMNS]
    labels = processed["target"]
    preds = model.predict(features)
    accuracy = (preds == labels).mean()
    report = classification_report(labels, preds, output_dict=True)

    print(f"Overall accuracy on generated dataset: {accuracy:.4f}")
    print("Classification report:")
    print(classification_report(labels, preds))
    return {"accuracy": float(accuracy), "report": report}


if __name__ == "__main__":
    evaluate_model()
