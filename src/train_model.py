from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_generation import generate_dataset
from src.feature_engineering import prepare_training_data
from src.utils import MODEL_DIR, PROCESSED_DATA_DIR, ensure_directories


FEATURE_COLUMNS = [
    "left_peak_accel_x",
    "left_peak_accel_y",
    "right_peak_accel_x",
    "right_peak_accel_y",
    "left_gyro_std",
    "right_gyro_std",
    "gait_asymmetry",
    "cadence",
    "stability_index",
    "vertical_displacement",
    "stride_balance",
]


def train_and_save_model() -> dict:
    ensure_directories()
    raw_data_path = PROCESSED_DATA_DIR / "synthetic_gait_data.csv"
    if not raw_data_path.exists():
        generate_dataset()

    raw_df = pd.read_csv(raw_data_path)
    data = prepare_training_data(raw_df)

    X = data[FEATURE_COLUMNS]
    y = data["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        n_estimators=250,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions, output_dict=True)
    cm = confusion_matrix(y_test, predictions)

    model_path = MODEL_DIR / "oa_gait_model.joblib"
    joblib.dump(model, model_path)

    metrics = {
        "accuracy": float(accuracy),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "model_path": str(model_path),
    }
    return metrics


if __name__ == "__main__":
    metrics = train_and_save_model()
    print(f"Model accuracy: {metrics['accuracy']:.4f}")
    print(f"Saved model to: {metrics['model_path']}")
