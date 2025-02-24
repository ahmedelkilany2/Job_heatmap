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

# Display Title
st.title("Jora Job Scraping Analysis - Australia 📊")

# Google Sheets URL (Must be in CSV format & Public)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=14400)  # Cache data for 4 hours
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

    # Filter Locations in Australia
    df = df[df["location"].str.contains("Australia", case=False, na=False)].copy()

    # Initialize Geocoder
    geolocator = Nominatim(user_agent="job_heatmap")

    @st.cache_data(ttl=14400)  # Cache geocoded locations for 4 hours
    def geocode_location(location):
        """Convert location names to latitude & longitude."""
        try:
            loc = geolocator.geocode(location, timeout=10, country_codes="au")
            if loc:
                return pd.Series([loc.latitude, loc.longitude])
        except GeocoderTimedOut:
            time.sleep(1)  # Wait and retry
        return pd.Series([None, None])

    # Apply geocoding and expand into 'lat' & 'lon' columns
    df[["lat", "lon"]] = df["location"].apply(geocode_location)

    # Remove failed geocodes
    df = df.dropna(subset=["lat", "lon"])

    # Display Key Stats
    total_locations = len(df)
    unique_locations = df["location"].nunique()
    successfully_geocoded = len(df.dropna(subset=["lat", "lon"]))

    col1, col2, col3 = st.columns(3)
    col1.metric("📍 Total Job Locations", total_locations)
    col2.metric("📍 Unique Locations", unique_locations)
    col3.metric("✅ Successfully Geocoded", successfully_geocoded)

    # Create Map
    st.subheader("📍 Job Posting Density Heatmap (Australia)")
    m = folium.Map(location=[-25.2744, 133.7751], zoom_start=4)  # Centered in Australia

    # Add Heatmap
    heat_data = df[["lat", "lon"]].dropna().values.tolist()
    HeatMap(heat_data, radius=15, blur=10).add_to(m)

    # Display Map
    folium_static(m)
