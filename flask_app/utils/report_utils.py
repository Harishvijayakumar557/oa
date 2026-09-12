from __future__ import annotations

from report_generator import build_report_bytes


def generate_pdf_report(patient_data: dict, prediction: dict, language: str = "en") -> bytes:
    """Generate a report PDF using the project report helper."""
    return build_report_bytes(patient_data, prediction, language=language)
