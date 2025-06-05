import os
import pickle
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, roc_curve, precision_recall_curve, auc
import seaborn as sns
import pandas as pd
import altair as alt

st.set_page_config(page_title="예측 결과", layout="centered")
st.title("예측 결과")

# Add threshold slider in sidebar
st.sidebar.header("예측 임계값 설정")
threshold = st.sidebar.slider("이탈 확률 기준 (Threshold)", 0.0, 1.0, 0.5, 0.01)
st.sidebar.write(f"현재 Threshold: {threshold:.2f}")

# Check if required data exists in session state
if "customer_info" not in st.session_state or "selected_model" not in st.session_state:
    st.warning("모든 정보를 입력해주세요.")
    st.switch_page("pages/1_고객_정보_입력.py")

# Get selected model
selected_model = st.session_state.get("selected_model")
if selected_model not in ["CatBoost", "LightGBM"]:
    st.warning("지원하지 않는 모델입니다.")
    st.switch_page("pages/2_모델_선택.py")

# Load the model
@st.cache_resource
def load_model():
    try:
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", f"{selected_model}.pkl")
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        return model
    except Exception as e:
        st.error(f"모델 로드 중 오류가 발생했습니다: {str(e)}")
        st.stop()

model = load_model()

# Get customer info from session state
customer_info = st.session_state.customer_info

# Prepare input features
feature_names = ['LogAge', 'NumOfProducts', 'IsActiveMember', 'Geography', 'Gender', 'Balance']

# Create a dictionary with the correct feature order
input_dict = {
    'LogAge': customer_info["LogAge"],
    'NumOfProducts': customer_info["NumOfProducts"],
    'IsActiveMember': customer_info["IsActiveMember"],
    'Geography': customer_info["Geography"],  # Keep original string values
    'Gender': customer_info["Gender"],  # Keep original string values
    'Balance': customer_info["Balance"]
}

# Convert to DataFrame with explicit column order
input_features = pd.DataFrame([input_dict], columns=feature_names)

# Validate feature names
if not all(col in input_features.columns for col in feature_names):
    st.error("Feature names mismatch with model expectations")
    st.stop()

# Make prediction
try:
    # Handle different model types
    if selected_model == "CatBoost":
        input_features['Geography'] = input_features['Geography'].map({'France': 0, 'Germany': 1, 'Spain': 2})
        input_features['Gender'] = input_features['Gender'].map({'Female': 0, 'Male': 1})
        prediction = model.predict(input_features)[0]
        prediction_proba = model.predict_proba(input_features)[0]
    else:  # LightGBM
        # Convert categorical features to numeric for LightGBM
        input_features['Geography'] = input_features['Geography'].map({'France': 0, 'Germany': 1, 'Spain': 2})
        input_features['Gender'] = input_features['Gender'].map({'Female': 0, 'Male': 1})
        prediction = model.predict(input_features)[0]
        prediction_proba = model.predict_proba(input_features)[0]

    # Display prediction result
    #st.subheader("📈 예측 결과")
    
    # Calculate probability
    prob = prediction_proba[1]  # class=1 이탈 확률
    
    # Create containers for dynamic updates
    prob_container = st.empty()
    result_container = st.empty()
    chart_container = st.empty()
    
    def update_display():
        # Update probability display
        prob_container.write(f"▶ **이탈 확률(Probability)** : **{prob:.3f}**")
        
        # Update prediction result based on threshold
        if prob >= threshold:
            result_container.error(f"▶ **예측 결과**: 이탈 고객 (Prob ≥ {threshold:.2f})")
        else:
            result_container.success(f"▶ **예측 결과**: 잔류 고객 (Prob < {threshold:.2f})")

        # Create donut chart using Altair
        # Choose colors based on threshold comparison
        if prob >= threshold:
            colors = ['#E74C3C', '#781F16']  # Red shades
        else:
            colors = ['#27AE60', '#7D8C83']  # Green shades

        # Create data for the chart
        source = pd.DataFrame({
            "Category": ['이탈 확률', '유지 확률'],
            "Value": [prob, 1-prob]
        })

        # Create the donut chart
        chart = alt.Chart(source).mark_arc(
            innerRadius=150,
            cornerRadius=15
        ).encode(
            theta=alt.Theta(field="Value", type="quantitative"),
            color=alt.Color(
                field="Category",
                type="nominal",
                scale=alt.Scale(domain=['이탈 확률', '유지 확률'], range=colors),
                legend=None
            )
        ).properties(
            width=400,
            height=400
        )

        # Add text in the center
        text = alt.Chart(pd.DataFrame({'text': [f'{prob*100:.1f}%']})).mark_text(
            align='center',
            baseline='middle',
            fontSize=48,
            font='Arial Black',
            color=colors[0]
        ).encode(
            text='text',
            x=alt.value(200),
            y=alt.value(200)
        )

        # Combine the chart and text
        final_chart = (chart + text).configure_view(
            strokeWidth=0
        )

        # Display the chart
        chart_container.altair_chart(final_chart, use_container_width=True)

    # Initial display
    update_display()

    # Update display when threshold changes
    if st.session_state.get('_threshold') != threshold:
        st.session_state['_threshold'] = threshold
        update_display()

except Exception as e:
    st.error(f"예측 중 오류가 발생했습니다: {str(e)}")

# Add navigation buttons
st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("이전 단계"):
        st.switch_page("pages/2_모델_선택.py")

with col2:
    if st.button("새로운 예측 시작하기"):
        # Clear session state
        for key in ["customer_info", "selected_model"]:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("pages/1_고객_정보_입력.py")
st.markdown('</div>', unsafe_allow_html=True)
