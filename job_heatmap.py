import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# Google Sheets CSV Export URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/export?format=csv"

# Load data
df = pd.read_csv(SHEET_URL)

# Ensure the dataset has latitude and longitude columns
if "latitude" not in df.columns or "longitude" not in df.columns:
    st.error("The dataset must contain 'latitude' and 'longitude' columns.")
    st.stop()

# Remove duplicates
heat_data = df[['latitude', 'longitude']].drop_duplicates().values.tolist()

# Create a heatmap
st.title("Heat Map of Locations")
map_ = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], zoom_start=10)
HeatMap(heat_data).add_to(map_)

# Display the map
st_folium(map_, width=700, height=500)
