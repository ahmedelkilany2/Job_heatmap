import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

# Google Sheets URL (must be in CSV format)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=14400)  # Cache data for 4 hours (14400 seconds)
def load_data():
    """Load job location data from Google Sheets."""
    try:
        df = pd.read_csv(GOOGLE_SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()  # Normalize column names
        if "location" not in df.columns:
            return None
        return df
    except Exception as e:
        return None

@st.cache_data(ttl=14400)  # Cache geocoded locations for 4 hours
def geocode_location(location):
    """Convert location names to latitude & longitude."""
    geolocator = Nominatim(user_agent="job_heatmap")
    try:
        loc = geolocator.geocode(location, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
    except GeocoderTimedOut:
        time.sleep(1)  # Wait and retry
    return None, None

def main():
    """Main function to run the Jora job heatmap dashboard."""
    st.subheader("Jora Job Posting Location Analysis")
    
    # Load data
    df = load_data()
    
    if df is not None:
        st.success("✅ Data Loaded Successfully!")
        
        # Apply geocoding
        df["lat"], df["lon"] = zip(*df["location"].apply(geocode_location))
        df = df.dropna(subset=["lat", "lon"])  # Remove rows with missing coordinates
        
        # Create Map
        st.subheader("📍 Job Posting Density Heatmap")
        m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)  # Default: Victoria, Australia
        
        # Add Heatmap
        heat_data = df[["lat", "lon"]].values.tolist()
        folium.plugins.HeatMap(heat_data, radius=15, blur=10).add_to(m)
        
        # Display Map
        folium_static(m)
    else:
        st.error("⚠️ No data available! Please check your Google Sheet connection.")
