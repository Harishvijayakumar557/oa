# COREX — AI-Assisted Osteoarthritis (OA) Screening System

**Complete Project Report**

**Domain:** ECE Final Year Project
**Stack:** Flask + Machine Learning + ESP32 IoT
**Version:** 1.0
**Last Updated:** September 2026

---

## 1. Project Overview

COREX is a low-cost, AI-assisted Osteoarthritis (OA) risk screening platform that combines wearable IMU sensors (ESP32 + dual MPU6050) with a trained machine learning classifier to detect early gait abnormalities associated with knee osteoarthritis.

The system is designed for community health screening camps in Northeast India, where access to specialist orthopedic care is limited. It is explicitly framed as a **screening and monitoring tool**, not a diagnostic instrument.

> **Disclaimer:** COREX supports risk screening only. It does not diagnose osteoarthritis and does not replace evaluation by a qualified healthcare professional.

---

## 2. Key Features

| Feature | Description |
|---|---|
| **Live IMU streaming** | ESP32 + dual MPU6050 sensors stream 12 values (6-axis × 2 IMUs) over Wi-Fi at 50 Hz |
| **Real-time gait analysis** | Complementary filter for knee angle, peak detection for step counting |
| **6 gait features extracted** | Gait Speed, Stride Time, Stride Length, Cadence, Knee ROM, Step Time Std |
| **ML risk prediction** | XGBoost classifier — 3 risk classes (Low / Moderate / High) |
| **20-second live test mode** | Averages live features over 20s for stable prediction |
| **DEMO mode** | Manual feature entry for testing without hardware |
| **Automated PDF reports** | Clinical-style report generated with ReportLab + QR code |
| **Multilingual UI** | English / Tamil / Hindi (3 languages with 229 translation keys) |
| **Patient history** | All screenings stored and searchable |
| **Dashboard analytics** | KPI cards, recent screenings, risk distribution, weekly trend |

---

## 3. Technology Stack

### Backend
- **Python 3.13**
- **Flask 3.1** — web framework
- **Flask-SQLAlchemy 3.1** — ORM
- **SQLite** — database (`data/oa_screening.db`)
- **ReportLab 4.5** — PDF generation
- **qrcode 8.2** — QR code for reports

### Machine Learning
- **scikit-learn 1.9** — RandomForest, SVM
- **XGBoost 2.1** — final selected model
- **pandas 2.3** — data handling
- **numpy 2.1** — numerical ops
- **joblib 1.6** — model persistence

### Frontend
- **Jinja2** templates (7 pages)
- **Bootstrap 5.3** — UI framework
- **Chart.js** — dashboard charts
- **Vanilla JS** — i18n, live polling, form handling

### IoT Hardware
- **ESP32** microcontroller
- **2× MPU6050** IMU sensors (thigh + calf)
- **Wi-Fi (HTTP POST)** — data transmission
- **Arduino IDE** — firmware development

---

## 4. System Architecture

```
┌──────────────────┐
│  MPU6050 (Thigh) │──┐
└──────────────────┘  │
                       ├──► ESP32 ──(Wi-Fi POST)──► Flask Server
┌──────────────────┐  │                              │
│  MPU6050 (Calf)  │──┘                              ▼
└──────────────────┘                          ┌──────────────┐
                                              │ Feature      │
                                              │ Extraction   │
                                              └──────┬───────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │ XGBoost      │
                                              │ Classifier   │
                                              └──────┬───────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │ Risk Class + │
                                              │ PDF Report   │
                                              └──────────────┘
```

### Data Flow
1. ESP32 reads 2× MPU6050 at 50 Hz (12 values per packet)
2. Streams over Wi-Fi to `/api/esp32/stream` (HTTP POST)
3. `RealTimeGaitProcessor` computes knee angle (complementary filter), detects steps (peak detection)
4. Browser polls `/api/live-data` every 280 ms
5. User clicks "Analyze Risk" — 20s collection, features averaged
6. POST to `/api/predict` — XGBoost returns risk class + confidence
7. Screening saved to DB, PDF report generated

---

## 5. Machine Learning Pipeline

### Dataset
- **Source:** Synthetic (no clinical dataset access)
- **Size:** 1500 samples (500 per class)
- **Distribution:** Gaussian, literature-consistent value ranges
- **Classes:** Healthy, Moderate, Severe

