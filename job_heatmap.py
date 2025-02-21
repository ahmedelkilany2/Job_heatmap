import pandas as pd
import folium
from folium.plugins import HeatMap
import streamlit as st
from streamlit_folium import st_folium

# Streamlit Page Configuration
st.set_page_config(
    page_title="Job Location Heatmap",
    page_icon="🗺️",
    layout="wide"
)

st.title("Job Location Heatmap - Australia 🇦🇺")
st.markdown("This heatmap visualizes job postings across Australia based on location data.")

# Google Sheets CSV URL
sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/edit?gid=0#gid=0"

# Load data
@st.cache_data(ttl=14400)  # Cache for 4 hours
def load_data():
    try:
        df = pd.read_csv(sheet_url)
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df = df.dropna(subset=["latitude", "longitude"])  # Remove invalid rows
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

df = load_data()

# Create the Heatmap
def create_heatmap(df):
    if df is None or df.empty:
        st.warning("No valid location data available for plotting.")
        return

    # Define Australia’s map center
    map_center = [-25, 133]  # Approximate center of Australia
    job_map = folium.Map(location=map_center, zoom_start=4, tiles="cartodbpositron")

    # Prepare the heatmap data
    heat_data = df[["latitude", "longitude"]].values.tolist()
    
    # Add heatmap layer
    HeatMap(heat_data, radius=12, blur=15, min_opacity=0.4).add_to(job_map)

    # Display the map in Streamlit
    st_folium(job_map, width=800, height=600)

# Display the map
if df is not None:
    create_heatmap(df)
else:
    st.warning("Could not load job location data.")
