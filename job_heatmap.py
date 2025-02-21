import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from geopy.extra.rate_limiter import RateLimiter
import streamlit as st
from streamlit_folium import st_folium
import datetime
import os
import json
import numpy as np
import time

# Set page config
st.set_page_config(
    page_title="Job Location Heatmap",
    page_icon="🗺️",
    layout="wide"
)

# Title and description
st.title("Job Location Heatmap - Australia")
st.markdown("This map shows the distribution of job postings across Australia.")

# Show last update time
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.datetime.now()

st.sidebar.info(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.info("Data updates every 4 hours")

# Cache file for geocoding results
CACHE_FILE = "geocode_cache.json"

# Load and save cache functions
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

# Define Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

@st.cache_data(ttl=14400)  # Cache for 4 hours
def fetch_and_process_data():
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"
        df = pd.read_csv(sheet_url)

        # Keep only non-empty locations
        locations = df["location"].dropna().unique().tolist()

        total_jobs = len(df['location'].dropna())
        unique_locations = len(locations)

        # Load cached geocodes
        geocode_cache = load_cache()

        # Setup geolocator with rate limiter
        geolocator = Nominatim(user_agent="job_location_geocoder", timeout=10)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=3)

        # Function to get latitude & longitude
        def get_lat_lon(location, retries=3):
            """Attempts to geocode a location up to `retries` times before failing."""
            if location in geocode_cache:
                return geocode_cache[location]

            formatted_loc = f"{location}, Australia"
            for attempt in range(retries):
                try:
                    geo = geocode(formatted_loc)
                    if geo and AU_LAT_MIN <= geo.latitude <= AU_LAT_MAX and AU_LON_MIN <= geo.longitude <= AU_LON_MAX:
                        coords = (geo.latitude, geo.longitude)
                        geocode_cache[location] = coords
                        return coords
                except GeocoderTimedOut:
                    time.sleep(2)  # Wait before retrying
            return None

        # Process locations efficiently
        location_data = [get_lat_lon(loc) for loc in locations if loc]

        # Remove None values and convert to NumPy array
        location_data = np.array([coords for coords in location_data if coords])

        # Save cache after all geocoding attempts
        save_cache(geocode_cache)

        # Update session state
        st.session_state.last_update = datetime.datetime.now()

        return {
            'location_data': location_data.tolist(),
            'total_jobs': total_jobs,
            'unique_locations': unique_locations,
            'geocoded_count': len(location_data)
        }
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None

# Fetch and process data
data = fetch_and_process_data()

if data:
    # Display statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Job Postings", data['total_jobs'])
    col2.metric("Unique Locations", data['unique_locations'])
    col3.metric("Geocoded Locations", data['geocoded_count'])

    # Create a map centered on Australia
    job_map = folium.Map(location=[-25.2744, 133.7751], zoom_start=5)

    # Add HeatMap if valid location data exists
    if len(data['location_data']) > 0:
        HeatMap(data['location_data'], radius=12, blur=8).add_to(job_map)
        st_folium(job_map, width=1200, height=600)
    else:
        st.warning("No valid location data to display on the map.")
else:
    st.error("Failed to fetch or process data. Please try again later.")

# Add footer
st.markdown("---")
st.markdown("© 2025 - Job Location Heatmap")

# Force Refresh Button
if st.button("Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()
