import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from concurrent.futures import ThreadPoolExecutor
import time
from folium.plugins import HeatMap

# Google Sheets URL (must be in CSV format)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

# Cache Data (4 hours)
@st.cache_data(ttl=14400)
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

# Cache Geocoding Results
@st.cache_data(ttl=14400)
def geocode_location(location):
    """Convert location names to latitude & longitude."""
    geolocator = Nominatim(user_agent="job_heatmap")
    try:
        loc = geolocator.geocode(location, timeout=10)
        if loc:
            return (loc.latitude, loc.longitude)
    except GeocoderTimedOut:
        time.sleep(1)  # Retry if timeout
    return (None, None)

def batch_geocode(locations):
    """Geocode multiple locations in parallel."""
    unique_locations = list(set(locations))  # Remove exact duplicates to optimize calls
    geocoded_results = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(geocode_location, unique_locations)

    for loc, coords in zip(unique_locations, results):
        geocoded_results[loc] = coords

    return geocoded_results

def main():
    """Main function to run the job heatmap dashboard."""
    st.title("Jora Job Posting Location Analysis")
    
    # Load data
    df = load_data()
    
    if df is not None:
        st.success("✅ Data Loaded Successfully!")
        
        # Remove empty locations
        df = df.dropna(subset=["location"])
        total_locations = len(df)

        # Batch Geocode Locations
        st.subheader("🔄 Geocoding Locations... Please wait.")
        geocoded_dict = batch_geocode(df["location"])
        
        # Map geocoded results back to DataFrame
        df["lat"], df["lon"] = zip(*df["location"].map(lambda x: geocoded_dict.get(x, (None, None))))
        
        # Remove rows with missing coordinates
        df = df.dropna(subset=["lat", "lon"])
        success_count = len(df)
        
        # Show Summary
        st.subheader("📊 Geocoding Summary")
        st.write(f"✅ Successfully geocoded **{success_count}** out of **{total_locations}** locations.")
        
        # Create Map
        st.subheader("📍 Job Posting Density Heatmap")
        m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)  # Default: Victoria, Australia
        
        # Include Duplicates by Weighting Heatmap
        location_counts = df.groupby(["lat", "lon"]).size().reset_index(name="count")
        heat_data = location_counts[["lat", "lon", "count"]].values.tolist()
        
        # Add Heatmap
        HeatMap(heat_data, radius=15, blur=10).add_to(m)
        
        # Display Map
        folium_static(m)
    else:
        st.error("⚠️ No data available! Please check your Google Sheet connection.")

if __name__ == "__main__":
    main()