### Features (6)
| Feature | Unit | Normal Range |
|---|---|---|
| Gait Speed | m/s | 1.20 – 1.40 |
| Stride Time | s | 1.00 – 1.10 |
| Stride Length | m | 1.25 – 1.45 |
| Cadence | steps/min | 110 – 120 |
| Knee ROM | ° | 55 – 65 |
| Step Time Std | s | 0.02 – 0.04 |

### Models Compared
| Model | Accuracy | F1 Score |
|---|---|---|
| RandomForest | 83.67% | 0.837 |
| SVM | 83.67% | 0.837 |
| **XGBoost (selected)** | **85.67%** | **0.8558** |

### Why XGBoost?
- Best accuracy on the test split
- Gradient boosting handles non-linear gait feature interactions
- Robust to outliers and small feature sets
- Feature importance interpretable for clinical discussion

### Feature Justification (Literature)
- **Boekesteijn et al. (2022, Gait & Posture):** gait speed, cadence, stride length are strong OA discriminators
- Knee ROM and step time variability supported by related OA gait literature
- Formulae used: complementary filter + peak detection (standard); stride_length/gait_speed formulas are custom simplified approximations for low-cost IMU screening

---

## 6. Web Application

### Routes
| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Dashboard with KPI cards + charts |
| `/register` | GET/POST | Patient registration form |
| `/analysis` | GET | Live + DEMO test page |
| `/history` | GET | All past screenings |
| `/settings` | GET/POST | Language + preferences |
| `/report/<id>` | GET | Individual screening report |
| `/report/<id>/pdf` | GET | PDF download |
| `/api/dashboard` | GET | Dashboard JSON |
| `/api/predict` | POST | ML prediction |
| `/api/esp32/stream` | POST | ESP32 data ingestion |
| `/api/live-data` | GET | Live telemetry (polled) |
| `/api/translations/<lang>` | GET | Translation dict |
| `/health` | GET | Health check |

### Templates (7)
1. `base.html` — layout (nav, sidebar, footer, language selector)
2. `index.html` — dashboard
3. `register.html` — patient form
4. `analysis.html` — live + demo test
5. `history.html` — screening history table
6. `report.html` — full clinical report
7. `settings.html` — preferences

### i18n
- **3 languages:** English (en), Tamil (ta), Hindi (hi)
- **229 translation keys**
- Nav dropdown + Settings dropdown
- `?lang=xx` query param → `before_request` hook → session
- Technical/clinical terms (Gait Speed, Knee ROM, IMU, MPU6050, COREX, ESP32) remain in English

---

## 7. IoT Hardware

### ESP32 Firmware (`esp32_firmware/oa_screening_firmware.ino`)
- Reads 2× MPU6050 via I2C
- 50 Hz sampling (20 ms interval)
- Sends 12 values per packet via Wi-Fi HTTP POST:
  `ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2`
- Accel in g (raw / 16384), Gyro in °/s (raw / 131)
- Endpoint: `http://<laptop-ip>:5009/api/esp32/stream`

### Sensor Placement
- **IMU 1 (0x68):** Thigh — above knee
- **IMU 2 (0x69):** Calf/Shank — below knee

### Data Processing (Server-side)
- **Knee angle:** Complementary filter (98% gyro + 2% accel)
- **Step detection:** Peak detection on acceleration magnitude
- **Feature extraction:** Rolling window over recent samples

---

## 8. Setup Instructions

### Prerequisites
- Python 3.10+ (tested on 3.13)
- pip
- ESP32 + 2× MPU6050 (for hardware mode)
- Arduino IDE (for firmware flashing)

### Local Setup
```bash
# Clone
git clone <repo-url>
cd oa

# Create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
# source .venv/bin/activate       # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# (Optional) Regenerate dataset + retrain model
python src/01_generate_synthetic.py
python src/02_train_model.py

# Run Flask app
python -m flask_app.app
```

Open `http://127.0.0.1:5000`

### ESP32 Setup
1. Open `esp32_firmware/oa_screening_firmware.ino` in Arduino IDE
2. Update Wi-Fi SSID + password
3. Update `serverIP` to your laptop's IP (find via `ipconfig`)
4. Flash to ESP32
5. Power on — data streams to Flask server

⚠️ **Note:** Laptop IP must be static or DHCP-reserved, else firmware re-flash needed each time the router reassigns.

---

## 9. Results

### Model Performance
- **Accuracy:** 85.67%
- **Macro F1:** 0.8558
- **Weighted F1:** 0.8558
- **5-fold CV Accuracy:** ~0.846 ± 0.012

