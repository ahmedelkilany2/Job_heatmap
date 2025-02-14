import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# GitHub-hosted CSV with precomputed lat/lon
GITHUB_CSV_URL = "https://raw.githubusercontent.com/your-username/your-repo/main/job_locations.csv"

@st.cache_data  # Cache data to improve performance
def fetch_data():
    """Fetches job location data (latitude & longitude) from GitHub."""
    df = pd.read_csv(GITHUB_CSV_URL)
    return df[["latitude", "longitude"]].dropna().values.tolist()

# Streamlit UI
st.title("🔍 Job Heatmap Analytics (Australia)")
st.write("Real-time job location heatmap from GitHub.")

# Load job locations
location_data = fetch_data()

if location_data:
    # Create a Folium map centered on Australia
    map_center = [-25.2744, 133.7751]
    job_map = folium.Map(location=map_center, zoom_start=5)

    # Add HeatMap layer
    HeatMap(location_data, radius=15, blur=10).add_to(job_map)

    # Render the map in Streamlit
    st_folium(job_map, width=800, height=500)

    # Auto-refresh every 30 seconds
    st.write("🔄 **Auto-refreshing every 30 seconds** to get the latest data.")
    st.experimental_rerun()

else:
    st.warning("⚠ No valid job locations found. Please check the data source.")
