# OA Screening Project Overview

## System concept

This project models a low-cost osteoarthritis screening system using two MPU6050 sensors placed on the left and right lower limbs. The goal is to estimate walking quality and classify the gait pattern as:

- Low risk
- Moderate risk
- High risk

## Sensor assumptions

- Two MPU6050 devices capture triaxial acceleration and angular velocity
- Each sensor records synchronized motion during walking trials
- Features are derived from gait stability, asymmetry, cadence, and stride variability

## ML workflow

1. Generate synthetic patient gait examples
2. Build feature vectors from motion metrics
3. Train a multiclass XGBoost model
4. Save model artifacts for later inference
5. Create a dashboard for reporting the prediction result to clinicians or users

## Example features used

- left_peak_accel_x
- left_peak_accel_y
- right_peak_accel_x
- right_peak_accel_y
- left_gyro_std
- right_gyro_std
- gait_asymmetry
- stride_time_mean
- cadence
- stability_index
- vertical_displacement

## Suggested deployment extension

- ESP32 reads sensor data over I2C and sends it to a local server
- Python pipeline preprocesses the raw stream and generates gait metrics
- Model predicts OA risk in real time
- Dashboard displays confidence and summary charts
