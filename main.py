import streamlit as st
import importlib

# ✅ Ensure this is the FIRST Streamlit command
st.set_page_config(page_title="Job Analysis Dashboards", layout="wide")

st.title("Job Market Analysis Dashboards")

# Create a radio button to select the dashboard
dashboard_selection = st.radio(
    "Select Dashboard:",
    ("Adzuna Job Analysis", "Jora Job Analysis")
)

# Dictionary mapping selection to module names
modules = {
    "Adzuna Job Analysis": "dropdown_function",
    "Jora Job Analysis": "job_heatmap"
}

module_name = modules[dashboard_selection]

# ✅ Use caching to prevent unnecessary reloading
@st.cache_resource
def load_module(module_name):
    return importlib.import_module(module_name)

try:
    module = load_module(module_name)  # ✅ Import dynamically
    st.success(f"Loaded {module_name} successfully!")
except Exception as e:
    st.error(f"Failed to load {module_name}: {e}")
