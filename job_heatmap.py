import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import streamlit as st
from streamlit_folium import st_folium
import datetime
import os
import json
from concurrent.futures import ThreadPoolExecutor

# Set page config
st.set_page_config(
    page_title="Job Location Heatmap",
    page_icon="🗺️",
    layout="wide"
)

st.title("Job Location Heatmap - Australia")
st.markdown("This map shows the distribution of job postings across Australia.")

if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.datetime.now()

st.sidebar.info(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.info("Data updates every 4 hours")

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

AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

def get_lat_lon(location, geolocator, cache):
    if location in cache:
        return cache[location]
    
    formatted_loc = f"{location}, Australia"
    if "VIC" in location:
        formatted_loc = f"{location.replace('VIC', '').strip()}, Victoria, Australia"
    
    for _ in range(3):  # Retry logic
        try:
            geo = geolocator.geocode(formatted_loc, timeout=5)
            if geo and AU_LAT_MIN <= geo.latitude <= AU_LAT_MAX and AU_LON_MIN <= geo.longitude <= AU_LON_MAX:
                cache[location] = (geo.latitude, geo.longitude)
                return cache[location]
        except GeocoderTimedOut:
            time.sleep(1)
    return None

@st.cache_data(ttl=14400)
def fetch_and_process_data():
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"
        df = pd.read_csv(sheet_url)
        locations = list(set(df["location"].dropna().tolist()))  # Use set to avoid duplicates early
        
        geolocator = Nominatim(user_agent="job_location_geocoder")
        geocode_cache = load_cache()
        
        location_data = []
        failed_locations = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda loc: get_lat_lon(loc, geolocator, geocode_cache), locations))
        
        for loc, coords in zip(locations, results):
            if coords:
                location_data.append(coords)
            else:
                failed_locations.append(loc)
        
        save_cache(geocode_cache)
        st.session_state.last_update = datetime.datetime.now()
        
        return {
            'location_data': location_data,
            'total_jobs': len(df),
            'unique_locations': len(locations),
            'failed_count': len(failed_locations),
            'success_count': len(location_data)
        }
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None

data = fetch_and_process_data()

if data:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Job Postings", data['total_jobs'])
    col2.metric("Unique Locations", data['unique_locations'])
    col3.metric("Geocoded Locations", data['success_count'])

    job_map = folium.Map(location=[-25.2744, 133.7751], zoom_start=5)
    if data['location_data']:
        HeatMap(data['location_data'], radius=15, blur=10).add_to(job_map)
        st_folium(job_map, width=1200, height=600)
    else:
        st.warning("No location data available to display on the map.")
else:
    st.error("Failed to fetch or process data. Please try again later.")

st.markdown("---")
st.markdown("© 2025 - Job Location Heatmap")

if st.button("Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()
