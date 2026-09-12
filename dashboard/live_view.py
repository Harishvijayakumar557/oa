from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DATA_PATH = PROJECT_ROOT / "data" / "latest_prediction.json"
HISTORY_PATH = PROJECT_ROOT / "data" / "live_predictions.csv"


def load_latest_prediction(path: Path = LIVE_DATA_PATH) -> dict:
    """Load the current prediction JSON if it exists and is valid."""
    if not path.exists():
        return {"status": "waiting", "message": "Waiting for ESP32..."}

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not payload:
            return {"status": "waiting", "message": "Waiting for ESP32..."}
        return payload
    except (json.JSONDecodeError, OSError):
        return {"status": "error", "message": "ESP32 data file unreadable."}


def ensure_history() -> pd.DataFrame:
    """Return the live predictions history as a DataFrame, if present."""
    if not HISTORY_PATH.exists():
        return pd.DataFrame(columns=[
            "timestamp",
            "gait_speed",
            "stride_time",
            "stride_length",
            "cadence",
            "knee_rom",
            "step_time_std",
            "predicted_class",
            "label",
            "confidence",
        ])
    return pd.read_csv(HISTORY_PATH)


def build_knee_angle_history(history_df: pd.DataFrame, window_seconds: int = 10) -> list[float]:
    """Create a simple rolling knee-angle series from the available data when present."""
    if history_df.empty:
        return [0.0] * 20

    if "knee_rom" not in history_df.columns:
        return [0.0] * 20

    series = history_df["knee_rom"].dropna().astype(float).tolist()
    if not series:
        return [0.0] * 20
    if len(series) < 20:
        return series + [series[-1]] * (20 - len(series))
    return series[-20:]


def render_live_view() -> None:
    """Render the live OA screening dashboard panel with auto-refreshing status."""
    st.set_page_config(page_title="OA Live View", page_icon="📡", layout="wide")
    st.title("ESP32 Live OA Screening")
    st.caption("⚠️ For screening only, not medical diagnosis.")

    placeholder = st.empty()
    history_placeholder = st.empty()
    chart_placeholder = st.empty()

    while True:
        with placeholder.container():
            payload = load_latest_prediction()
            history_df = ensure_history()

            if payload.get("status") in {"waiting", "error"}:
                st.warning(payload.get("message", "Waiting for ESP32..."))
                st.info("Waiting for ESP32 serial stream and prediction JSON update...")
                st.stop()

            timestamp = payload.get("timestamp", "N/A")
            features = payload.get("features", {})
            prediction = payload.get("prediction", {})
            confidence = payload.get("confidence") or prediction.get("confidence")
            label = prediction.get("label", "Unknown")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Connection", "ESP32 Connected", delta="Live")
            with col2:
                st.metric("Risk", label, delta=f"{confidence:.2f}%" if isinstance(confidence, (int, float)) else "--")
            with col3:
                st.metric("Last update", datetime.now().strftime("%H:%M:%S"))

            st.write(f"Last timestamp: {timestamp}")

            if features:
                feature_df = pd.DataFrame([features])
                st.dataframe(feature_df, use_container_width=True)
            else:
                st.info("No live feature payload received yet.")

            with chart_placeholder.container():
                knee_history = build_knee_angle_history(history_df)
                chart_x = range(len(knee_history))
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(chart_x, knee_history, color="#2563eb", linewidth=2)
                ax.set_title("Rolling knee angle trend")
                ax.set_xlabel("Sample")
                ax.set_ylabel("Knee ROM proxy")
                ax.grid(True, alpha=0.2)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            with history_placeholder.container():
                st.subheader("Live prediction history")
                if history_df.empty:
                    st.info("No predictions recorded yet.")
                else:
                    st.dataframe(history_df.tail(10), use_container_width=True)

            if st.button("Stop live view"):
                st.stop()

        time.sleep(2)
        st.rerun()


if __name__ == "__main__":
    render_live_view()
