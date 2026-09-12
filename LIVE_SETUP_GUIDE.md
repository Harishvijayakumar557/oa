# COREX OA Screening System — Live Setup & Deployment Guide

This guide provides step-by-step instructions to set up, calibrate, and run the **COREX Osteoarthritis (OA) Screening System** live with the trained AI model, wearable ESP32 sensor hardware, Wi-Fi streaming, and the Flask web portal.

---

## 1. System Requirements & Hardware Checklist

### Hardware Requirements
* **1x ESP32 DevKit** (V1 or NodeMCU ESP-WROOM-32)
* **2x MPU6050 6-Axis IMU Sensors** (with triple-axis accelerometer + gyroscope)
* **Jumper Wires & Breadboard** (or wearable straps)
* **Micro-USB Cable** (for flashing ESP32)
* **Wi-Fi Router or Mobile Hotspot** (PC and ESP32 must be on the same local network)

### Software Requirements
* **Python 3.10+**
* **Arduino IDE** (v2.x recommended) with ESP32 board support installed

---

## 2. Hardware Wiring Diagram

Both MPU6050 sensors share the same I2C bus (`GPIO 21` for SDA, `GPIO 22` for SCL). To avoid I2C address conflict, **Sensor 1 (Thigh)** has its `AD0` pin pulled to `GND` (address `0x68`), and **Sensor 2 (Shank)** has its `AD0` pin pulled to `3.3V` (address `0x69`).

```text
                     +---------------------------------------+
                     |           ESP32 DevKit                |
                     |  3.3V   GND   GPIO21(SDA)  GPIO22(SCL)|
                     +---+------+---------+-----------+------+
                         |      |         |           |
       +-----------------+      |         |           |
       |       +----------------+         |           |
       |       |                          |           |
+------+-------+------+            +------+-----------+------+
| MPU6050 #1 (Thigh)  |            | MPU6050 #2 (Shank)      |
| VCC   -> 3.3V       |            | VCC   -> 3.3V           |
| GND   -> GND        |            | GND   -> GND            |
| SDA   -> GPIO 21    |            | SDA   -> GPIO 21        |
| SCL   -> GPIO 22    |            | SCL   -> GPIO 22        |
| AD0   -> GND (0x68) |            | AD0   -> 3.3V (0x69)    |
+---------------------+            +-------------------------+
```

### Sensor Placement on Patient:
* **Sensor 1 (0x68):** Strapped firmly to the **anterior thigh** (approx. 5–8 cm above the knee patella).
* **Sensor 2 (0x69):** Strapped firmly to the **anterior lower-leg / shank** (approx. 5–8 cm below the knee).

---

## 3. Python Environment & Dependency Installation

1. Open PowerShell or Terminal in the project root directory:
   ```powershell
   cd e:\oa
   ```

2. (Optional but recommended) Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install required packages:
   ```powershell
   python -m pip install -r requirements.txt
   ```

---

## 4. Train & Validate the AI Model

Before running predictions, generate the trained model and feature scaler:

1. Run the model training pipeline:
   ```powershell
   python src/02_train_model.py
   ```

2. What this script does:
   * Loads `data/synthetic_gait.csv` (1,500 gait patterns).
   * Trains and compares `RandomForest`, `XGBoost`, and `SVM` classifiers.
   * Selects the highest-performing model (XGBoost with ~85.7% accuracy).
   * Saves serialized artifacts to:
     * `models/oa_model.pkl` (Trained classifier)
     * `models/scaler.pkl` (StandardScaler)
   * Generates confusion matrices and feature importance charts in `docs/`.

3. Verify artifacts exist:
   ```powershell
   Test-Path models\oa_model.pkl
   Test-Path models\scaler.pkl
   ```

---

## 5. Configure & Flash ESP32 Firmware

1. Open Arduino IDE.
2. In **Tools > Board**, select **ESP32 Dev Module** (or your specific ESP32 board).
3. Install the required Arduino libraries via Library Manager if not already present:
   * `Wire` (built-in)
   * `WiFi` (built-in)
4. Open the firmware file:
   `e:\oa\esp32_firmware\oa_screening_firmware.ino`
5. Edit the Wi-Fi credentials and Target PC IP at the top of the file:
   ```cpp
   // ==========================================
   // --- WI-FI CONFIGURATION (EDIT HERE) ---
   // ==========================================
   const char* WIFI_SSID     = "Your_WiFi_Name";        // Your 2.4GHz Wi-Fi SSID
   const char* WIFI_PASSWORD = "Your_WiFi_Password";    // Your Wi-Fi password

   // IP address of the PC running the Flask server
   const char* SERVER_IP     = "10.229.1.126";          // Replace with your PC's IP
   const uint16_t UDP_PORT   = 5005;                    // Fast UDP streaming port
   ```
