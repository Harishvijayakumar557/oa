from flask_app.models.patient import Patient
from flask_app.models_loader import FEATURE_NAMES


def test_patient_has_corex_registration_fields():
    fields = {column.name for column in Patient.__table__.columns}
    required = {
        "state",
        "district",
        "village_town",
        "occupation",
        "screening_date",
        "screening_mode",
        "knee_pain",
        "walking_difficulty",
        "stair_climbing_difficulty",
        "stiffness_after_rest",
        "chair_standing_difficulty",
        "reduced_knee_movement",
        "symptom_duration",
    }
    assert required.issubset(fields)


def test_model_feature_contract():
    expected = [
        "gait_speed",
        "stride_time",
        "stride_length",
        "cadence",
        "knee_rom",
        "step_time_std",
    ]
    assert FEATURE_NAMES == expected
