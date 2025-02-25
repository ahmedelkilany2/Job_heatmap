import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

# Google Sheets URL (must be in CSV format)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

# Initialize geolocator
geolocator = Nominatim(user_agent="job_heatmap")

def load_data():
    """Load job location data from Google Sheets."""
    try:
        df = pd.read_csv(GOOGLE_SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()  # Normalize column names
        if "location" not in df.columns:
            st.error("⚠️ 'location' column is missing in the dataset!")
            return None
        return df.dropna(subset=["location"])  # Remove empty locations
    except Exception as e:
        st.error(f"⚠️ Error loading data: {e}")
        return None

def geocode_location(location):
    """Convert location names to latitude & longitude, handling errors."""
    try:
        loc = geolocator.geocode(location, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
    except GeocoderTimedOut:
        time.sleep(1)  # Retry after delay
    return None, None

def main():
    """Main function for the Jora job heatmap dashboard."""
    st.subheader("📍 Jora Job Posting Location Heatmap")

    df = load_data()
    if df is None:
        return

    st.success("✅ Data Loaded Successfully!")

    # Add button to trigger geocoding (avoids unnecessary refresh)
    if st.button("🔍 Process Locations"):
        with st.spinner("🔍 Geocoding locations... This may take some time."):
            df["lat"], df["lon"] = zip(*df["location"].apply(geocode_location))
        
        # Remove missing coordinates
        df = df.dropna(subset=["lat", "lon"])

        # Show summary
        total_locations = len(df)
        unique_locations = df["location"].nunique()
        st.success(f"✅ Geocoded {unique_locations} unique locations from {total_locations} job postings!")

        # Create map centered on Victoria, Australia
        st.subheader("📍 Job Posting Density Heatmap")
        m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)

        # Add Heatmap (including duplicate locations for better intensity)
        from folium.plugins import HeatMap
        heat_data = df[["lat", "lon"]].values.tolist()
        HeatMap(heat_data, radius=15, blur=10).add_to(m)

        # Display map
        folium_static(m)

if __name__ == "__main__":
    main()
