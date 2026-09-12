from __future__ import annotations

from datetime import datetime

from .database import db


class Screening(db.Model):
    __tablename__ = "screenings"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    mode = db.Column(db.String(20), nullable=False, default="LIVE")
    gait_speed = db.Column(db.Float, nullable=False)
    stride_time = db.Column(db.Float, nullable=False)
    stride_length = db.Column(db.Float, nullable=False)
    cadence = db.Column(db.Float, nullable=False)
    knee_rom = db.Column(db.Float, nullable=False)
    step_time_std = db.Column(db.Float, nullable=False)
    risk_class = db.Column(db.Integer, nullable=False)
    risk_label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="screenings")
    report = db.relationship("Report", back_populates="screening", uselist=False, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "mode": self.mode,
            "gait_speed": self.gait_speed,
            "stride_time": self.stride_time,
            "stride_length": self.stride_length,
            "cadence": self.cadence,
            "knee_rom": self.knee_rom,
            "step_time_std": self.step_time_std,
            "risk_class": self.risk_class,
            "risk_label": self.risk_label,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
