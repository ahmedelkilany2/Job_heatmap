import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from folium.plugins import HeatMap
import time
from streamlit_autorefresh import st_autorefresh
import streamlit_analytics as sa

# Reload page every 4 hours (14400 seconds)
time.sleep(14400)
st.experimental_rerun()

# Google Sheets URL (CSV export link)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQub8XWScX6fHhlfMzgIbm_Uh6oFX8eVafOsz3RGKzM5jT_ZlwNBlxlmQFYgF4oUAA/pub?output=csv"

# Load data
def load_data():
    df = pd.read_csv(GOOGLE_SHEET_URL)
    return df

def get_lat_lon(location):
    geolocator = Nominatim(user_agent="job_locator")
    try:
        if location.lower() == "vic":
            location = "Victoria, Australia"
        loc = geolocator.geocode(location, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
        else:
            return None, None
    except GeocoderTimedOut:
        return None, None

# Load data
st.title("Job Location Heatmap")
df = load_data()

# Check if 'Location' column exists
if 'Location' not in df.columns:
    st.error("No 'Location' column found in the dataset!")
else:
    df['Coordinates'] = df['Location'].apply(get_lat_lon)
    df.dropna(subset=['Coordinates'], inplace=True)
    df[['Latitude', 'Longitude']] = pd.DataFrame(df['Coordinates'].tolist(), index=df.index)

    # Create map
    m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)  # Centered in Victoria, Australia
    HeatMap(df[['Latitude', 'Longitude']].values, radius=15).add_to(m)
    
    # Display map
    folium_static(m)

sa.stop_tracking()
