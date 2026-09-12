from __future__ import annotations

from datetime import datetime

from .database import db


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    screening_id = db.Column(db.Integer, db.ForeignKey("screenings.id"), nullable=False, unique=True)
    report_id = db.Column(db.String(80), unique=True, nullable=False)
    pdf_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    screening = db.relationship("Screening", back_populates="report")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "screening_id": self.screening_id,
            "report_id": self.report_id,
            "pdf_path": self.pdf_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
