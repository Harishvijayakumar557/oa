from __future__ import annotations

from datetime import datetime

from .database import db


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    address = db.Column(db.Text, nullable=True)
    state = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    village_town = db.Column(db.String(100), nullable=True)
    occupation = db.Column(db.String(100), nullable=True)
    screening_date = db.Column(db.Date, nullable=True)
    screening_mode = db.Column(db.String(20), nullable=True)
    pain_level = db.Column(db.Integer, nullable=True)
    mobility = db.Column(db.String(80), nullable=True)
    medical_history = db.Column(db.Text, nullable=True)
    knee_pain = db.Column(db.String(20), nullable=True)
    walking_difficulty = db.Column(db.String(20), nullable=True)
    stair_climbing_difficulty = db.Column(db.String(20), nullable=True)
    stiffness_after_rest = db.Column(db.String(20), nullable=True)
    chair_standing_difficulty = db.Column(db.String(20), nullable=True)
    reduced_knee_movement = db.Column(db.String(20), nullable=True)
    symptom_duration = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    screenings = db.relationship("Screening", back_populates="patient", cascade="all, delete-orphan")

    @property
    def patient_id(self) -> str:
        return str(self.id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "state": self.state,
            "district": self.district,
            "village_town": self.village_town,
            "occupation": self.occupation,
            "screening_date": self.screening_date.isoformat() if self.screening_date else None,
            "screening_mode": self.screening_mode,
            "pain_level": self.pain_level,
            "mobility": self.mobility,
            "medical_history": self.medical_history,
            "knee_pain": self.knee_pain,
            "walking_difficulty": self.walking_difficulty,
            "stair_climbing_difficulty": self.stair_climbing_difficulty,
            "stiffness_after_rest": self.stiffness_after_rest,
            "chair_standing_difficulty": self.chair_standing_difficulty,
            "reduced_knee_movement": self.reduced_knee_movement,
            "symptom_duration": self.symptom_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