6. Connect your ESP32 via USB and click **Upload**.
7. Open **Serial Monitor** (115200 baud) to verify:
   ```text
   Connecting to Wi-Fi SSID: Your_WiFi_Name
   ...
   >>> Wi-Fi Connected Successfully! <<<
   ESP32 IP Address: 10.229.1.45
   Target Flask Server: 10.229.1.126:5005
   READY - Streaming started.
   ```

> **Firewall Note (Windows):** If prompted by Windows Defender Firewall, allow Python to receive incoming connections on Private/Public networks so UDP port `5005` and HTTP port `5000` are accessible.

---

## 6. Launch the Flask Web Application

1. In your terminal, launch the Flask server:
   ```powershell
   python flask_app/app.py
   ```
2. The console will confirm:
   ```text
   * Running on all addresses (0.0.0.0)
   * Running on http://127.0.0.1:5000
   * Running on http://<your-pc-ip>:5000
   ```
3. The UDP background listener will automatically bind to `0.0.0.0:5005` to receive ESP32 packets.

---

## 7. Conducting a Live Screening Workflow

### Step 7.1: Patient Intake
1. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/register
   ```
2. Enter patient demographic information, medical history, and clinical symptoms (knee pain, stiffness, chair-standing difficulty).
3. Select **LIVE** screening mode and click **Save & Proceed to Screening**.

### Step 7.2: Live Sensor Ingestion & Kinematics
1. You will be redirected to the Analysis screen (`/analysis`).
2. Verify the status banner at the top:
   * **Status Badge:** Switches to **`🟢 Connected: Wi-Fi (UDP) (10.229.1.x)`**.
   * **Live Knee Angle:** Displays real-time angle in degrees ($|\theta_{thigh} - \theta_{shank}|$).
   * **Step Counter:** Increments automatically on gait foot strikes.
   * **Live Cadence:** Computes real-time walking tempo ($steps/min$).
   * **Kinematics Waveform:** The dynamic Chart.js graph renders smooth flexion/extension oscillations as the patient walks.
3. Have the patient walk in a straight line for 10–20 meters.
4. The 6 gait metrics on the left panel will automatically update to reflect the patient's actual biomechanical values:
   * Gait Speed ($m/s$)
   * Stride Time ($s$)
   * Stride Length ($m$)
   * Cadence ($steps/min$)
   * Knee ROM ($^\circ$)
   * Step Time Std ($s$)

### Step 7.3: AI Inference & Clinical Report
1. Once sufficient walking data has been captured, click **Analyze Risk**.
2. The system executes:
   * Feature contract validation against normative clinical bounds.
   * Standard scaling and model inference via `models/oa_model.pkl`.
   * Risk tier determination: **Low Risk**, **Moderate Risk**, or **High Risk** with class probability distribution.
   * ReportLab PDF generation with embedded QR verification code and medical disclaimer.
3. You will be automatically redirected to the detailed report view (`/report/<screening_id>`), where you can review findings and download the clinical screening PDF.

---

## 8. Testing Without Physical Hardware (Simulation Mode)

If your ESP32 is not plugged in or you want to test the entire website UI immediately:
1. Open `http://127.0.0.1:5000/analysis`.
2. In the top Wi-Fi banner, click **Test Wi-Fi Stream**.
3. The built-in kinematics engine will simulate an active walking session:
   * The status badge turns **`🟢 Connected: Simulation`**.
   * The knee angle dynamically flexes and extends (30° to 75°).
   * Steps increment and cadence is computed.
   * Gait sliders update in real-time.
4. Click **Analyze Risk** to test prediction and report generation.
5. Click **Stop Test Stream** when done.

---

## 9. Troubleshooting & FAQ

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| **"Waiting for ESP32 Wi-Fi..." banner never turns green** | PC firewall blocking port 5005 or ESP32 on different Wi-Fi network | 1. Ensure PC and ESP32 are connected to the exact same Wi-Fi SSID.<br>2. Run `powershell New-NetFirewallRule -DisplayName "OA UDP 5005" -Direction Inbound -LocalPort 5005 -Protocol UDP -Action Allow`.<br>3. Verify IP configured in `oa_screening_firmware.ino` matches `serverIpDisplay`. |
| **Model prediction fails with "Model file not found"** | `models/oa_model.pkl` has not been generated | Run `python src/02_train_model.py` in your terminal to train and save the model artifacts. |
| **I2C error or readings return 0 on ESP32** | Loose wiring or wrong MPU6050 address | Check jumper wires: ensure Thigh `AD0 -> GND` (0x68) and Shank `AD0 -> 3.3V` (0x69). |
| **Knee angle values seem inverted or flat** | IMU orientation mismatch | Ensure both IMU boards are mounted facing the same forward orientation on the thigh and shank. |

---

## 10. Medical Disclaimer

⚠️ **For Research & Prototype Screening Only — Not Medical Diagnosis.**  
This screening system is intended for mobility evaluation, early risk assessment, and clinical decision support. It is not a medical diagnosis and must never replace professional clinical judgment or radiological evaluation.
