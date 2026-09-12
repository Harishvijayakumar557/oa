from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Iterable

import joblib
import numpy as np
import pandas as pd

try:
    import serial
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "pyserial is required. Install it with: pip install pyserial"
    ) from exc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"
MODEL_PATH = MODELS_DIR / "oa_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
CSV_LOG_PATH = DATA_DIR / "live_predictions.csv"
LATEST_PREDICTION_PATH = DATA_DIR / "latest_prediction.json"
FEATURE_NAMES = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
]
RISK_LABELS = {0: "Low", 1: "Moderate", 2: "High"}


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    CSV_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    ensure_directories()
    logger = logging.getLogger("esp32_integration")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(LOGS_DIR / "esp32_integration.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ESP32 OA screening real-time integration")
    parser.add_argument("--port", type=str, default=None, help="COM port e.g. COM3. Auto-detect if omitted.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--window", type=float, default=5.0, help="Seconds between prediction windows")
    parser.add_argument("--buffer-size", type=int, default=500, help="Number of samples stored in memory")
    return parser.parse_args()


def detect_port(preferred_port: str | None = None) -> str | None:
    if preferred_port:
        return preferred_port

    candidates = [f"COM{i}" for i in range(3, 11)]
    for port in candidates:
        try:
            test = serial.Serial(port, baudrate=115200, timeout=1)
            time.sleep(0.2)
            test.close()
            return port
        except serial.SerialException:
            continue

    try:
        import serial.tools.list_ports as list_ports

        ports = list_ports.comports()
        if ports:
            return ports[0].device
    except Exception:
        pass

    return None


def load_ml_artifacts() -> tuple[Any, Any]:
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        raise FileNotFoundError(
            f"Model/scaler not found. Expected files: {MODEL_PATH} and {SCALER_PATH}. "
            "Train the model first with python src/02_train_model.py"
        )

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return model, scaler


def ensure_csv_log_exists() -> None:
    if not CSV_LOG_PATH.exists():
        with CSV_LOG_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def save_latest_prediction(payload: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "latest_prediction.json").open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def append_prediction_csv(payload: dict[str, Any]) -> None:
    ensure_csv_log_exists()
    with CSV_LOG_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            payload["timestamp"],
            payload["features"]["gait_speed"],
            payload["features"]["stride_time"],
            payload["features"]["stride_length"],
            payload["features"]["cadence"],
            payload["features"]["knee_rom"],
            payload["features"]["step_time_std"],
            payload["prediction"]["predicted_class"],
            payload["prediction"]["label"],
            payload["prediction"]["confidence"],
        ])


def read_latest_prediction(path: str | Path = LATEST_PREDICTION_PATH) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {"timestamp": None, "features": {}, "prediction": {}, "confidence": None}

    with file_path.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {"timestamp": None, "features": {}, "prediction": {}, "confidence": None}


def get_live_prediction(path: str | Path = LATEST_PREDICTION_PATH, stale_seconds: float | None = 10.0) -> dict[str, Any]:
    """Return the most recent ESP32 prediction, optionally marking it stale if older than a timeout."""
    payload = read_latest_prediction(path)
    if not payload.get("timestamp"):
        return {"timestamp": None, "features": {}, "prediction": {}, "confidence": None, "is_stale": True}

    if stale_seconds is not None:
        try:
            ts = datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
            payload["is_stale"] = age_seconds > stale_seconds
        except ValueError:
            payload["is_stale"] = True
    else:
        payload["is_stale"] = False

    return payload


def compute_accel_angle(ax: float, ay: float, az: float) -> float:
    if az == 0:
        az = 1e-6
    angle = math.degrees(math.atan2(ay, az))
    return float(angle)


def complementary_filter(prev_angle: float, gyro_rate: float, accel_angle: float, dt: float) -> float:
    if dt <= 0:
        dt = 0.02
    return 0.98 * (prev_angle + gyro_rate * dt) + 0.02 * accel_angle


class ESP32Stream:
    def __init__(self, port: str, baudrate: int, timeout: float = 1.0) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False
        self.last_read = 0.0

    def connect(self) -> None:
        if self.serial is not None and self.serial.is_open:
            self.connected = True
            return

        self.serial = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        self.connected = True
        self.last_read = time.time()

    def reconnect(self) -> None:
        try:
            if self.serial is not None:
                self.serial.close()
        except Exception:
            pass
        self.connected = False
        self.serial = None
        time.sleep(1)
        self.connect()

    def read_line(self) -> str | None:
        if self.serial is None or not self.serial.is_open:
            return None
        try:
            line = self.serial.readline()
            if not line:
                return None
            decoded = line.decode("utf-8", errors="ignore").strip()
            if decoded:
                self.last_read = time.time()
                return decoded
            return None
        except (OSError, serial.SerialException):
            self.connected = False
            return None

    def close(self) -> None:
        if self.serial is not None and self.serial.is_open:
            self.serial.close()
        self.connected = False


