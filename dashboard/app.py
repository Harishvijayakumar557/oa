from __future__ import annotations

import base64
import datetime as dt
import io
import json
import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.report_generator import build_report_bytes
from dashboard.translations import LANGUAGE_OPTIONS, REGION_OPTIONS, TRANSLATIONS, t

MODEL_PATH = ROOT / "models" / "oa_model.pkl"
SCALER_PATH = ROOT / "models" / "scaler.pkl"
FEATURES = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
]
RISK_LABELS = {0: "Low Risk", 1: "Moderate Risk", 2: "High Risk"}
RISK_COLORS = {
    0: "#22c55e",
    1: "#f59e0b",
    2: "#ef4444",
}
NORMAL_RANGES = {
    "gait_speed": (1.05, 1.55),
    "stride_time": (0.90, 1.25),
    "stride_length": (1.10, 1.50),
    "cadence": (100, 125),
    "knee_rom": (45, 65),
    "step_time_std": (0.02, 0.08),
}


def load_css() -> None:
    css_path = Path(__file__).resolve().parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def get_lang(code: str) -> dict:
    return TRANSLATIONS.get(code, TRANSLATIONS["en"])


@st.cache_resource
def load_model_and_scaler():
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        st.error("Training artifacts not found. Please train the model first:")
        st.code("python src/02_train_model.py")
        st.stop()
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return model, scaler


def make_prediction(model, scaler, patient_values: dict) -> dict:
    row = pd.DataFrame([patient_values], columns=FEATURES)
    X = scaler.transform(row)
    pred = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0]
    conf = float(np.max(proba) * 100)
    output = {
        "risk_label": RISK_LABELS.get(pred, "Low Risk"),
        "risk_code": pred,
        "confidence": conf,
        "proba": proba,
        "probabilities": {label: float(prob) for label, prob in zip([0, 1, 2], proba)},
    }
    return output


def patient_status(value: float, feature: str) -> str:
    low, high = NORMAL_RANGES[feature]
    if value < low or value > high:
        return "abnormal"
    return "normal"


def feature_table(patient_values: dict, lang_dict: dict) -> pd.DataFrame:
    rows = []
    for feature in FEATURES:
        value = float(patient_values[feature])
        low, high = NORMAL_RANGES[feature]
        status = "normal" if low <= value <= high else "warning"
        rows.append({
            "Feature": feature,
            "Value": round(value, 3),
            "Normal range": f"{low} to {high}",
            "Status": status,
        })
    return pd.DataFrame(rows)


def feature_contribution_chart(probabilities: dict, lang_dict: dict) -> None:
    labels = [lang_dict.get('low_risk', 'Low Risk'), lang_dict.get('moderate_risk', 'Moderate Risk'), lang_dict.get('high_risk', 'High Risk')]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, [probabilities[0], probabilities[1], probabilities[2]], color=['#22c55e', '#f59e0b', '#ef4444'])
    ax.set_ylabel('Probability')
    ax.set_title(lang_dict.get('feature_contribution', 'Feature contribution'))
    ax.set_ylim(0, 1.05)
    fig.tight_layout()
    return fig


def render_sidebar(lang_code: str, lang_dict: dict) -> tuple[str, dict]:
    with st.sidebar:
        st.markdown("<div style='text-align:center;'><h2>🏥 OA Screening System</h2></div>", unsafe_allow_html=True)
        st.markdown("---")

        st.subheader(lang_dict.get('nav_overview', 'Overview'))
        nav = st.radio(
            'Navigation',
            [
                lang_dict.get('nav_patient', 'Patient Registration'),
                lang_dict.get('nav_gait', 'Gait Data Input'),
                lang_dict.get('nav_results', 'Analysis Results'),
                lang_dict.get('nav_risk', 'Risk Prediction'),
                lang_dict.get('nav_report', 'Medical Report'),
                lang_dict.get('nav_guidance', 'Guidance'),
            ],
            index=0,
            key='nav_selection',
        )

        st.markdown("---")
        st.subheader("Language")
        grouped = {}
        for region_name, codes in REGION_OPTIONS:
            grouped[region_name] = [LANGUAGE_OPTIONS[code] for code in codes]

        selected_lang = st.selectbox(
            "Select language",
            options=[code for code in TRANSLATIONS.keys()],
            format_func=lambda code: LANGUAGE_OPTIONS.get(code, code),
            index=0,
            key='lang_selector',
        )

        st.markdown("---")
        st.caption(lang_dict.get('sidebar_disclaimer', 'For screening only, not medical diagnosis'))
        st.caption("© Clinical prototype")

    return nav, {'selected_lang': selected_lang}


