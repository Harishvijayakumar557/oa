from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None

live_bp = Blueprint("live_bp", __name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LIVE_DATA_PATH = DATA_DIR / "latest_esp32.json"

ESP32_CONNECTION = {
    "connected": False,
    "port": None,
    "thread": None,
    "serial_handle": None,
    "last_data": None,
}


def _read_env_setting(name: str, default: str) -> str:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if not text or text.startswith("#") or "=" not in text:
                    continue
                key, val = text.split("=", 1)
                if key.strip() == name:
                    return val.strip().strip('"').strip("'")
        except OSError:
            pass
    return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extract_features(raw_values: list[float]) -> dict:
    if len(raw_values) < 12:
        return {
            "gait_speed": 1.2,
            "stride_time": 1.1,
            "stride_length": 1.3,
            "cadence": 110.0,
            "knee_rom": 55.0,
            "step_time_std": 0.04,
        }

    ax1, ay1, az1, gx1, gy1, gz1, ax2, ay2, az2, gx2, gy2, gz2 = raw_values[:12]
    accel_mag_1 = (ax1 ** 2 + ay1 ** 2 + az1 ** 2) ** 0.5
    accel_mag_2 = (ax2 ** 2 + ay2 ** 2 + az2 ** 2) ** 0.5
    gyro_mag = (gx1 ** 2 + gy1 ** 2 + gz1 ** 2 + gx2 ** 2 + gy2 ** 2 + gz2 ** 2) ** 0.5

    gait_speed = 0.8 + ((accel_mag_1 + accel_mag_2) / 18.0)
    gait_speed = _clamp(gait_speed, 0.5, 2.0)

    stride_time = 1.15 - ((accel_mag_1 + accel_mag_2) / 60.0)
    stride_time = _clamp(stride_time, 0.6, 1.8)

    stride_length = 0.9 + (gait_speed / 1.8)
    stride_length = _clamp(stride_length, 0.8, 2.1)

    cadence = (60.0 / max(stride_time, 0.5)) * 1.05
    cadence = _clamp(cadence, 70.0, 170.0)

    knee_rom = 35.0 + (abs(gx1) + abs(gx2)) * 1.8 + (abs(gy1) + abs(gy2)) * 0.2
    knee_rom = _clamp(knee_rom, 20.0, 100.0)

    step_time_std = 0.02 + (gyro_mag / 8000.0)
    step_time_std = _clamp(step_time_std, 0.01, 0.2)

    return {
        "gait_speed": round(gait_speed, 3),
        "stride_time": round(stride_time, 3),
        "stride_length": round(stride_length, 3),
        "cadence": round(cadence, 2),
        "knee_rom": round(knee_rom, 2),
        "step_time_std": round(step_time_std, 4),
    }


def _write_live_data(payload: dict) -> None:
    LIVE_DATA_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_serial_stream(port: str, baud_rate: int = 115200) -> None:
    if serial is None:
        payload = {
            "status": "disconnected",
            "message": "pyserial is not installed.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _write_live_data(payload)
        ESP32_CONNECTION["connected"] = False
        return

    try:
        connection = serial.Serial(port, baudrate=baud_rate, timeout=1.0)
    except Exception as exc:  # pragma: no cover - depends on hardware
        payload = {
            "status": "disconnected",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _write_live_data(payload)
        ESP32_CONNECTION["connected"] = False
        return

    ESP32_CONNECTION["serial_handle"] = connection
    ESP32_CONNECTION["connected"] = True
    ESP32_CONNECTION["port"] = port

    try:
        while ESP32_CONNECTION.get("connected") and connection.is_open:
            try:
                raw_line = connection.readline()
            except Exception:
                break

            if not raw_line:
                time.sleep(0.2)
                continue

            text = raw_line.decode("utf-8", errors="ignore").strip()
            if not text:
                continue

            numbers = []
            for chunk in text.replace("\r", "").replace("\n", " ").split():
                if chunk.count(","):
                    for part in chunk.split(","):
                        part = part.strip()
                        if part:
                            numbers.append(_safe_float(part))
                else:
                    numbers.append(_safe_float(chunk))

            if len(numbers) < 12:
                continue

            features = _extract_features(numbers)
            payload = {
                "status": "connected",
                "features": features,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "port": port,
            }
            ESP32_CONNECTION["last_data"] = payload
            _write_live_data(payload)
            time.sleep(2)
    finally:
        try:
            connection.close()
        except Exception:
            pass
        ESP32_CONNECTION["connected"] = False
        ESP32_CONNECTION["serial_handle"] = None
        _write_live_data({
            "status": "disconnected",
            "message": "ESP32 disconnected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "port": port,
        })


@live_bp.route("/api/connect-esp32", methods=["POST"])
def connect_esp32():
    """Open a serial connection to the ESP32 and start a background reader."""
    if ESP32_CONNECTION.get("connected") and ESP32_CONNECTION.get("serial_handle") is not None:
        return jsonify({"status": "connected", "port": ESP32_CONNECTION.get("port") or _read_env_setting("ESP32_PORT", "COM3")})

    port = _read_env_setting("ESP32_PORT", "COM3")
    baud_rate = int(_read_env_setting("ESP32_BAUD", "115200"))

    try:
        if serial is None:
            raise RuntimeError("pyserial is not installed")

        connection = serial.Serial(port, baudrate=baud_rate, timeout=1.0)
        connection.close()
    except Exception as exc:  # pragma: no cover - hardware-specific
        return jsonify({"status": "error", "message": f"Unable to open serial port {port}: {exc}"}), 500

    ESP32_CONNECTION["connected"] = True
    ESP32_CONNECTION["port"] = port
    ESP32_CONNECTION["thread"] = threading.Thread(target=_read_serial_stream, args=(port, baud_rate), daemon=True)
    ESP32_CONNECTION["thread"].start()

    return jsonify({"status": "connected", "port": port})


@live_bp.route("/api/disconnect-esp32", methods=["POST"])
def disconnect_esp32():
    """Disconnect the ESP32 session and stop the serial reader."""
    ESP32_CONNECTION["connected"] = False
    serial_handle = ESP32_CONNECTION.get("serial_handle")
    if serial_handle is not None:
        try:
            serial_handle.close()
        except Exception:
            pass
    ESP32_CONNECTION["serial_handle"] = None
    ESP32_CONNECTION["thread"] = None
    _write_live_data({
        "status": "disconnected",
        "message": "Disconnected by user",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "port": ESP32_CONNECTION.get("port"),
    })
    return jsonify({"status": "disconnected", "message": "ESP32 disconnected"})


@live_bp.route("/api/live-data")
def live_data():
    """Return the latest live ESP32 status and features."""
    if not LIVE_DATA_PATH.exists():
        return jsonify({"status": "waiting", "message": "Waiting for ESP32 data."})

    try:
        payload = json.loads(LIVE_DATA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return jsonify({"status": "waiting", "message": "Waiting for ESP32 data."})

    status = payload.get("status")
    if status == "connected":
        return jsonify({
            "status": "connected",
            "features": payload.get("features", {}),
            "timestamp": payload.get("timestamp"),
            "port": payload.get("port"),
        })
    if status == "disconnected":
        return jsonify({"status": "disconnected", "message": payload.get("message", "ESP32 disconnected")})
    return jsonify({"status": "waiting", "message": "Waiting for ESP32 data."})