class GaitBuffer:
    def __init__(self, max_samples: int = 500) -> None:
        self.max_samples = max_samples
        self.timestamps: Deque[float] = deque(maxlen=max_samples)
        self.knee_angles: Deque[float] = deque(maxlen=max_samples)
        self.magnitudes: Deque[float] = deque(maxlen=max_samples)
        self.step_times: Deque[float] = deque(maxlen=100)
        self.last_peak_time = 0.0

    def add_sample(self, timestamp: float, knee_angle: float, magnitude: float) -> None:
        self.timestamps.append(timestamp)
        self.knee_angles.append(knee_angle)
        self.magnitudes.append(magnitude)

    def detect_step(self, current_time: float) -> bool:
        if len(self.magnitudes) < 5:
            return False
        mags = list(self.magnitudes)
        threshold = max(1.0, np.mean(mags) + 0.3 * np.std(mags))
        current_mag = mags[-1]
        previous_mag = mags[-2]
        two_back = mags[-3] if len(mags) >= 3 else previous_mag

        if current_mag > previous_mag and current_mag > threshold and current_mag > two_back:
            elapsed = current_time - self.last_peak_time
            if elapsed > 0.25:
                self.last_peak_time = current_time
                self.step_times.append(current_time)
                return True
        return False

    def step_time_stats(self) -> dict[str, float]:
        if len(self.step_times) < 2:
            return {"stride_time": 0.0, "cadence": 0.0, "step_time_std": 0.0}

        diffs = np.diff(np.array(list(self.step_times), dtype=float))
        if len(diffs) == 0:
            return {"stride_time": 0.0, "cadence": 0.0, "step_time_std": 0.0}

        step_interval = float(np.mean(diffs))
        stride_time = max(0.5, 2.0 * step_interval)
        cadence = 60.0 / max(step_interval, 0.25)
        step_std = float(np.std(diffs))
        return {"stride_time": stride_time, "cadence": cadence, "step_time_std": step_std}

    def extract_features(self) -> dict[str, float]:
        if len(self.timestamps) < 20:
            raise ValueError("Insufficient buffer data for feature extraction")

        knee_values = np.array(list(self.knee_angles), dtype=float)
        if len(knee_values) == 0:
            raise ValueError("Knee angle buffer empty")

        knee_rom = float(np.max(knee_values) - np.min(knee_values))
        stats = self.step_time_stats()
        stride_time = stats["stride_time"]
        cadence = stats["cadence"]
        step_time_std = stats["step_time_std"]

        if stride_time <= 0:
            stride_time = 1.0
        if cadence <= 0:
            cadence = 100.0

        stride_length = 0.65 + (cadence * 0.008)
        gait_speed = stride_length / max(stride_time, 0.5)

        features = {
            "gait_speed": float(np.clip(gait_speed, 0.5, 2.5)),
            "stride_time": float(np.clip(stride_time, 0.5, 2.5)),
            "stride_length": float(np.clip(stride_length, 0.7, 2.5)),
            "cadence": float(np.clip(cadence, 50.0, 170.0)),
            "knee_rom": float(np.clip(knee_rom, 5.0, 120.0)),
            "step_time_std": float(np.clip(step_time_std, 0.0, 0.5)),
        }
        return features


def parse_csv_line(line: str) -> tuple[float, float, float, float, float, float, float, float, float, float, float, float] | None:
    try:
        values = [float(value.strip()) for value in line.split(",") if value.strip()]
    except ValueError:
        return None

    if len(values) != 12:
        return None
    return tuple(values)


def run_prediction_window(model: Any, scaler: Any, buffer: GaitBuffer, logger: logging.Logger) -> dict[str, Any] | None:
    try:
        features = buffer.extract_features()
    except ValueError as exc:
        logger.warning("Skipping prediction: %s", exc)
        return None

    row = pd.DataFrame([features], columns=FEATURE_NAMES)
    scaled = scaler.transform(row)
    prediction = int(model.predict(scaled)[0])
    probas = model.predict_proba(scaled)[0]
    confidence = float(np.max(probas) * 100.0)
    label = RISK_LABELS.get(prediction, "Low")

    payload = {
        "timestamp": utc_now_iso(),
        "features": {key: float(value) for key, value in features.items()},
        "prediction": {
            "predicted_class": prediction,
            "label": label,
            "confidence": round(confidence, 2),
        },
        "confidence": round(confidence, 2),
    }

    save_latest_prediction(payload)
    append_prediction_csv(payload)
    logger.info(
        "Prediction: class=%s label=%s confidence=%.2f%% features=%s",
        prediction,
        label,
        confidence,
        json.dumps(features, sort_keys=True),
    )
    return payload


