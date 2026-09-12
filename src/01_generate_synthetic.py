# Disclaimer: This synthetic gait dataset is generated for research, prototyping, and educational use only.
# It is not clinical-grade data and should not be used as a medical diagnosis or treatment recommendation.

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"


PARAMS = {
    0: {
        "name": "Healthy",
        "gait_speed": (1.30, 0.15),
        "stride_time": (1.05, 0.08),
        "stride_length": (1.35, 0.12),
        "cadence": (115.0, 8.0),
        "knee_rom": (60.0, 5.0),
        "step_time_std": (0.03, 0.01),
    },
    1: {
        "name": "Moderate_OA",
        "gait_speed": (1.10, 0.18),
        "stride_time": (1.12, 0.10),
        "stride_length": (1.22, 0.13),
        "cadence": (107.0, 9.0),
        "knee_rom": (52.0, 6.0),
        "step_time_std": (0.05, 0.02),
    },
    2: {
        "name": "Severe_OA",
        "gait_speed": (0.95, 0.20),
        "stride_time": (1.20, 0.12),
        "stride_length": (1.10, 0.15),
        "cadence": (100.0, 10.0),
        "knee_rom": (45.0, 8.0),
        "step_time_std": (0.08, 0.03),
    },
}

FEATURES = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
]


def generate_sample(label: int, rng: np.random.Generator) -> dict:
    cfg = PARAMS[label]
    sample = {"label": label}

    for feature in FEATURES:
        mean, std = cfg[feature]
        sample[feature] = float(rng.normal(loc=mean, scale=std))

    return sample


def generate_dataset(n_per_class: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for label in [0, 1, 2]:
        for _ in range(n_per_class):
            rows.append(generate_sample(label, rng))

    df = pd.DataFrame(rows)
    return df


def print_summary(df: pd.DataFrame) -> None:
    print("Synthetic Gait Dataset Summary")
    print("=" * 40)
    print(f"Total samples: {len(df)}")
    print(df["label"].value_counts().sort_index().to_string())
    print("\nGroup statistics by label:")
    print(df.groupby("label")[FEATURES].mean().round(3).to_string())
    print("\nOverall feature summary:")
    print(df[FEATURES].describe().round(3).to_string())


def plot_histograms(df: pd.DataFrame) -> None:
    docs_dir = DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(len(FEATURES), 1, figsize=(10, 16), sharex=False)
    for ax, feature in zip(axes, FEATURES):
        for label in [0, 1, 2]:
            subset = df[df["label"] == label][feature]
            ax.hist(
                subset,
                bins=25,
                alpha=0.6,
                label=f"Label {label}",
                density=True,
            )
        ax.set_title(f"Histogram of {feature}")
        ax.set_xlabel(feature)
        ax.set_ylabel("Density")
        ax.legend()

    fig.tight_layout()
    fig.savefig(docs_dir / "gait_feature_histograms.png", dpi=300)
    plt.close(fig)


def plot_pairplot(df: pd.DataFrame) -> None:
    docs_dir = DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)

    pairplot = sns.pairplot(
        df,
        vars=FEATURES,
        hue="label",
        palette={0: "green", 1: "orange", 2: "red"},
        diag_kind="hist",
        plot_kws={"alpha": 0.75, "s": 14},
        height=2.2,
    )
    pairplot.savefig(docs_dir / "gait_pairplot.png", dpi=300, bbox_inches="tight")
    plt.close(pairplot.fig)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    df = generate_dataset(n_per_class=500, seed=42)
    output_path = DATA_DIR / "synthetic_gait.csv"
    df.to_csv(output_path, index=False)

    print(f"Saved dataset to: {output_path}")
    print_summary(df)

    plot_histograms(df)
    plot_pairplot(df)

    print("\nSaved visualizations:")
    print(f"- {DOCS_DIR / 'gait_feature_histograms.png'}")
    print(f"- {DOCS_DIR / 'gait_pairplot.png'}")


if __name__ == "__main__":
    main()
