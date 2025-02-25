import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import os

# Google Sheets URL (must be in CSV format)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

# Google Maps API Key (Replace with your own key)
API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"  # Replace with your API key
if API_KEY == "YOUR_GOOGLE_MAPS_API_KEY":
    st.error("⚠️ Please set your Google Maps API Key!")
    st.stop()

gmaps = googlemaps.Client(key=API_KEY)

# File to store cached geocoded locations
CACHE_FILE = "geocoded_locations.csv"

@st.cache_data(ttl=14400)  # Cache for 4 hours
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

def load_cached_geocodes():
    """Load cached geocoded locations."""
    if os.path.exists(CACHE_FILE):
        return pd.read_csv(CACHE_FILE).set_index("location").to_dict(orient="index")
    return {}

def save_cached_geocodes(cache):
    """Save geocoded locations."""
    pd.DataFrame.from_dict(cache, orient="index").reset_index().rename(
        columns={"index": "location"}
    ).to_csv(CACHE_FILE, index=False)

def geocode_location(location, cache):
    """Convert location names to latitude & longitude using Google Maps API."""
    if location in cache:
        return cache[location]["lat"], cache[location]["lon"]

    try:
        geocode_result = gmaps.geocode(location)
        if geocode_result:
            lat = geocode_result[0]["geometry"]["location"]["lat"]
            lon = geocode_result[0]["geometry"]["location"]["lng"]
            cache[location] = {"lat": lat, "lon": lon}  # Store in cache
            return lat, lon
    except Exception as e:
        st.warning(f"⚠️ Geocoding failed for {location}: {e}")
        return None, None

    return None, None

def main():
    """Main function for the job location heatmap."""
    st.subheader("📍 Jora Job Posting Location Heatmap")

    df = load_data()
    if df is None:
        return

    cached_geocodes = load_cached_geocodes()

    # Geocode all locations
    st.info("🔍 Geocoding job locations... This may take a few seconds.")
    df["lat"], df["lon"] = zip(*df["location"].apply(lambda loc: geocode_location(loc, cached_geocodes)))

    # Save updated geocodes
    save_cached_geocodes(cached_geocodes)

    # Remove invalid coordinates
    df = df.dropna(subset=["lat", "lon"])

    total_locations = len(df)
    unique_locations = df["location"].nunique()
    st.success(f"✅ Geocoded {unique_locations} unique locations out of {total_locations} job postings!")

    # Create map
    st.subheader("📍 Job Posting Density Heatmap")
    m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)  # Default to Victoria, Australia

    # Add heatmap layer
    from folium.plugins import HeatMap
    heat_data = df[["lat", "lon"]].values.tolist()
    HeatMap(heat_data, radius=15, blur=10).add_to(m)

    # Display map
    folium_static(m)

if __name__ == "__main__":
    main()
