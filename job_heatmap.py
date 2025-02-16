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
import threading
import schedule

# Set page config
st.set_page_config(
    page_title="Job Location Heatmap",
    page_icon="🗺️",
    layout="wide"
)

# Title and description
st.title("Job Location Heatmap - Australia")
st.markdown("This map shows the distribution of job postings across Australia.")

# Initialize session state variables
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.datetime.now()
if 'location_data' not in st.session_state:
    st.session_state.location_data = []
if 'total_jobs' not in st.session_state:
    st.session_state.total_jobs = 0
if 'unique_locations' not in st.session_state:
    st.session_state.unique_locations = 0
if 'success_count' not in st.session_state:
    st.session_state.success_count = 0
if 'background_refresh_started' not in st.session_state:
    st.session_state.background_refresh_started = False

# Show last update time
st.sidebar.info(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.info("Data automatically updates every 4 hours")

# Cache file for geocoding results
CACHE_FILE = "geocode_cache.json"

# Load geocoding cache if it exists
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save geocoding cache
def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

# Define Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

def fetch_and_process_data():
    # Google Sheets CSV URL
    sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"
    
    # Load dataset from Google Sheets
    df = pd.read_csv(sheet_url)
    
    # Keep all job locations (don't remove duplicates)
    locations = df["location"].dropna().tolist()
    
    # Log statistics
    total_jobs = len(df['location'].dropna())
    unique_locations = len(set(locations))
    
    # Initialize geocoder and load cache
    geolocator = Nominatim(user_agent="job_location_geocoder")
    geocode_cache = load_cache()
    
    # Function to get latitude & longitude within Australia's bounds
    def get_lat_lon(location):
        if location in geocode_cache:
            return geocode_cache[location]
        
        # Append "Victoria, Australia" if "VIC" is in location
        formatted_loc = location.replace("VIC", "").strip() + ", Victoria, Australia" if "VIC" in location else location + ", Australia"
        
        for attempt in range(3):  # Retry up to 3 times
            try:
                time.sleep(1)  # Delay to prevent rate limiting
                geo = geolocator.geocode(formatted_loc)
                if geo:
                    lat, lon = geo.latitude, geo.longitude
                    # Check if location is within Australia
                    if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                        coords = (lat, lon)
                        geocode_cache[location] = coords
                        return coords
                    else:
                        return None
            except GeocoderTimedOut:
                continue
            except Exception as e:
                print(f"Error geocoding {location}: {e}")
                break
        
        return None
    
    # Convert locations to lat/lon, filtering out invalid ones
    location_data = []
    failed_locations = []
    
    for loc in locations:
        coords = get_lat_lon(loc)
        if coords:
            location_data.append(coords)
        else:
            failed_locations.append(loc)
    
    # Save updated cache
    save_cache(geocode_cache)
    
    # Update session state
    st.session_state.location_data = location_data
    st.session_state.total_jobs = total_jobs
    st.session_state.unique_locations = unique_locations
    st.session_state.success_count = len(location_data)
    st.session_state.last_update = datetime.datetime.now()
    
    # Write to a status file that the app was updated
    with open("last_update.txt", "w") as f:
        f.write(st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S'))
    
    print(f"Data updated at {st.session_state.last_update}")

def background_job():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Set up the background refresh job
def setup_background_refresh():
    if not st.session_state.background_refresh_started:
        # Schedule the job to run every 4 hours
        schedule.every(4).hours.do(fetch_and_process_data)
        
        # Start the background thread
        thread = threading.Thread(target=background_job, daemon=True)
        thread.start()
        
        st.session_state.background_refresh_started = True
        print("Background refresh started")

# Initial data fetch if needed
if len(st.session_state.location_data) == 0:
    with st.spinner("Fetching initial data..."):
        fetch_and_process_data()

# Set up the background refresh
setup_background_refresh()

# Display statistics
col1, col2, col3 = st.columns(3)
col1.metric("Total Job Postings", st.session_state.total_jobs)
col2.metric("Unique Locations", st.session_state.unique_locations)
col3.metric("Geocoded Locations", st.session_state.success_count)

# Create a map centered on Australia
map_center = [-25.2744, 133.7751]
job_map = folium.Map(location=map_center, zoom_start=5)

# Add HeatMap if we have data
if st.session_state.location_data:
    HeatMap(st.session_state.location_data, radius=15, blur=10).add_to(job_map)

# Display the map
st_folium(job_map, width=1200, height=600)

# Add footer
st.markdown("---")
st.markdown("© 2025 - Job Location Heatmap")

# Add button to force refresh
if st.button("Force Refresh Data"):
    with st.spinner("Refreshing data..."):
        fetch_and_process_data()
    st.experimental_rerun()
