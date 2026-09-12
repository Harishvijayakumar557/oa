# OA Screening System

The OA Screening System is a prototype Python-based gait monitoring pipeline for early screening of osteoarthritis risk using two MPU6050 sensors and a multiclass machine learning model. It combines synthetic data generation, model training, ESP32 serial integration, dashboard visualization, and PDF reporting into a full end-to-end workflow.

## Disclaimer

⚠️ For screening only, not medical diagnosis.

This project is intended for research, prototyping, and educational use in a clinical-support context only. It is not a diagnostic system and must not replace professional medical judgment.

## Project overview

The system follows a 9-stage flow:

1. Data generation
2. Feature validation
3. Model training
4. Evaluation
5. ESP32 sensor acquisition
6. Real-time serial ingestion
7. Live feature extraction
8. Risk prediction
9. Reporting and dashboard review

## System architecture

```text
+---------------------+     +---------------------+     +---------------------+
| 1. Synthetic data   | --> | 2. Feature mining    | --> | 3. Model training   |
| generation          |     | gait metrics        |     | + scaler + model    |
+---------------------+     +---------------------+     +---------------------+
             |                              |                            |
             v                              v                            v
+---------------------+     +---------------------+     +---------------------+
| 4. Evaluation       | --> | 5. ESP32 + MPU6050  | --> | 6. Real-time stream |
| + metrics + plots   |     | sensors             |     | + serial parser     |
+---------------------+     +---------------------+     +---------------------+
             |                              |                            |
             v                              v                            v
+---------------------+     +---------------------+     +---------------------+
| 7. Live feature     | --> | 8. Risk prediction  | --> | 9. Dashboard + PDF  |
| extraction          |     | + confidence        |     | + report export     |
+---------------------+     +---------------------+     +---------------------+
```

## Folder structure

```text
oa/
├── README.md
├── requirements.txt
├── run_system.py
├── .gitignore
├── data/
│   ├── synthetic_gait.csv
│   ├── live_predictions.csv
│   ├── latest_prediction.json
│   └── sample_patients.csv
├── src/
│   ├── 01_generate_synthetic.py
│   ├── 02_train_model.py
│   ├── 03_evaluate_model.py
│   ├── 05_esp32_integration.py
│   ├── 06_full_system_test.py
│   ├── 07_generate_sample_patient.py
│   └── __init__.py
├── dashboard/
│   ├── app.py
│   ├── live_view.py
│   ├── report_generator.py
│   ├── translations.py
│   └── assets/
│       └── style.css
├── esp32_firmware/
│   └── oa_screening_firmware.ino
├── models/
│   ├── oa_model.pkl
│   └── scaler.pkl
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── USER_GUIDE.md
│   └── system_test_report.txt
├── logs/
│   └── esp32_integration.log
└──
```

## Requirements

- Python 3.10+
- pip
- ESP32 with two MPU6050 modules for live hardware use
- Serial access on the host machine

## Installation

1. Clone or open the project folder.
2. Create a virtual environment:

```bash
python -m venv .venv
```

3. Activate it:

- Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

- Linux/macOS:

```bash
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Confirm the environment is ready:

```bash
python --version
```

## Usage

### 1) Train the model

```bash
python src/02_train_model.py
```

### 2) Generate synthetic data

```bash
python src/01_generate_synthetic.py
```

### 3) Run evaluation

```bash
python src/03_evaluate_model.py
```

### 4) Generate sample patients

```bash
python src/07_generate_sample_patient.py
```

### 5) Run full system test

```bash
python src/06_full_system_test.py
```

### 6) Launch the dashboard

```bash
streamlit run dashboard/app.py
```

### 7) Launch the live ESP32 monitor

```bash
python src/05_esp32_integration.py --port COM3
```

### 8) Use the quick launcher

```bash
python run_system.py
```

## ESP32 hardware setup

- Sensor 1: MPU6050 at address 0x68
- Sensor 2: MPU6050 at address 0x69
- Connect SDA to GPIO 21
- Connect SCL to GPIO 22
- Upload firmware from [esp32_firmware/oa_screening_firmware.ino](esp32_firmware/oa_screening_firmware.ino)
- Serial baud rate: 115200

## Feature set used by the model

The trained model expects the following features:

- gait_speed
- stride_time
- stride_length
- cadence
- knee_rom
- step_time_std

## Troubleshooting

### Model file not found

Run:

```bash
python src/02_train_model.py
```

### Serial not detected

- Check physical USB connection
- Verify COM port in Device Manager
- Use the argument `--port COMx`
- Confirm the ESP32 is running the firmware and printing `READY`

### Dashboard not loading

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

### PDF export issues

- Ensure `reportlab` is installed
- Confirm the fonts folder exists if you want non-default fonts
- Check logs for PDF generation errors

### Missing live JSON or data

- Ensure the ESP32 integration script is running
- Verify the JSON file is being written to `data/latest_prediction.json`
- Check `logs/esp32_integration.log`

## Security and professional use notes

- Use the system only with the consent of the patient and under appropriate clinical workflow.
- Do not use the result as a sole basis for diagnosis or treatment.
- Store results securely and in accordance with local clinical data standards.

## Credits and references

This project is a prototype screening framework built for gait analysis, real-time sensor processing, and health technology demonstration. It combines open-source Python scientific libraries and clinic-style reporting patterns.

Key libraries used:

- scikit-learn
- pandas
- NumPy
- seaborn
- matplotlib
- streamlit
- reportlab
- pyserial
- qrcode
- pillow

## Final medical note

⚠️ For screening only, not medical diagnosis.
