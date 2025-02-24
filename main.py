import streamlit as st
import importlib

st.set_page_config(page_title="Job Market Analysis", layout="wide")

st.title("Job Market Analysis Dashboards")

# Create a radio button to select the dashboard
dashboard_selection = st.radio(
    "Select Dashboard:",
    ("Adzuna Job Analysis", "Jora Job Analysis")
)

# Dictionary to map selection to module names
modules = {
    "Adzuna Job Analysis": "dropdown_function",
    "Jora Job Analysis": "job_heatmap"
}

# Dynamically import the selected module
module_name = modules[dashboard_selection]
module = importlib.import_module(module_name)
