from __future__ import annotations

import pandas as pd


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    aggregated = (
        df.groupby(["sample_id", "risk_label"], as_index=False)
        .agg(
            left_peak_accel_x=("left_accel_x", "max"),
            left_peak_accel_y=("left_accel_y", "max"),
            right_peak_accel_x=("right_accel_x", "max"),
            right_peak_accel_y=("right_accel_y", "max"),
            left_gyro_std=("left_gyro_z", "std"),
            right_gyro_std=("right_gyro_z", "std"),
            left_mean_accel_x=("left_accel_x", "mean"),
            right_mean_accel_x=("right_accel_x", "mean"),
            left_mean_accel_y=("left_accel_y", "mean"),
            right_mean_accel_y=("right_accel_y", "mean"),
            step_count=("step_index", "count"),
        )
        .copy()
    )

    aggregated["gait_asymmetry"] = (
        aggregated["left_peak_accel_x"] - aggregated["right_peak_accel_x"]
    ).abs() / (aggregated["left_peak_accel_x"] + aggregated["right_peak_accel_x"] + 1e-6)

    aggregated["cadence"] = aggregated["step_count"] / 10.0
    aggregated["stability_index"] = (
        aggregated["left_gyro_std"] + aggregated["right_gyro_std"]
    ) / 2.0

    aggregated["vertical_displacement"] = (
        aggregated["left_peak_accel_y"] + aggregated["right_peak_accel_y"]
    ) / 2.0

    aggregated["stride_balance"] = (
        aggregated["left_mean_accel_x"] - aggregated["right_mean_accel_x"]
    ).abs()

    return aggregated


def prepare_training_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    features = engineer_features(raw_df)
    target_mapping = {"Low": 0, "Moderate": 1, "High": 2}
    features["risk_label"] = features["risk_label"].map(target_mapping)
    features = features.rename(columns={"risk_label": "target"})
    return features