### Per-class Performance (XGBoost)
| Class | Precision | Recall | F1 |
|---|---|---|---|
| Low | ~0.92 | ~0.94 | ~0.93 |
| Moderate | ~0.75 | ~0.77 | ~0.76 |
| High | ~0.84 | ~0.80 | ~0.82 |

Moderate class is hardest (overlapping gait patterns with Low/High).

### Validation
- All 8 core routes return HTTP 200
- Live + DEMO + history + report + PDF flows tested end-to-end
- 3 languages render correctly on all pages
- PDF generation with ReportLab works across sessions

---

## 10. Limitations

1. **Synthetic training data** — no clinical dataset used; model performance on real patients is unverified
2. **Binary IMU setup only** — no validation against gold-standard motion capture
3. **Custom feature formulas** — stride_length/gait_speed are simplified approximations, not clinically calibrated
4. **No clinical trial** — not tested against radiograph-confirmed OA
5. **Single-language report PDF** — report text is English even when UI is Tamil/Hindi
6. **Dynamic IP** — ESP32 firmware hardcodes server IP; router DHCP changes require re-flash
7. **No user authentication** — anyone with network access can view patient records

---

## 11. Future Work

- Clinical validation with real patient data (radiograph-confirmed OA)
- Calibrate custom feature formulas against motion-capture gold standard
- Static IP / mDNS for ESP32
- Add user authentication + role-based access
- PDF report localization (Tamil / Hindi)
- Mobile app for field workers
- Edge inference (ESP32-TFLite) to remove server dependency
- Expand to other joints (hip, ankle)

---

## 12. Viva Prep — Anticipated Questions

**Q1: Why synthetic data?**
No access to a clinical OA dataset. Gaussian-generated samples use value ranges from published gait literature (Boekesteijn et al. 2022). Future work includes clinical validation.

**Q2: Why 6 features specifically?**
Gait speed, cadence, stride length are literature-confirmed OA discriminators. Knee ROM and step time variability are supported by related OA gait studies. Formula-based extraction is practical for a low-cost IMU prototype.

**Q3: How does the ML model decide at prediction time?**
It does not "compare against 1500 rows." It learned decision rules during training and applies those rules to new data. Training vs inference distinction.

**Q4: Why XGBoost?**
Best test accuracy (85.67%) and F1 (0.8558) among 3 compared algorithms — a data-driven selection, not a preference.

**Q5: Is this medically valid?**
No — it is a screening/monitoring prototype, not a diagnostic device. The disclaimer is present on every report. Clinical validation is future work.

**Q6: How accurate is the knee angle?**
Complementary filter (98% gyro + 2% accel) — standard IMU fusion. Not validated against motion capture, so it is a practical approximation, not clinical-grade.

**Q7: What about Northeast India language support?**
Currently 3 languages (English, Tamil, Hindi). Six NE languages were prototyped but removed pending native-speaker review of clinical terminology. UI-only translation is straightforward; clinical text needs expert validation.

---

## 13. Repository Structure

```
oa/
├── flask_app/              # Main Flask application
│   ├── app.py              # App factory
│   ├── models_loader.py    # ML model loading
│   ├── report_generator.py # PDF generation
│   ├── translations.py     # i18n (en/ta/hi)
│   ├── models/             # SQLAlchemy models
│   ├── routes/             # Blueprints (main, predict, live, report)
│   ├── templates/          # 7 Jinja templates
│   ├── static/             # CSS + JS
│   └── utils/              # Helper functions
├── src/                    # ML pipeline scripts
│   ├── 01_generate_synthetic.py
│   ├── 02_train_model.py
│   ├── 03_evaluate_model.py
│   ├── 05_esp32_integration.py
│   └── 06_full_system_test.py
├── models/                 # Trained .pkl files
├── data/                   # DB + synthetic dataset
├── esp32_firmware/         # Arduino code
├── docs/                   # Evaluation report + figures
├── dashboard/              # Legacy Streamlit UI
├── archive/                # Legacy scripts
└── tests/                  # Test suite
```

---

## 14. References

1. Boekesteijn, R. J., et al. (2022). "Objective gait analysis in knee osteoarthritis: a systematic review." *Gait & Posture*.
2. Chen, T., & Guestrin, C. (2016). "XGBoost: A Scalable Tree Boosting System." *KDD*.
3. World Health Organization. (2023). "Osteoarthritis — Key Facts."
4. MPU6050 Datasheet — InvenSense.
5. ESP32 Technical Reference Manual — Espressif Systems.

---

**End of Report**
