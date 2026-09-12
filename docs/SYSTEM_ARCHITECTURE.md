# OA Screening System Architecture

## Overview

The OA Screening System is a modular pipeline for gait-based osteoarthritis screening using synthetic and ESP32-based sensor data. It merges data generation, feature engineering, ML modeling, deployment, and medical reporting into a single research & prototype workflow.

## System flow

```text
+---------------------+      +--------------------+      +---------------------+
| Synthetic Data      | ---> | Feature Extraction | ---> | Model Training      |
| Generation          |      | + gait metrics     |      | + scaler + model    |
+---------------------+      +--------------------+      +---------------------+
             |                                                       |
             v                                                       v
+---------------------+      +--------------------+      +---------------------+
| ESP32 + 2x MPU6050  | ---> | Real-time Stream   | ---> | Prediction JSON     |
| (thigh + lower-leg) |      | + feature window   |      | + metrics + label   |
+---------------------+      +--------------------+      +---------------------+
             |                                                       |
             v                                                       v
+---------------------+      +--------------------+      +---------------------+
| Streamlit Dashboard | <--- | Live View + Report | <--- | PDF / UI output     |
| Multi-language UI   |      | + clinician display|      | + PDF export        |
+---------------------+      +--------------------+      +---------------------+
```

## Component description

### 1. Synthetic generator

The project begins with [src/01_generate_synthetic.py](../src/01_generate_synthetic.py), which creates a synthetic gait dataset representing low, moderate, and high OA risk.

### 2. Model training

The training pipeline in [src/02_train_model.py](../src/02_train_model.py) creates a multiclass classifier and saves the trained model plus scaler to the models directory.

### 3. Evaluation

The evaluator in [src/03_evaluate_model.py](../src/03_evaluate_model.py) checks model performance and saves metrics to the docs directory.

### 4. ESP32 sensor acquisition

The hardware firmware in [esp32_firmware/oa_screening_firmware.ino](../esp32_firmware/oa_screening_firmware.ino) reads two MPU6050 sensors and sends CSV data to a host computer over Serial at 115200 baud.

### 5. Real-time integration

The real-time bridge in [src/05_esp32_integration.py](../src/05_esp32_integration.py) reads serial data, estimates knee angle, computes gait features, predicts risk, and writes JSON and CSV outputs.

### 6. Dashboard

The dashboard in [dashboard/app.py](../dashboard/app.py) and [dashboard/live_view.py](../dashboard/live_view.py) renders patient data, risk prediction, live updates, and medical report views.

### 7. Reporting

The PDF generator in [dashboard/report_generator.py](../dashboard/report_generator.py) exports clinic-style reports with disclaimers and design placeholders.

## Hardware wiring diagram

```text
               +-------------------+
               |  ESP32 DevKit     |
               |  GPIO21 (SDA)     |
               |  GPIO22 (SCL)     |
               +---------+---------+
                         |
             +-----------+-----------+
             |                       |
     +-------+--------+       +--------+--------+
     | MPU6050 @0x68  |       | MPU6050 @0x69  |
     | Thigh sensor   |       | Lower-leg      |
     |                |       | sensor         |
     +----------------+       +----------------+
```

## Software stack

- Python 3.10+
- NumPy, pandas, scikit-learn
- XGBoost
- Matplotlib, seaborn
- Streamlit
- reportlab, qrcode, pillow
- pyserial

## Data flow explanation

1. Sensor values are captured from the thigh and lower-leg MPU6050 modules.
2. The raw accelerometer and gyroscope inputs are combined using a complementary filter.
3. Knee angle is calculated as thigh angle minus lower-leg angle.
4. Features such as gait speed, stride length, cadence, and step-time variation are derived.
5. The trained machine learning model predicts one of Low, Moderate, or High risk classes.
6. The result is saved to a live JSON file for the dashboard and a CSV log for reporting.

## Medical disclaimer

⚠️ For screening only, not medical diagnosis.

This system is intended for prototype evaluation, clinician-facing screening support, and educational use only. It is not a medical diagnosis and should not replace professional clinical judgment.
