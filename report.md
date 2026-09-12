# COREX OA Screening System Project Report

## 1. Project Overview

COREX is an AI-assisted osteoarthritis (OA) screening system designed to support early gait-based risk assessment using a structured clinical workflow. The platform integrates patient intake, six gait-related measurements, machine learning inference, live or demo screening modes, database persistence, and report generation into a unified Flask application. The system is intended for screening support and monitoring rather than diagnosis, and it is designed to help clinicians or researchers evaluate risk trends in a fast, transparent, and repeatable way.

---

## 2. File Structure and Purpose

### Root project folders

- `README.md` — project overview, setup instructions, and usage notes.
- `requirements.txt` — Python dependencies for ML, Flask, database, report generation, and sensor integration.
- `run_system.py` — top-level launcher for the application workflow.
- `data/` — raw and processed datasets used for model input, testing, and demo flows.
- `docs/` — architecture, user guidance, and project documentation.
- `src/` — training, evaluation, feature-engineering, and synthetic data generation scripts.
- `models/` — serialized model and scaler artifacts used for prediction.
- `flask_app/` — main application package containing the web app, routes, template, static assets, DB models, and report logic.
- `dashboard/` — alternate dashboard/front-end assets and supporting components.
- `esp32_firmware/` — firmware for sensor-based acquisition targets.
- `tests/` — validation and regression checks for the project logic.

### Core application structure

#### `flask_app/`

- `app.py` — Flask app factory and application bootstrap.
- `models_loader.py` — central ML feature contract and validation logic using the six OA screening features.
- `report_generator.py` — PDF report generation and QR-based verification output.
- `translations.py` — multi-language text mapping for UI strings.
- `data/` — local runtime data or JSON outputs for live/demo workflow.
- `models/` — SQLAlchemy models for patient data, screening records, and report metadata.
- `routes/` — API and page routes for dashboard, prediction, live data, and reports.
- `static/` — CSS, JavaScript, and frontend assets.
- `templates/` — Flask Jinja templates for patient registration, dashboard, history, report display, and analysis screens.
- `utils/` — helper functions for feature and report support.

### Supporting project folders

#### `src/`

- `01_generate_synthetic.py` — synthetic gait data generation.
- `02_train_model.py` — model training pipeline.
- `03_evaluate_model.py` — evaluation and performance checks.
- `05_esp32_integration.py` — ESP32 serial integration workflow.
- `06_full_system_test.py` — end-to-end system validation.
- `07_generate_sample_patient.py` — example patient generation.
- `feature_engineering.py` — gait feature calculation logic.
- `train_model.py` — reusable model training implementation.
- `evaluate_model.py` — evaluation logic.
- `data_generation.py` — synthetic dataset generation utilities.
- `utils.py` — general project helper functions.

#### `data/`

- `latest_esp32.json` — live or most recent sensor output.
- `synthetic_gait.csv` — synthetic gait training data.
- `processed/` — cleaned or processed dataset outputs.
- `raw/` — original raw data, if used in analysis workflows.

#### `docs/`

- `project_overview.md` — conceptual system outline.
- `SYSTEM_ARCHITECTURE.md` — technical architecture documentation.
- `USER_GUIDE.md` — operational guidance for users.
- `evaluation_report.txt` — performance and assessment notes.

#### `esp32_firmware/`

- `oa_screening_firmware.ino` — firmware for reading sensor data and preparing motion features for the application.

#### `dashboard/`

- `app.py` — dashboard entry point.
- `live_view.py` — real-time monitoring display.
- `report_generator.py` — report support for dashboard workflows.
- `translations.py` — text translations for dashboard components.
- `assets/style.css` — dashboard styling.

---

## 3. Components Built

### Machine Learning (ML)

- A gait-based screening model is trained using a fixed feature contract.
- The model expects exactly six gait/movement measurements:
  - Gait Speed
  - Stride Time
  - Stride Length
  - Cadence
  - Knee ROM
  - Step Time Std
- Feature validation and normal-range analysis are handled centrally in `flask_app/models_loader.py`.
- Risk prediction is performed through the Flask prediction API and stored with the patient record.

### ESP32 / Sensor Integration

- ESP32 firmware and sensor acquisition support are included to capture motion signals and convert them into gait descriptors.
- Real-time or demo sensor-modes help the user test the screening flow without hardware.
- The app supports a live mode that can ingest data and sync values into the screening interface.

### Flask Web Application

- The platform uses Flask for routing, dashboard views, patient registration, prediction API, and report access.
- The app includes patient intake, history pages, analysis workflows, and report display pages.
- It follows a modular blueprint-based structure to separate dashboard, prediction, live data, and reporting functions.

### Database Layer

- SQLAlchemy models are used to persist patient and screening records.
- The database stores patient information, screening session metadata, risk output, confidence values, and six-feature measurements.
- History pages show prior screening results and related patient information.

### Reporting Module

- Report generation creates a structured PDF-like screening output that includes patient information, feature findings, risk assessment, recommendations, and disclaimer wording.
- The system also generates a verification QR code and stores the report context with the screening session.

---

## 4. Features Working

- Patient registration and screening intake workflow
- Dashboard navigation and analysis page flow
- LIVE mode and DEMO mode support
- Six-feature validation and feature-normal analysis
- Risk prediction endpoint and result generation
- Database persistence for patient records and screening sessions
- Screening history display and patient report linkage
- PDF report generation with disclaimer and clinical context
- Non-diagnostic screening messaging for safer interpretation

---

## 5. Features Pending / Future Work

- Full hardware validation with real ESP32 + MPU sensors in a live clinical or lab setting
- Calibration against larger clinical datasets with clinically verified labels
- Formal model audit and bias review before external deployment
- More robust multilingual translation coverage across all UI sections
- Advanced clinician review workflow, secure authentication, and role-based access
- Deployment packaging for cloud, local server, or institutional use
- Additional reporting enhancements for longitudinal comparison across multiple screenings

---

## 6. Tech Stack

- Python 3.x
- Flask
- Flask-SQLAlchemy
- SQLAlchemy models and SQLite data storage
- scikit-learn
- joblib
- pandas / numpy
- matplotlib / seaborn
- reportlab
- qrcode
- Pillow
- pyserial
- ESP32 firmware workflow
- Jinja2 templates and CSS/JavaScript frontend assets

---

## 7. Reference

Boekesteijn, R. J., et al. (2022). Gait and Posture. "[Insert article title or relevant OA gait screening study here if available in your project documentation]." The project follows the general research direction of gait analysis-based assessment of mobility and movement abnormalities associated with osteoarthritis risk and functional decline.

> Note: If a specific paper title, DOI, or citation is required for formal submission, the exact reference should be confirmed and formatted according to the target journal or institutional standard.

---

## 8. Disclaimer

This COREX OA Screening System is intended for early screening and risk assessment only. It is not a medical diagnosis, it does not replace professional clinical evaluation, and it should not be used as the sole basis for treatment decisions. Any abnormal result should be reviewed by a qualified healthcare professional.

---

## 9. Summary

COREX demonstrates a complete screening pipeline that combines gait analysis, ML prediction, database storage, and report generation into one workflow. It is well-suited as a research prototype or clinical decision-support tool for early OA risk screening, while keeping the system clearly separated from diagnostic decision-making.
