import os
import pandas as pd
import streamlit as st
import plotly.express as px
from google import genai
from google.genai import types
from dotenv import load_dotenv
from bot_tools import calculate_sheet_metric, generate_data_visualization

load_dotenv()

# Page Setup
st.set_page_config(
    page_title="Analytics Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dark Theme Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }

    .app-header {
        font-size: 1.75rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.25rem;
    }
    .app-subtitle {
        color: #94A3B8;
        font-size: 0.875rem;
        margin-bottom: 1.5rem;
    }

    [data-testid="stChatMessage"] {
        background-color: #1E293B !important;
        border: 1px solid #334155;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin-bottom: 0.75rem !important;
    }

    .metric-box {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-left: 3px solid #3B82F6;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        color: #E2E8F0;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Client Initialization
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Main Header
st.markdown('<div class="app-header">Data Analytics Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Upload your dataset to calculate formulas, generate visualizations, or manually configure charts.</div>', unsafe_allow_html=True)

# Session State Setup
if "df" not in st.session_state:
    st.session_state.df = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar - Dataset Upload
st.sidebar.markdown("### Dataset Upload")
uploaded_file = st.sidebar.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        st.session_state.df = pd.read_csv(uploaded_file)
    else:
        st.session_state.df = pd.read_excel(uploaded_file)
    
    st.sidebar.success("File loaded successfully")
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Dataset Overview**")
    st.sidebar.text(f"Rows: {st.session_state.df.shape[0]} | Columns: {st.session_state.df.shape[1]}")
    st.sidebar.dataframe(st.session_state.df.head(5), width="stretch")
    
    # Sidebar - Manual Graph Settings
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Graph Settings")
    
    columns = list(st.session_state.df.columns)
    chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar", "Scatter", "Histogram"])
    x_axis = st.sidebar.selectbox("X-Axis", columns)
    
    # Y-Axis selection (optional for histogram)
    if chart_type != "Histogram":
        y_axis = st.sidebar.selectbox("Y-Axis", columns)
    else:
        y_axis = None

    color_by = st.sidebar.selectbox("Color / Group By (Optional)", ["None"] + columns)
    color_param = None if color_by == "None" else color_by

    if st.sidebar.button("Generate Manual Chart"):
        # Build manual chart figure using Plotly Express
        if chart_type == "Line":
            fig = px.line(st.session_state.df, x=x_axis, y=y_axis, color=color_param, title=f"{y_axis} over {x_axis}")
        elif chart_type == "Bar":
            fig = px.bar(st.session_state.df, x=x_axis, y=y_axis, color=color_param, title=f"{y_axis} by {x_axis}")
        elif chart_type == "Scatter":
            fig = px.scatter(st.session_state.df, x=x_axis, y=y_axis, color=color_param, title=f"{y_axis} vs {x_axis}")
        elif chart_type == "Histogram":
            fig = px.histogram(st.session_state.df, x=x_axis, color=color_param, title=f"Distribution of {x_axis}")

        # Dark theme layout for chart
        fig.update_layout(
            paper_bgcolor='#1E293B',
            plot_bgcolor='#1E293B',
            font=dict(color='#F8FAFC'),
            xaxis=dict(gridcolor='#334155'),
            yaxis=dict(gridcolor='#334155')
        )
        
        # Append manual chart to conversation stream
        msg_text = f"Manual **{chart_type} Chart** generated for `{x_axis}`" + (f" vs `{y_axis}`" if y_axis else "") + "."
        st.session_state.messages.append({"role": "assistant", "content": msg_text, "chart": fig})

# Render Chat History (with Chart Support)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)
        if "chart" in msg and msg["chart"] is not None:
            st.plotly_chart(msg["chart"], width="stretch")

# Input Prompt Handling (AI Agent)
if prompt := st.chat_input("Ask a question about your data or request a chart..."):
    if st.session_state.df is None:
        st.warning("Please upload a CSV or Excel file in the sidebar to get started.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[calculate_sheet_metric, generate_data_visualization],
                system_instruction=(
                    "You are a helpful data analytics assistant. "
                    "When asked to create a chart or plot data, you MUST call the generate_data_visualization function tool. "
                    f"Available dataset columns: {list(st.session_state.df.columns)}"
                )
            )
        )

        # Force execution of tool calls
        if response.function_calls:
            for call in response.function_calls:
                fn_name = call.name
                args = call.args

                if fn_name == "calculate_sheet_metric":
                    res = calculate_sheet_metric(st.session_state.df, **args)
                    formatted_res = f'<div class="metric-box"><strong>Result:</strong> <code>{res}</code></div>'
                    st.markdown(formatted_res, unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": formatted_res})

                elif fn_name == "generate_data_visualization":
                    fig = generate_data_visualization(st.session_state.df, **args)
                    fig.update_layout(
                        paper_bgcolor='#1E293B',
                        plot_bgcolor='#1E293B',
                        font=dict(color='#F8FAFC'),
                        xaxis=dict(gridcolor='#334155'),
                        yaxis=dict(gridcolor='#334155')
                    )
                    st.plotly_chart(fig, width="stretch")
                    msg_text = f"Rendered chart for `{args.get('x_axis')}` vs `{args.get('y_axis')}`."
                    st.session_state.messages.append({"role": "assistant", "content": msg_text, "chart": fig})
        else:
            text_response = response.text or "Request processed."
            st.markdown(text_response)
            st.session_state.messages.append({"role": "assistant", "content": text_response})