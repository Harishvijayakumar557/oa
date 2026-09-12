# Disclaimer: This script trains models on synthetic gait data for research and prototype evaluation only.
# It is not clinical-grade software and must not be used for medical diagnosis or treatment decisions.

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "synthetic_gait.csv"
MODEL_DIR = PROJECT_ROOT / "models"
DOCS_DIR = PROJECT_ROOT / "docs"
FEATURES = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
]
TARGET = "label"


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded data shape: {df.shape}")
    print("Class distribution:")
    print(df[TARGET].value_counts().sort_index())
    return df


def build_models() -> dict:
    return {
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
        "XGBoost": XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            objective="multi:softprob",
            num_class=3,
            random_state=42,
            eval_metric="mlogloss",
        ),
        "SVM": SVC(kernel="rbf", class_weight="balanced", probability=True, random_state=42),
    }


def evaluate_model(name: str, model: object, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "model_name": name,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, average="weighted", zero_division=0),
        "recall": recall_score(y_test, y_pred, average="weighted", zero_division=0),
        "f1": f1_score(y_test, y_pred, average="weighted", zero_division=0),
        "report": classification_report(y_test, y_pred, digits=4),
        "confusion": confusion_matrix(y_test, y_pred),
        "predictions": y_pred,
    }

    print(f"\n=== {name} ===")
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1:        {metrics['f1']:.4f}")
    print(metrics["report"])
    return metrics


def save_confusion_matrix(cm: np.ndarray, label_names: list[str]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=label_names, yticklabels=label_names, ax=ax)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title("Best Model Confusion Matrix")
    fig.tight_layout()
    fig.savefig(DOCS_DIR / "best_model_confusion_matrix.png", dpi=300)
    plt.close(fig)


def plot_feature_importance(model_name: str, model: object, feature_names: list[str]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        order = np.argsort(importances)[::-1]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh([feature_names[i] for i in order], importances[order])
        ax.invert_yaxis()
        ax.set_title(f"{model_name} Feature Importance")
        ax.set_xlabel("Importance")
        fig.tight_layout()
        fig.savefig(DOCS_DIR / f"{model_name.lower()}_feature_importance.png", dpi=300)
        plt.close(fig)
    else:
        print(f"{model_name} does not expose feature_importances_. Skipping plot.")


def plot_model_comparison(results: list[dict]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    names = [result["model_name"] for result in results]
    f1_values = [result["f1"] for result in results]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(names, f1_values, color=["steelblue", "darkorange", "forestgreen"])
    ax.set_title("Model Comparison by Weighted F1 Score")
    ax.set_xlabel("Model")
    ax.set_ylabel("F1 Score")
    for i, value in enumerate(f1_values):
        ax.text(i, value + 0.01, f"{value:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(DOCS_DIR / "model_comparison_f1.png", dpi=300)
    plt.close(fig)


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(DATA_PATH)
    if df.empty:
        raise ValueError("Dataset is empty. Check the input path.")

    print(f"Feature columns: {FEATURES}")
    print(f"Target column: {TARGET}")

    X = df[FEATURES].values
    y = df[TARGET].values

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    print(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")
    print(f"Train class balance: {np.bincount(y_train)}")
    print(f"Test class balance: {np.bincount(y_test)}")

    results = []
    models = build_models()

    for model_name, model in models.items():
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        result = evaluate_model(model_name, model, X_train_scaled, y_train, X_test_scaled, y_test)
        results.append(result)

        if model_name in ["RandomForest", "XGBoost"]:
            joblib.dump(model, MODEL_DIR / f"{model_name.lower()}_model.pkl")
            plot_feature_importance(model_name, model, FEATURES)

    best_result = max(results, key=lambda r: r["f1"])
    best_model_name = best_result["model_name"]
    best_model = models[best_model_name]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    best_model.fit(X_train_scaled, y_train)
    joblib.dump(best_model, MODEL_DIR / "oa_model.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")

    save_confusion_matrix(best_result["confusion"], ["Low", "Moderate", "High"])
    plot_model_comparison(results)

    print("\nFinal Summary")
    print("=" * 40)
    print(f"Best model: {best_model_name}")
    print(f"Best F1 score: {best_result['f1']:.4f}")
    print(f"Best accuracy: {best_result['accuracy']:.4f}")
    print(f"Saved model to: {MODEL_DIR / 'oa_model.pkl'}")
    print(f"Saved scaler to: {MODEL_DIR / 'scaler.pkl'}")


if __name__ == "__main__":
    main()