def colorize(label: str, value: str) -> str:
    colors = {
        "Low": "\033[92m",
        "Moderate": "\033[93m",
        "High": "\033[91m",
        "info": "\033[96m",
        "reset": "\033[0m",
    }
    return f"{colors.get(label, colors['info'])}{value}{colors['reset']}"


def print_live_status(buffer: GaitBuffer, payload: dict[str, Any] | None = None) -> None:
    if len(buffer.knee_angles) == 0:
        return
    knee_value = float(np.mean(list(buffer.knee_angles)[-20:])) if len(buffer.knee_angles) >= 20 else float(np.mean(buffer.knee_angles))
    step_count = len(buffer.step_times)
    print(f"\nKnee angle: {knee_value:.2f}° | Steps: {step_count} | Buffer: {len(buffer.timestamps)}")

    if payload is not None:
        label = payload["prediction"]["label"]
        confidence = payload["prediction"]["confidence"]
        print(colorize(label, f"Prediction: {label} risk | Confidence: {confidence:.2f}%"))
        for key, value in payload["features"].items():
            print(f"  {key}: {value:.3f}")


def main() -> None:
    args = parse_args()
    logger = setup_logging()
    ensure_directories()
    print("⚠️ For screening only, not medical diagnosis.")

    try:
        model, scaler = load_ml_artifacts()
    except FileNotFoundError as exc:
        logger.exception("Model loading failed: %s", exc)
        print(f"\nERROR: {exc}\n")
        raise SystemExit(1)

    port = detect_port(args.port)
    if not port:
        logger.error("No ESP32 serial port detected. Tried COM3-COM10 and USB serial enumeration.")
        raise SystemExit("ESP32 not detected. Please specify --port COMx")

    logger.info("Detected serial port: %s", port)
    stream = ESP32Stream(port=port, baudrate=args.baud, timeout=1.0)
    buffer = GaitBuffer(max_samples=args.buffer_size)
    last_prediction_time = 0.0

    try:
        stream.connect()
        logger.info("Connected to ESP32 on %s at %s baud", port, args.baud)

        while True:
            try:
                line = stream.read_line()
                if line is None:
                    if time.time() - stream.last_read > 3:
                        logger.warning("No data received from ESP32 for 3 seconds; reconnecting...")
                        stream.reconnect()
                    time.sleep(0.1)
                    continue

                parsed = parse_csv_line(line)
                if parsed is None:
                    logger.warning("Invalid CSV frame ignored: %s", line)
                    continue

                ax1, ay1, az1, gx1, gy1, gz1, ax2, ay2, az2, gx2, gy2, gz2 = parsed
                accel1_angle = compute_accel_angle(ax1, ay1, az1)
                accel2_angle = compute_accel_angle(ax2, ay2, az2)

                if not hasattr(buffer, "prev_thigh_angle"):
                    buffer.prev_thigh_angle = accel1_angle
                    buffer.prev_leg_angle = accel2_angle
                dt_s = 1.0 / 50.0
                thigh_gyro = gy1
                leg_gyro = gy2

                thigh_angle = complementary_filter(buffer.prev_thigh_angle, thigh_gyro, accel1_angle, dt_s)
                leg_angle = complementary_filter(buffer.prev_leg_angle, leg_gyro, accel2_angle, dt_s)
                knee_angle = thigh_angle - leg_angle

                buffer.prev_thigh_angle = thigh_angle
                buffer.prev_leg_angle = leg_angle

                magnitude = math.sqrt(ax1 * ax1 + ay1 * ay1 + az1 * az1 + ax2 * ax2 + ay2 * ay2 + az2 * az2)
                timestamp = time.time()
                buffer.add_sample(timestamp, knee_angle, magnitude)
                if buffer.detect_step(timestamp):
                    logger.info("Step detected at %.3f s | knee=%0.2f°", timestamp, knee_angle)

                now = time.time()
                if now - last_prediction_time >= args.window:
                    last_prediction_time = now
                    result = run_prediction_window(model, scaler, buffer, logger)
                    if result is not None:
                        print_live_status(buffer, result)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, exiting gracefully.")
                print("\nStopping ESP32 integration...")
                raise
            except Exception as exc:  # pragma: no cover
                logger.exception("Unhandled serial processing error: %s", exc)
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nGraceful exit requested.")
        logger.info("Graceful shutdown complete.")
    finally:
        if stream is not None:
            stream.close()
        logger.info("Serial connection closed.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nForced shutdown.")
    except Exception as exc:
        logger = setup_logging()
        logger.exception("Fatal error: %s", exc)
        raise
