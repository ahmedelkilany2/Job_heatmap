import streamlit as st
import importlib
import os
# Set environment variable to prevent app from sleeping
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
# this is the FIRST Streamlit command
st.set_page_config(
    page_title="Job Analysis Dashboards", 
    layout="wide",
    # This helps with keeping the session alive
    initial_sidebar_state="expanded"
)
# Additional configuration to prevent sleeping
st._config.set_option('server.maxUploadSize', 200)
st._config.set_option('server.maxMessageSize', 200)
st.title("Job Market Analysis Dashboards")
# Create a radio button to select the dashboard
dashboard_selection = st.radio(
    "Select Dashboard:",
    ("Adzuna Job Analysis", "Jora Job Analysis", "Seek Job Analysis", "Indeed Job Analysis")
)
# Dictionary mapping selection to module names
modules = {
    "Adzuna Job Analysis": "dropdown_function",
    "Jora Job Analysis": "jora_heatmap",
    "Seek Job Analysis": "seek_heatmap",
    "Indeed Job Analysis": "indeed_heatmap"
}
module_name = modules[dashboard_selection]
# Import the selected module - do NOT cache this!
try:
    module = importlib.import_module(module_name)
    
    # Now call the module's main function
    if hasattr(module, 'main'):
        module.main()
    else:
        st.error(f"The {module_name} module doesn't have a main() function.")
        st.info("Each module must have a main() function that contains all the Streamlit UI code.")
except Exception as e:
    st.error(f"Failed to load or run {module_name}: {str(e)}")
    st.code(f"Error details: {e}")
    
    # More detailed error handling for debugging
    import traceback
    st.code(traceback.format_exc())
