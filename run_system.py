from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def colorize(text: str, color: str = "cyan") -> str:
    """Return ANSI-colored text for better terminal readability."""
    palette = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
    }
    return f"{palette.get(color, palette['cyan'])}{text}{palette['reset']}"


def print_header() -> None:
    """Print the system banner."""
    print(colorize("\nOA Screening System Launcher", "green"))
    print(colorize("⚠️ For screening only, not medical diagnosis.", "yellow"))


def ensure_dependencies() -> bool:
    """Check whether the project dependencies are available."""
    required = ["numpy", "pandas", "sklearn", "streamlit", "joblib", "reportlab", "serial", "qrcode", "PIL"]
    missing = []
    for package in required:
        try:
            __import__(package)
        except Exception:
            missing.append(package)

    if missing:
        print(colorize(f"Missing dependencies: {', '.join(missing)}", "red"))
        print("Install using: python -m pip install -r requirements.txt")
        return False
    return True


def run_command(command: list[str]) -> int:
    """Execute a shell command and return the code."""
    print(colorize(f"Running: {' '.join(command)}", "cyan"))
    try:
        result = subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)
        return result.returncode
    except KeyboardInterrupt:
        print(colorize("Interrupted by user.", "yellow"))
        return 1


def train_model() -> int:
    """Train the OA model using the synthetic dataset."""
    if not (PROJECT_ROOT / "data" / "synthetic_gait.csv").exists():
        print(colorize("Synthetic dataset missing. Generating it first...", "yellow"))
        code = run_command([sys.executable, "src/01_generate_synthetic.py"])
        if code != 0:
            return code
    return run_command([sys.executable, "src/02_train_model.py"])


def full_system_test() -> int:
    """Run the full end-to-end test script."""
    return run_command([sys.executable, "src/06_full_system_test.py"])


def launch_dashboard() -> int:
    """Launch the main Streamlit dashboard."""
    if not (PROJECT_ROOT / "models" / "oa_model.pkl").exists():
        print(colorize("Model not found. Training the model first...", "yellow"))
        code = train_model()
        if code != 0:
            return code
    return run_command([sys.executable, "-m", "streamlit", "run", "dashboard/app.py"])


def run_esp32() -> int:
    """Run the real-time ESP32 integration script."""
    if not (PROJECT_ROOT / "models" / "oa_model.pkl").exists():
        print(colorize("Model not found. Training the model first...", "yellow"))
        code = train_model()
        if code != 0:
            return code
    return run_command([sys.executable, "src/05_esp32_integration.py"])


def main() -> None:
    """Display the launcher menu and handle user-selected actions."""
    print_header()
    if not ensure_dependencies():
        raise SystemExit(1)

    while True:
        print("\nChoose an option:")
        print("1. Train model")
        print("2. Run full system test")
        print("3. Launch dashboard")
        print("4. Run ESP32 integration")
        print("5. Exit")

        choice = input("Enter selection (1-5): ").strip()

        if choice == "1":
            code = train_model()
            if code == 0:
                print(colorize("Model training completed.", "green"))
        elif choice == "2":
            code = full_system_test()
            if code == 0:
                print(colorize("Full system test passed.", "green"))
        elif choice == "3":
            code = launch_dashboard()
            if code != 0:
                print(colorize("Dashboard launch failed or was interrupted.", "red"))
        elif choice == "4":
            code = run_esp32()
            if code != 0:
                print(colorize("ESP32 integration exited with an error.", "red"))
        elif choice == "5":
            print(colorize("Exiting OA Screening System launcher.", "yellow"))
            break
        else:
            print(colorize("Invalid option. Please choose 1 - 5.", "red"))


if __name__ == "__main__":
    main()
