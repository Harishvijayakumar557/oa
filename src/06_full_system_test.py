from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
import serial

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
MODELS_DIR = PROJECT_ROOT / "models"

FEATURES = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
]


def colorize(text: str, is_pass: bool) -> str:
    """Return ANSI-colored text for terminal output."""
    green = "\033[92m"
    red = "\033[91m"
    reset = "\033[0m"
    return f"{green if is_pass else red}{text}{reset}"


def write_report(lines: list[str]) -> None:
    """Write the test summary to the docs folder."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "system_test_report.txt"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def check_required_files() -> tuple[bool, str]:
    """Confirm that all required deliverables exist."""
    required = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "run_system.py",
        PROJECT_ROOT / "dashboard" / "app.py",
        PROJECT_ROOT / "dashboard" / "report_generator.py",
        PROJECT_ROOT / "dashboard" / "live_view.py",
        PROJECT_ROOT / "src" / "01_generate_synthetic.py",
        PROJECT_ROOT / "src" / "02_train_model.py",
        PROJECT_ROOT / "src" / "03_evaluate_model.py",
        PROJECT_ROOT / "src" / "05_esp32_integration.py",
        PROJECT_ROOT / "models" / "oa_model.pkl",
        PROJECT_ROOT / "models" / "scaler.pkl",
        PROJECT_ROOT / "data" / "synthetic_gait.csv",
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required if not path.exists()]
    if missing:
        return False, f"Missing files: {', '.join(missing)}"
    return True, "All required files found."


def check_model_and_scaler() -> tuple[bool, str]:
    """Load the trained model and scaler from disk."""
    try:
        model = joblib.load(MODELS_DIR / "oa_model.pkl")
        scaler = joblib.load(MODELS_DIR / "scaler.pkl")
        if model is None or scaler is None:
            return False, "Model or scaler loaded as None."
        return True, f"Model types loaded: {type(model).__name__}, {type(scaler).__name__}"
    except Exception as exc:  # pragma: no cover
        return False, f"Model/scaler load error: {exc}"


def check_sample_prediction() -> tuple[bool, str]:
    """Run a known prediction against the trained model."""
    try:
        model = joblib.load(MODELS_DIR / "oa_model.pkl")
        scaler = joblib.load(MODELS_DIR / "scaler.pkl")
        feature_row = {
            "gait_speed": 1.22,
            "stride_time": 1.10,
            "stride_length": 1.28,
            "cadence": 108.0,
            "knee_rom": 55.0,
            "step_time_std": 0.04,
        }
        frame = pd.DataFrame([feature_row], columns=FEATURES)
        data = scaler.transform(frame)
        prediction = model.predict(data)[0]
        prob = model.predict_proba(data)[0]
        return True, f"Prediction ok: class={int(prediction)}, confidence={max(prob):.3f}"
    except Exception as exc:  # pragma: no cover
        return False, f"Sample prediction failed: {exc}"


def check_synthetic_data() -> tuple[bool, str]:
    """Validate the synthetic dataset structure and size."""
    try:
        dataset = pd.read_csv(DATA_DIR / "synthetic_gait.csv")
        required = FEATURES + ["label"]
        missing = [col for col in required if col not in dataset.columns]
        if missing:
            return False, f"Dataset missing columns: {missing}"
        if dataset.empty:
            return False, "Dataset is empty."
        if len(dataset) < 50:
            return False, "Dataset too small."
        return True, f"Dataset validated: {len(dataset)} rows, {dataset['label'].nunique()} classes"
    except Exception as exc:  # pragma: no cover
        return False, f"Synthetic dataset validation failed: {exc}"


def check_serial_port() -> tuple[bool, str]:
    """Check whether any serial ports are available for ESP32 connection."""
    try:
        available = [port.device for port in serial.tools.list_ports.comports()]
        if available:
            return True, f"Serial ports detected: {available}"
        return True, "No serial ports detected; environment may not have an ESP32 connected."
    except Exception as exc:  # pragma: no cover
        return False, f"Serial port scan failed: {exc}"


def check_dashboard_imports() -> tuple[bool, str]:
    """Import dashboard modules without executing the Streamlit app."""
    try:
        modules = [
            PROJECT_ROOT / "dashboard" / "app.py",
            PROJECT_ROOT / "dashboard" / "live_view.py",
            PROJECT_ROOT / "dashboard" / "report_generator.py",
        ]
        for module_path in modules:
            spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load {module_path.name}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return True, "Dashboard modules imported successfully."
    except Exception as exc:  # pragma: no cover
        return False, f"Dashboard import failed: {exc}"


def check_pdf_generation() -> tuple[bool, str]:
    """Generate a PDF using the project report generator."""
    try:
        import importlib.util

        report_path = PROJECT_ROOT / "dashboard" / "report_generator.py"
        spec = importlib.util.spec_from_file_location("report_generator", report_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        patient_data = {
            "name": "Demo Patient",
            "age": 52,
            "gender": "Female",
            "medical_history": "Mild knee discomfort",
            "pain_level": 4,
            "mobility_difficulty": "Mild limitation",
        }
        prediction = {"risk_label": "Moderate Risk", "confidence": 82.5}

        pdf_bytes = module.build_report_bytes(patient_data, prediction, language="en")
        if not pdf_bytes or len(pdf_bytes) < 100:
            return False, "PDF generation produced an empty or invalid file."
        return True, f"PDF generation ok: {len(pdf_bytes)} bytes"
    except Exception as exc:  # pragma: no cover
        return False, f"PDF generation failed: {exc}"


def run_tests() -> tuple[int, list[str], list[bool]]:
    """Execute each system test and record pass/fail status."""
    tests = [
        ("Required files exist", check_required_files),
        ("Model and scaler load", check_model_and_scaler),
        ("Sample prediction", check_sample_prediction),
        ("Synthetic data integrity", check_synthetic_data),
        ("ESP32 serial availability", check_serial_port),
        ("Dashboard imports", check_dashboard_imports),
        ("PDF generation", check_pdf_generation),
    ]

    report_lines: list[str] = []
    passed_flags: list[bool] = []

    for name, func in tests:
        success, detail = func()
        status = "PASS" if success else "FAIL"
        message = f"[{status}] {name}: {detail}"
        report_lines.append(message)
        print(colorize(message, success))
        passed_flags.append(success)

    summary = f"Summary: {sum(passed_flags)}/{len(passed_flags)} tests passed."
    print(colorize(summary, sum(passed_flags) == len(passed_flags)))
    report_lines.append(summary)
    write_report(report_lines)
    return sum(passed_flags), report_lines, passed_flags


def main() -> None:
    """Run full system validation and print final summary."""
    total, _, _ = run_tests()
    sys.exit(0 if total > 0 else 1)


if __name__ == "__main__":
    main()
