import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from folium.plugins import HeatMap
import time

# Streamlit Page Config
st.set_page_config(page_title="Jora Job Scraping Analysis - Australia 📊", layout="wide")

# Google Sheets URL (must be in CSV format)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=14400)  # Cache data for 4 hours (14400 seconds)
def load_data():
    """Load job location data from Google Sheets."""
    try:
        df = pd.read_csv(GOOGLE_SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()  # Normalize column names
        if "location" not in df.columns:
            st.error("⚠️ No 'location' column found in the dataset! Please check your Google Sheet.")
            return None
        return df
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None

df = load_data()

if df is not None:
    st.success("✅ Data Loaded Successfully!")

    # Initialize geocoder
    geolocator = Nominatim(user_agent="job_heatmap")

    @st.cache_data(ttl=14400)  # Cache geocoded locations for 4 hours
    def geocode_location(location):
        """Convert location names to latitude & longitude."""
        try:
            loc = geolocator.geocode(location, timeout=10)
            if loc:
                return loc.latitude, loc.longitude
        except GeocoderTimedOut:
            time.sleep(1)  # Wait and retry
        return None, None

    # Apply geocoding
    df["lat"], df["lon"] = zip(*df["location"].apply(geocode_location))
    df = df.dropna(subset=["lat", "lon"])  # Remove rows with missing coordinates

    # Create Map
    st.subheader("📍 Job Posting Density Heatmap")
    m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)  # Default: Victoria, Australia

    # Add Heatmap
    heat_data = df[["lat", "lon"]].values.tolist()
    HeatMap(heat_data, radius=15, blur=10).add_to(m)

    # Display Map
    folium_static(m)