def page_patient_registration(lang_dict: dict) -> None:
    st.header(f"🩺 {lang_dict.get('patient_registration', 'Patient Registration')}")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input(lang_dict.get('name', 'Name'), key='patient_name')
        st.number_input(lang_dict.get('age', 'Age'), min_value=1, max_value=120, value=45, key='patient_age')
        st.selectbox(lang_dict.get('gender', 'Gender'), [lang_dict.get('gender_male', 'Male'), lang_dict.get('gender_female', 'Female'), lang_dict.get('gender_other', 'Other')], key='patient_gender')
    with col2:
        st.slider(lang_dict.get('pain_level', 'Pain level'), 1, 10, 5, key='pain_level')
        st.selectbox(lang_dict.get('mobility_difficulty', 'Mobility difficulty'), [lang_dict.get('mobility_normal', 'Normal'), lang_dict.get('mobility_mild', 'Mild limitation'), lang_dict.get('mobility_moderate', 'Moderate limitation'), lang_dict.get('mobility_severe', 'Severe limitation')], key='mobility_difficulty')
        st.selectbox(lang_dict.get('region', 'Region'), ['North East', 'North', 'South', 'Central', 'Other'], key='patient_region')

    st.text_area(lang_dict.get('medical_history', 'Medical history'), key='medical_history')
    st.session_state['language_pref'] = st.selectbox(lang_dict.get('language_pref', 'Language preference'), list(LANGUAGE_OPTIONS.values()), key='language_pref')
    st.button(lang_dict.get('save_patient', 'Save patient'))
    st.markdown("<div class='medical-divider'></div>", unsafe_allow_html=True)


def page_gait_input(lang_dict: dict) -> None:
    st.header(f"📊 {lang_dict.get('gait_analysis', 'Gait Analysis')}")
    tab_manual, tab_upload = st.tabs([lang_dict.get('manual_entry', 'Manual entry'), lang_dict.get('upload_csv', 'Upload CSV from ESP32')])

    sample_values = {
        'gait_speed': 1.25,
        'stride_time': 1.10,
        'stride_length': 1.30,
        'cadence': 110,
        'knee_rom': 55,
        'step_time_std': 0.05,
    }

    with tab_manual:
        patient_values = {}
        for feature in FEATURES:
            low, high = NORMAL_RANGES[feature]
            if feature == 'step_time_std':
                patient_values[feature] = st.slider(feature, 0.01, 0.20, float(sample_values[feature]), 0.01)
            elif feature == 'cadence':
                patient_values[feature] = st.slider(feature, 70, 150, int(sample_values[feature]), 1)
            else:
                patient_values[feature] = st.slider(feature, float(low) - 0.5, float(high) + 0.5, float(sample_values[feature]), 0.01)
        st.session_state['patient_values'] = patient_values
        st.caption(lang_dict.get('sample_values', 'Sample values'))
        st.json(sample_values)

    with tab_upload:
        uploaded = st.file_uploader(lang_dict.get('upload_csv', 'Upload CSV from ESP32'), type=['csv'])
        if uploaded is not None:
            df = pd.read_csv(uploaded)
            st.dataframe(df.head())
            if all(feature in df.columns for feature in FEATURES):
                for feature in FEATURES:
                    st.session_state['patient_values'] = {feature: float(df[feature].mean()) for feature in FEATURES}
                st.success('CSV loaded successfully')
            else:
                st.warning('CSV is missing required features.')


