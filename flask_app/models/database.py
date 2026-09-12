from __future__ import annotations

from pathlib import Path

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "oa_screening.db"

db = SQLAlchemy()
migrate = Migrate()


def _upgrade_schema() -> None:
    """Add missing COREX fields to existing SQLite databases without replacing the app."""
    inspector = db.inspect(db.engine)

    if inspector.has_table("patients"):
        existing = {col["name"] for col in inspector.get_columns("patients")}
        additions = {
            "state": "VARCHAR(100)",
            "district": "VARCHAR(100)",
            "village_town": "VARCHAR(100)",
            "occupation": "VARCHAR(100)",
            "screening_date": "DATE",
            "screening_mode": "VARCHAR(20)",
            "knee_pain": "VARCHAR(20)",
            "walking_difficulty": "VARCHAR(20)",
            "stair_climbing_difficulty": "VARCHAR(20)",
            "stiffness_after_rest": "VARCHAR(20)",
            "chair_standing_difficulty": "VARCHAR(20)",
            "reduced_knee_movement": "VARCHAR(20)",
            "symptom_duration": "VARCHAR(50)",
        }
        for column_name, column_type in additions.items():
            if column_name not in existing:
                db.session.execute(text(f"ALTER TABLE patients ADD COLUMN {column_name} {column_type}"))

    if inspector.has_table("screenings"):
        existing = {col["name"] for col in inspector.get_columns("screenings")}
        if "mode" not in existing:
            db.session.execute(text("ALTER TABLE screenings ADD COLUMN mode VARCHAR(20) DEFAULT 'LIVE'"))

    db.session.commit()


def init_db(app: Flask) -> None:
    """Initialize SQLAlchemy and create database tables if they do not exist."""
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{DB_PATH}")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()
        _upgrade_schema()
