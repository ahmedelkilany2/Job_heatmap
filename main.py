import streamlit as st

st.set_page_config(page_title="Job Market Analysis", layout="wide")

st.title("Job Market Analysis Dashboards")

# Create a radio button to select the dashboard
dashboard_selection = st.radio(
    "Select Dashboard:",
    ("Adzuna Job Analysis", "Jora Job Analysis")
)

if dashboard_selection == "Adzuna Job Analysis":
    import dropdown_function
elif dashboard_selection == "Jora Job Analysis":
    import job_heatmap
