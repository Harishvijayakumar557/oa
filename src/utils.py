from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODEL_DIR = PROJECT_ROOT / "models"


def ensure_directories() -> None:
    for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, MODEL_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