def page_analysis_results(lang_dict: dict, patient_values: dict) -> None:
    st.header(f"📋 {lang_dict.get('analysis_results', 'Analysis Results')}")
    summary = st.container()
    with summary:
        st.markdown("<div class='report-card'>", unsafe_allow_html=True)
        st.subheader(lang_dict.get('patient_summary', 'Patient Summary'))
        st.write(f"{lang_dict.get('name', 'Name')}: {st.session_state.get('patient_name', 'N/A')}")
        st.write(f"{lang_dict.get('age', 'Age')}: {st.session_state.get('patient_age', 0)}")
        st.write(f"{lang_dict.get('pain_level', 'Pain level')}: {st.session_state.get('pain_level', 0)}/10")
        st.markdown("</div>", unsafe_allow_html=True)

    table = feature_table(patient_values, lang_dict)
    st.dataframe(table, use_container_width=True)

    st.subheader(lang_dict.get('gait_features', 'Gait Features'))
    chart_df = pd.DataFrame({
        'Feature': FEATURES,
        'Value': [patient_values[f] for f in FEATURES],
        'Reference': [np.mean([NORMAL_RANGES[f][0], NORMAL_RANGES[f][1]]) for f in FEATURES],
    })
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=chart_df, x='Feature', y='Value', color='#4c8bf5', ax=ax)
    ax.axhline(0, color='gray')
    ax.set_title('Feature Comparison')
    fig.tight_layout()
    st.pyplot(fig)


def page_risk_prediction(lang_dict: dict, patient_values: dict, model, scaler) -> None:
    st.header(f"⚕️ {lang_dict.get('risk_assessment', 'Risk Assessment')}")
    prediction = make_prediction(model, scaler, patient_values)
    risk_code = prediction['risk_code']
    risk_label = prediction['risk_label']
    conf = prediction['confidence']

    classes = [lang_dict.get('low_risk', 'Low Risk'), lang_dict.get('moderate_risk', 'Moderate Risk'), lang_dict.get('high_risk', 'High Risk')]
    class_values = [prediction['probabilities'][0], prediction['probabilities'][1], prediction['probabilities'][2]]

    st.markdown(f"<div class='report-card risk-{['low','moderate','high'][risk_code]}'>", unsafe_allow_html=True)
    st.subheader(f"{lang_dict.get('risk_level', 'Risk level')}: {risk_label}")
    st.metric(lang_dict.get('confidence', 'Confidence'), f"{conf:.1f}%")
    st.markdown("</div>", unsafe_allow_html=True)

    fig = feature_contribution_chart(prediction['probabilities'], lang_dict)
    st.pyplot(fig)

    st.markdown("<div class='medical-divider'></div>", unsafe_allow_html=True)
    st.write("Model explanation: The model compares the patient's gait metrics with learned patterns for low, moderate, and high OA risk classes.")


