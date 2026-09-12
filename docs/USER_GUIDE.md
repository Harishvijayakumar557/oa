# OA Screening User Guide

## Purpose

This user guide explains how healthcare workers can use the OA Screening System to capture gait-related data, run the analysis pipeline, review risk output, and plan next steps.

## Step-by-step screening process

1. Prepare the patient.
   - Confirm consent for screening.
   - Ensure the patient is comfortable and walking naturally.
   - Secure the two MPU6050 sensors on the thigh and lower leg.

2. Power the ESP32 and confirm connection.
   - Connect the device to the host computer.
   - Run the real-time integration script.
   - Confirm the serial stream is active.

3. Begin gait capture.
   - Ask the patient to walk a short path at a comfortable pace.
   - Let the system collect the time series window.
   - Watch the live knee-angle and feature display.

4. Review the model output.
   - The system classifies the gait into Low / Moderate / High risk.
   - Review the predicted confidence and relevant gait features.

5. Record the result.
   - Save the report.
   - Add any clinic notes and patient history.

6. Decide next steps.
   - Low: continue routine monitoring.
   - Moderate: increase therapy or observe symptoms.
   - High: refer for specialist review if clinically indicated.

## How to interpret results

The model uses features such as gait speed, stride time, stride length, cadence, knee range of motion, and step-time variability. The result is a screening estimate only.

### Typical interpretation

- Low risk: gait pattern closer to stable range and lower biomechanical abnormality.
- Moderate risk: indicates potential mobility concern or altered gait pattern.
- High risk: indicates clinically significant deviation and needs specialist evaluation.

## When to refer the patient

Healthcare staff should consider prompt clinical review when:

- the patient reports worsening pain or instability,
- the gait pattern remains abnormal across repeated tests,
- the risk remains high across multiple readings,
- the patient has mobility restrictions or falls.

## Multi-language note

The dashboard supports several languages for clinician and patient communication, including regional language variants relevant to North East India. This feature improves readability for local workflows but should not replace formal clinical translation or documentation.

## Disclaimer

⚠️ For screening only, not medical diagnosis.

This tool is intended for gait screening support and educational use only. It must not be used to diagnose or treat medical conditions without proper clinical review.
