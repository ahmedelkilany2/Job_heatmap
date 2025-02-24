import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from folium.plugins import HeatMap
from streamlit_autorefresh import st_autorefresh

# 🕒 Auto-refresh every 4 hours (14400 seconds)
st_autorefresh(interval=14400 * 1000, key="refresh")

# 📌 Google Sheets URL (CSV export link)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

# 🔄 Load Data
@st.cache_data(ttl=14400)  # Cache data for 4 hours
def load_data():
    df = pd.read_csv(GOOGLE_SHEET_URL)
    return df

# 📍 Get Latitude & Longitude
@st.cache_data
def get_lat_lon(location):
    geolocator = Nominatim(user_agent="job_locator")
    try:
        if location.lower() == "vic":
            location = "Victoria, Australia"
        loc = geolocator.geocode(location, timeout=10)
        return (loc.latitude, loc.longitude) if loc else (None, None)
    except GeocoderTimedOut:
        return (None, None)

# 🎯 Load & Process Data
st.title("🌍 Job Location Heatmap")
df = load_data()

if "Location" not in df.columns:
    st.error("⚠️ No 'Location' column found in the dataset!")
else:
    df["Coordinates"] = df["Location"].apply(get_lat_lon)
    df.dropna(subset=["Coordinates"], inplace=True)
    df[["Latitude", "Longitude"]] = pd.DataFrame(df["Coordinates"].tolist(), index=df.index)

    # 🗺️ Create Heatmap
    m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)  # Centered in Victoria, Australia
    HeatMap(df[["Latitude", "Longitude"]].values, radius=15).add_to(m)
    
    # 📌 Display Map
    folium_static(m)