def page_report(lang_dict: dict, patient_values: dict, prediction: dict) -> None:
    st.header(f"📄 {lang_dict.get('nav_report', 'Medical Report')}")
    patient_data = {
        'name': st.session_state.get('patient_name', 'N/A'),
        'age': st.session_state.get('patient_age', 0),
        'gender': st.session_state.get('patient_gender', 'N/A'),
        'medical_history': st.session_state.get('medical_history', 'N/A'),
        'pain_level': st.session_state.get('pain_level', 0),
        'mobility_difficulty': st.session_state.get('mobility_difficulty', 'N/A'),
    }
    report_bytes = build_report_bytes(patient_data, prediction, language='en')
    st.download_button(
        label=lang_dict.get('download_report', 'Download Report'),
        data=report_bytes,
        file_name=f"OA_report_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime='application/pdf',
    )

    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    st.write(f"{lang_dict.get('report_id', 'Report ID')}: OA-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}")
    st.write(f"{lang_dict.get('report_generated', 'Report generated')}: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"{lang_dict.get('risk_level', 'Risk level')}: {prediction['risk_label']}")
    st.markdown("</div>", unsafe_allow_html=True)


def page_guidance(lang_dict: dict, prediction: dict) -> None:
    st.header(f"💡 {lang_dict.get('nav_guidance', 'Guidance')}")
    risk_code = prediction['risk_code']
    if risk_code == 0:
        recommendations = [
            'Maintain regular low-impact activities and strengthen quadriceps and hamstrings.',
            'Continue routine mobility and flexibility check-ups.',
        ]
    elif risk_code == 1:
        recommendations = [
            'Reduce loading on the painful side and increase physiotherapy sessions.',
            'Use supportive footwear and range-of-motion exercises.',
        ]
    else:
        recommendations = [
            'Urgent clinical review is recommended.',
            'Consider physiotherapy, orthopaedic consultation, and symptom monitoring.',
        ]
    for item in recommendations:
        st.write(f"• {item}")
    st.markdown("<div class='medical-divider'></div>", unsafe_allow_html=True)
    st.write(lang_dict.get('referral_note', 'Refer to physiotherapist/orthopaedic review if high risk persists'))


def main() -> None:
    load_css()
    st.set_page_config(page_title='OA Screening System', page_icon='🏥', layout='wide')
    model, scaler = load_model_and_scaler()

    default_lang = 'en'
    if 'selected_language' not in st.session_state:
        st.session_state['selected_language'] = default_lang

    selected_lang = st.selectbox(
        'Language',
        options=list(TRANSLATIONS.keys()),
        format_func=lambda code: LANGUAGE_OPTIONS.get(code, code),
        index=0,
        key='language_selector',
    )
    st.session_state['selected_language'] = selected_lang
    lang_dict = get_lang(selected_lang)

    if 'patient_values' not in st.session_state:
        st.session_state['patient_values'] = {feature: NORMAL_RANGES[feature][0] for feature in FEATURES}

    nav = st.sidebar.radio('Navigation', [
        lang_dict.get('nav_patient', 'Patient Registration'),
        lang_dict.get('nav_gait', 'Gait Data Input'),
        lang_dict.get('nav_results', 'Analysis Results'),
        lang_dict.get('nav_risk', 'Risk Prediction'),
        lang_dict.get('nav_report', 'Medical Report'),
        lang_dict.get('nav_guidance', 'Guidance'),
    ], index=0, key='main_nav')

    st.sidebar.markdown('---')
    st.sidebar.caption(lang_dict.get('disclaimer', 'For screening only, not medical diagnosis'))

    patient_values = st.session_state.get('patient_values', {feature: 1.0 for feature in FEATURES})

    if nav == lang_dict.get('nav_patient', 'Patient Registration'):
        page_patient_registration(lang_dict)
    elif nav == lang_dict.get('nav_gait', 'Gait Data Input'):
        page_gait_input(lang_dict)
    elif nav == lang_dict.get('nav_results', 'Analysis Results'):
        page_analysis_results(lang_dict, patient_values)
    elif nav == lang_dict.get('nav_risk', 'Risk Prediction'):
        if 'patient_values' not in st.session_state or not all(feature in st.session_state['patient_values'] for feature in FEATURES):
            st.warning('Please provide gait values before running analysis.')
            return
        page_risk_prediction(lang_dict, st.session_state['patient_values'], model, scaler)
    elif nav == lang_dict.get('nav_report', 'Medical Report'):
        prediction = make_prediction(model, scaler, st.session_state.get('patient_values', {feature: 1.0 for feature in FEATURES}))
        page_report(lang_dict, st.session_state.get('patient_values', {}), prediction)
    else:
        prediction = make_prediction(model, scaler, st.session_state.get('patient_values', {feature: 1.0 for feature in FEATURES}))
        page_guidance(lang_dict, prediction)

    st.markdown("<div class='medical-divider'></div>", unsafe_allow_html=True)
    st.caption(lang_dict.get('screening_only', 'This system is for early screening and risk assessment only. Not a medical diagnosis.'))


if __name__ == '__main__':
    main()
