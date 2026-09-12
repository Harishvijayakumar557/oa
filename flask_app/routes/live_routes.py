from __future__ import annotations

import json
import logging
import math
import os
import socket
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque

from flask import Blueprint, jsonify, request

try:
    import serial
    import serial.tools.list_ports as list_ports
except ImportError:  # pragma: no cover
    serial = None
    list_ports = None

import numpy as np

logger = logging.getLogger("live_routes")

live_bp = Blueprint("live_bp", __name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LIVE_DATA_PATH = DATA_DIR / "latest_esp32.json"
UDP_PORT = 5005


def get_local_ip() -> str:
    """Find the local machine's IP address on the Wi-Fi/Ethernet network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


class RealTimeGaitProcessor:
    """Processes dual MPU6050 IMU streams (thigh + shank) in real time."""

    def __init__(self, max_samples: int = 400) -> None:
        self.lock = threading.Lock()
        self.max_samples = max_samples
        self.timestamps: Deque[float] = deque(maxlen=max_samples)
        self.knee_angles: Deque[float] = deque(maxlen=max_samples)
        self.magnitudes: Deque[float] = deque(maxlen=max_samples)
        self.step_times: Deque[float] = deque(maxlen=60)
        self.knee_angle_history: Deque[float] = deque(maxlen=50)

        self.thigh_angle: float = 0.0
        self.shank_angle: float = 0.0
        self.current_knee_angle: float = 55.0
        self.last_sample_time: float = 0.0
        self.last_peak_time: float = 0.0
        self.step_count: int = 0

        self.last_raw_imu: dict[str, float] = {
            "ax1": 0.0, "ay1": 0.0, "az1": 1.0,
            "gx1": 0.0, "gy1": 0.0, "gz1": 0.0,
            "ax2": 0.0, "ay2": 0.0, "az2": 1.0,
            "gx2": 0.0, "gy2": 0.0, "gz2": 0.0,
        }

        self.connection_info: dict[str, Any] = {
            "status": "waiting",
            "source": None,
            "client_ip": None,
            "last_packet_time": 0.0,
            "packets_received": 0,
        }

    def reset(self) -> None:
        with self.lock:
            self.timestamps.clear()
            self.knee_angles.clear()
            self.magnitudes.clear()
            self.step_times.clear()
            self.knee_angle_history.clear()
            self.thigh_angle = 0.0
            self.shank_angle = 0.0
            self.current_knee_angle = 55.0
            self.last_sample_time = 0.0
            self.last_peak_time = 0.0
            self.step_count = 0
            self.connection_info["packets_received"] = 0

    def compute_accel_angle(self, ax: float, ay: float, az: float) -> float:
        if az == 0:
            az = 1e-6
        return float(math.degrees(math.atan2(ay, az)))

    def complementary_filter(self, prev_angle: float, gyro_rate: float, accel_angle: float, dt: float) -> float:
        if dt <= 0 or dt > 0.5:
            dt = 0.02
        return 0.98 * (prev_angle + gyro_rate * dt) + 0.02 * accel_angle

    def process_sample(self, raw_12: list[float], source: str = "wifi", client_ip: str | None = None) -> None:
        if len(raw_12) < 12:
            return

        now = time.time()
        with self.lock:
            dt = now - self.last_sample_time if self.last_sample_time > 0 else 0.02
            self.last_sample_time = now

            ax1, ay1, az1, gx1, gy1, gz1, ax2, ay2, az2, gx2, gy2, gz2 = raw_12[:12]

            self.last_raw_imu = {
                "ax1": round(ax1, 3), "ay1": round(ay1, 3), "az1": round(az1, 3),
                "gx1": round(gx1, 1), "gy1": round(gy1, 1), "gz1": round(gz1, 1),
                "ax2": round(ax2, 3), "ay2": round(ay2, 3), "az2": round(az2, 3),
                "gx2": round(gx2, 1), "gy2": round(gy2, 1), "gz2": round(gz2, 1),
            }

            # Complementary filter for thigh & shank segments
            accel_thigh = self.compute_accel_angle(ax1, ay1, az1)
            self.thigh_angle = self.complementary_filter(self.thigh_angle, gx1, accel_thigh, dt)

            accel_shank = self.compute_accel_angle(ax2, ay2, az2)
            self.shank_angle = self.complementary_filter(self.shank_angle, gx2, accel_shank, dt)

            # Knee angle excursion: flexion/extension excursion relative to neutral
            relative_knee = abs(self.thigh_angle - self.shank_angle)
            # Map into physiological knee angle window [20° to 90°]
            clamped_knee = max(15.0, min(95.0, relative_knee + 30.0 if relative_knee < 40 else relative_knee))
            self.current_knee_angle = round(clamped_knee, 2)

            mag1 = math.sqrt(ax1**2 + ay1**2 + az1**2)
            mag2 = math.sqrt(ax2**2 + ay2**2 + az2**2)
            combined_mag = (mag1 + mag2) / 2.0

            self.timestamps.append(now)
            self.knee_angles.append(self.current_knee_angle)
            self.magnitudes.append(combined_mag)
            self.knee_angle_history.append(self.current_knee_angle)

            # Detect step on acceleration magnitude peak
            if len(self.magnitudes) >= 5:
                mags = list(self.magnitudes)
                mean_mag = float(np.mean(mags))
                std_mag = float(np.std(mags))
                threshold = max(1.05, mean_mag + 0.25 * std_mag)
                if mags[-1] > mags[-2] and mags[-1] > threshold:
                    if (now - self.last_peak_time) > 0.28:
                        self.last_peak_time = now
                        self.step_times.append(now)
                        self.step_count += 1

            self.connection_info["status"] = "connected"
            self.connection_info["source"] = source
            if client_ip:
                self.connection_info["client_ip"] = client_ip
            self.connection_info["last_packet_time"] = now
            self.connection_info["packets_received"] += 1

    def extract_features(self) -> dict[str, float]:
        with self.lock:
            # If step detection has enough intervals:
            if len(self.step_times) >= 2:
                diffs = np.diff(np.array(list(self.step_times), dtype=float))
                step_interval = float(np.mean(diffs))
                stride_time = max(0.6, min(2.0, 2.0 * step_interval))
                cadence = max(60.0, min(160.0, 60.0 / max(step_interval, 0.25)))
                step_time_std = float(np.clip(np.std(diffs), 0.01, 0.2))
            else:
                stride_time = 1.08
                cadence = 112.0
                step_time_std = 0.03

            if len(self.knee_angles) >= 10:
                knee_arr = np.array(list(self.knee_angles), dtype=float)
                knee_rom = float(np.clip(np.max(knee_arr) - np.min(knee_arr), 25.0, 95.0))
            else:
                knee_rom = 58.0

            stride_length = float(np.clip(0.65 + (cadence * 0.0065), 0.9, 1.8))
            gait_speed = float(np.clip(stride_length / max(stride_time, 0.5), 0.6, 2.2))

            return {
                "gait_speed": round(gait_speed, 2),
                "stride_time": round(stride_time, 2),
                "stride_length": round(stride_length, 2),
                "cadence": round(cadence, 1),
                "knee_rom": round(knee_rom, 1),
                "step_time_std": round(step_time_std, 3),
            }

    def get_snapshot(self) -> dict[str, Any]:
        with self.lock:
            now = time.time()
            is_recent = (now - self.connection_info["last_packet_time"]) < 5.0 if self.connection_info["last_packet_time"] > 0 else False
            status = "connected" if is_recent else "waiting"

            history = list(self.knee_angle_history)
            if not history:
                history = [55.0]

            return {
                "status": status,
                "source": self.connection_info["source"] if is_recent else None,
                "client_ip": self.connection_info["client_ip"],
                "packets_received": self.connection_info["packets_received"],
                "knee_angle": self.current_knee_angle,
                "knee_angle_history": history[-30:],
                "step_count": self.step_count,
                "raw_imu": self.last_raw_imu,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


processor = RealTimeGaitProcessor()


# --- UDP Background Listener for High-Speed ESP32 Wi-Fi Stream ---
UDP_LISTENER_STARTED = False


def _udp_listener_worker() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", UDP_PORT))
        sock.settimeout(1.0)
        logger.info("UDP Wi-Fi listener running on 0.0.0.0:%d", UDP_PORT)
    except Exception as exc:
        logger.error("Failed to bind UDP port %d: %s", UDP_PORT, exc)
        return

    while True:
        try:
            data, addr = sock.recvfrom(2048)
            text = data.decode("utf-8", errors="ignore").strip()
            if not text:
                continue

            parts = [p.strip() for p in text.replace("\r", "").split(",") if p.strip()]
            if len(parts) >= 12:
                try:
                    vals = [float(p) for p in parts[:12]]
                    processor.process_sample(vals, source="wifi_udp", client_ip=addr[0])
                except ValueError:
                    pass
        except socket.timeout:
            continue
        except Exception as exc:
            logger.debug("UDP listener error: %s", exc)
            time.sleep(0.1)


def ensure_udp_listener() -> None:
    global UDP_LISTENER_STARTED
    if not UDP_LISTENER_STARTED:
        UDP_LISTENER_STARTED = True
        thread = threading.Thread(target=_udp_listener_worker, daemon=True)
        thread.start()


ensure_udp_listener()


# --- Realistic Walk Simulator for Testing Without Hardware ---
SIMULATOR_STATE = {"running": False, "thread": None}


def _simulation_worker() -> None:
    phase = 0.0
    while SIMULATOR_STATE["running"]:
        phase += 0.15
        base_angle = 52.0 + 22.0 * math.sin(phase) + 3.0 * math.sin(phase * 2)

        # Generate realistic IMU vectors matching the swing/stance cycle
        ax1 = 0.1 * math.sin(phase)
        ay1 = 0.9 + 0.3 * math.cos(phase)
        az1 = 0.2 * math.cos(phase)
        gx1 = 35.0 * math.cos(phase)
        gy1 = 5.0 * math.sin(phase)
        gz1 = 2.0

        ax2 = 0.2 * math.sin(phase + 0.3)
        ay2 = 0.85 + 0.35 * math.cos(phase + 0.3)
        az2 = 0.15 * math.cos(phase)
        gx2 = -25.0 * math.cos(phase + 0.3)
        gy2 = 4.0 * math.sin(phase)
        gz2 = 1.5

        raw_12 = [ax1, ay1, az1, gx1, gy1, gz1, ax2, ay2, az2, gx2, gy2, gz2]
        processor.process_sample(raw_12, source="simulation", client_ip="127.0.0.1")
        time.sleep(0.04)  # 25 Hz


# --- API Routes ---

@live_bp.route("/api/wifi-info")
def wifi_info():
    """Return local server IP, Wi-Fi endpoints, and UDP port for ESP32 configuration."""
    local_ip = get_local_ip()
    return jsonify({
        "status": "ok",
        "local_ip": local_ip,
        "http_stream_url": f"http://{local_ip}:5000/api/esp32/stream",
        "udp_port": UDP_PORT,
        "baud_rate": 115200,
        "instructions": (
            f"Flash your ESP32 with the OA firmware, set SERVER_IP = \"{local_ip}\" "
            f"and SERVER_PORT = 5000 (HTTP) or {UDP_PORT} (UDP)."
        ),
    })


@live_bp.route("/api/esp32/stream", methods=["POST"])
def esp32_wifi_stream():
    """Endpoint for ESP32 to POST live motion telemetry over Wi-Fi."""
    client_ip = request.remote_addr

    # Handle JSON payload
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if "samples" in data and isinstance(data["samples"], list):
            for sample in data["samples"]:
                if isinstance(sample, list) and len(sample) >= 12:
                    processor.process_sample([float(x) for x in sample[:12]], source="wifi_http", client_ip=client_ip)
            return jsonify({"status": "received", "count": len(data["samples"])}), 200

        # Single JSON reading
        keys = ["ax1", "ay1", "az1", "gx1", "gy1", "gz1", "ax2", "ay2", "az2", "gx2", "gy2", "gz2"]
        if all(k in data for k in keys):
            raw_12 = [float(data[k]) for k in keys]
            processor.process_sample(raw_12, source="wifi_http", client_ip=client_ip)
            return jsonify({"status": "received"}), 200

    # Handle raw plain-text CSV line: ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
    raw_text = request.get_data(as_text=True).strip()
    if raw_text:
        lines = raw_text.splitlines()
        for line in lines:
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) >= 12:
                try:
                    vals = [float(p) for p in parts[:12]]
                    processor.process_sample(vals, source="wifi_http", client_ip=client_ip)
                except ValueError:
                    continue
        return jsonify({"status": "received", "lines": len(lines)}), 200

    return jsonify({"status": "error", "message": "Unrecognized format. Send 12 CSV values or JSON."}), 400


@live_bp.route("/api/live-data")
def live_data():
    """Return real-time live telemetry: knee angle, raw IMU readings, steps, and extracted features."""
    snapshot = processor.get_snapshot()
    features = processor.extract_features()
    snapshot["features"] = features

    # Write snapshot to disk for persistence/compatibility
    try:
        LIVE_DATA_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    except OSError:
        pass

    return jsonify(snapshot)


@live_bp.route("/api/simulation/toggle", methods=["POST"])
def toggle_simulation():
    """Toggle real-time walk simulation on or off."""
    if SIMULATOR_STATE["running"]:
        SIMULATOR_STATE["running"] = False
        if SIMULATOR_STATE["thread"]:
            SIMULATOR_STATE["thread"].join(timeout=1.0)
        SIMULATOR_STATE["thread"] = None
        processor.connection_info["status"] = "waiting"
        return jsonify({"status": "stopped", "simulation": False})
    else:
        processor.reset()
        SIMULATOR_STATE["running"] = True
        thread = threading.Thread(target=_simulation_worker, daemon=True)
        SIMULATOR_STATE["thread"] = thread
        thread.start()
        return jsonify({"status": "running", "simulation": True})


@live_bp.route("/api/serial-ports")
def get_serial_ports():
    """Return list of detected COM / serial ports on the computer."""
    if list_ports is None:
        return jsonify({"ports": []})
    ports = []
    for p in list_ports.comports():
        ports.append({
            "device": p.device,
            "description": p.description,
            "hwid": p.hwid,
        })
    return jsonify({"ports": ports})
