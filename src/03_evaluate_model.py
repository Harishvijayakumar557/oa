# Disclaimer: This evaluation script analyzes synthetic gait data for research and prototyping only.
# It is not a validated clinical tool and must not be used for medical diagnosis or treatment decisions.

from __future__ import annotations

import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import label_binarize
from sklearn.svm import SVC
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "synthetic_gait.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "oa_model.pkl"
SCALER_PATH = PROJECT_ROOT / "models" / "scaler.pkl"
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
CLASS_NAMES = ["Low", "Moderate", "High"]


def load_assets() -> tuple[pd.DataFrame, object, object]:
    df = pd.read_csv(DATA_PATH)
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return df, model, scaler


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    accuracy = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    kappa = cohen_kappa_score(y_true, y_pred)

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "kappa": kappa,
    }


def plot_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    per_class = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    values = [per_class[str(i)]["f1-score"] for i in range(3)]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(CLASS_NAMES, values, color=["#4C78A8", "#F58518", "#54A24B"])
    ax.set_title("Per-Class F1 Score")
    ax.set_xlabel("Class")
    ax.set_ylabel("F1 Score")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.3f}", ha="center")
    fig.tight_layout()
    fig.savefig(DOCS_DIR / "per_class_f1_bar.png", dpi=300)
    plt.close(fig)


def plot_roc_curves(model: object, X_test: np.ndarray, y_test: np.ndarray) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if not hasattr(model, "predict_proba"):
        print("Model does not support predict_proba; skipping ROC plot.")
        return

    y_test_bin = label_binarize(y_test, classes=[0, 1, 2])
    y_score = model.predict_proba(X_test)
    fig, ax = plt.subplots(figsize=(8, 6))

    for i in range(3):
        fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_score[:, i])
        ax.plot(fpr, tpr, label=f"{CLASS_NAMES[i]} vs Rest")

    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves (One-vs-Rest)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(DOCS_DIR / "roc_curves.png", dpi=300)
    plt.close(fig)


def plot_cv_boxplot(cv_scores: np.ndarray) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.boxplot(cv_scores, patch_artist=True, boxprops={"facecolor": "lightsteelblue"})
    ax.set_title("5-Fold Cross-Validation Accuracy Distribution")
    ax.set_ylabel("Accuracy")
    ax.set_xticks([])
    fig.tight_layout()
    fig.savefig(DOCS_DIR / "cv_accuracy_boxplot.png", dpi=300)
    plt.close(fig)


def plot_feature_ranking(model: object, feature_names: list[str]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        ranking = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        names = [item[0] for item in ranking]
        values = [item[1] for item in ranking]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(names, values, color="steelblue")
        ax.invert_yaxis()
        ax.set_title("Feature Importance Ranking")
        ax.set_xlabel("Importance")
        fig.tight_layout()
        fig.savefig(DOCS_DIR / "feature_ranking.png", dpi=300)
        plt.close(fig)

        print("\nTop 3 most important features:")
        for name, value in ranking[:3]:
            print(f"- {name}: {value:.4f}")
    else:
        print("Model does not provide feature importance; feature ranking plot skipped.")


def write_report(report_text: str) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "evaluation_report.txt"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\nSaved evaluation report: {report_path}")


def main() -> None:
    df, model, scaler = load_assets()
    if df.empty:
        raise ValueError("Data is empty.")

    X = df[FEATURES].values
    y = df[TARGET].values

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)

    print("\nDetailed classification report:")
    report = classification_report(y_test, y_pred, target_names=CLASS_NAMES, digits=4, zero_division=0)
    print(report)

    metrics = compute_metrics(y_test, y_pred)
    print("\nEvaluation metrics:")
    print(f"Overall accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1:        {metrics['macro_f1']:.4f}")
    print(f"Weighted F1:     {metrics['weighted_f1']:.4f}")
    print(f"Cohen's kappa:   {metrics['kappa']:.4f}")

    # 5-fold CV on full dataset
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    X_scaled = scaler.transform(X)
    accuracy_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="accuracy")
    f1_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="f1_weighted")

    print("\n5-fold cross-validation:")
    print(f"Accuracy mean ± std: {accuracy_scores.mean():.4f} ± {accuracy_scores.std():.4f}")
    print(f"F1 mean ± std:       {f1_scores.mean():.4f} ± {f1_scores.std():.4f}")

    plot_per_class_f1(y_test, y_pred)
    plot_roc_curves(model, X_test_scaled, y_test)
    plot_cv_boxplot(accuracy_scores)
    plot_feature_ranking(model, FEATURES)

    report_lines = [
        "OA Screening Model Evaluation Report",
        "=" * 40,
        "Disclaimer: This evaluation is based on synthetic gait data for research and prototype assessment only.",
        "It is not a medical diagnostic instrument.",
        "",
        f"Dataset shape: {df.shape}",
        f"Class distribution: {df[TARGET].value_counts().sort_index().to_dict()}",
        "",
        "Detailed classification report:",
        report,
        "",
        "Computed metrics:",
        f"Overall accuracy: {metrics['accuracy']:.4f}",
        f"Macro F1:        {metrics['macro_f1']:.4f}",
        f"Weighted F1:     {metrics['weighted_f1']:.4f}",
        f"Cohen's kappa:   {metrics['kappa']:.4f}",
        "",
        "5-fold cross-validation:",
        f"Accuracy mean ± std: {accuracy_scores.mean():.4f} ± {accuracy_scores.std():.4f}",
        f"F1 mean ± std:       {f1_scores.mean():.4f} ± {f1_scores.std():.4f}",
    ]
    write_report("\n".join(report_lines))

    print("\nFinal evaluation summary")
    print("=" * 40)
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Weighted F1: {metrics['weighted_f1']:.4f}")
    print(f"Cohen's kappa: {metrics['kappa']:.4f}")
    print(f"Best model artifact loaded: {MODEL_PATH.name}")
    print(f"Saved docs: {DOCS_DIR}")


if __name__ == "__main__":
    main()
