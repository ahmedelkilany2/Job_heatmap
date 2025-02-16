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
LAST_UPDATE_FILE = "last_update.txt"

# Check if we need to refresh based on the last update file
def check_needs_refresh():
    if os.path.exists(LAST_UPDATE_FILE):
        try:
            with open(LAST_UPDATE_FILE, "r") as f:
                last_update_str = f.read().strip()
                last_update = datetime.datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
                time_since_update = datetime.datetime.now() - last_update
                # If it's been more than 4 hours since last update
                if time_since_update > datetime.timedelta(hours=4):
                    return True
        except Exception as e:
            print(f"Error reading last update file: {e}")
            return True
    else:
        # No update file exists, so we should refresh
        return True
    return False

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
    
    try:
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
            
            # Just return None for now - we'll geocode unique locations separately
            return None
        
        # First pass: use cache and identify unique locations that need geocoding
        location_data = []
        unique_locations_to_geocode = set()
        location_to_coords = {}
        
        for loc in locations:
            coords = get_lat_lon(loc)
            if coords:
                location_data.append(coords)
                location_to_coords[loc] = coords
            else:
                unique_locations_to_geocode.add(loc)
        
        # Progress bar for geocoding
        if unique_locations_to_geocode:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Geocode only unique locations that aren't in cache
            total_to_geocode = len(unique_locations_to_geocode)
            for i, loc in enumerate(unique_locations_to_geocode):
                # Update progress
                progress = int((i / total_to_geocode) * 100)
                progress_bar.progress(progress)
                status_text.text(f"Geocoding location {i+1} of {total_to_geocode}: {loc}")
                
                # Append "Victoria, Australia" if "VIC" is in location
                formatted_loc = loc.replace("VIC", "").strip() + ", Victoria, Australia" if "VIC" in loc else loc + ", Australia"
                
                try:
                    time.sleep(1)  # Respect rate limits
                    geo = geolocator.geocode(formatted_loc)
                    if geo:
                        lat, lon = geo.latitude, geo.longitude
                        # Check if location is within Australia
                        if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                            coords = (lat, lon)
                            geocode_cache[loc] = coords
                            location_to_coords[loc] = coords
                except Exception as e:
                    print(f"Error geocoding {loc}: {e}")
            
            # Clean up progress elements
            progress_bar.empty()
            status_text.empty()
            
            # Save updated cache after all geocoding is done
            save_cache(geocode_cache)
        
        # Second pass: build final location_data using the cached and newly geocoded coordinates
        location_data = []
        for loc in locations:
            if loc in location_to_coords:
                location_data.append(location_to_coords[loc])
        
        # Update session state
        st.session_state.location_data = location_data
        st.session_state.total_jobs = total_jobs
        st.session_state.unique_locations = unique_locations
        st.session_state.success_count = len(location_data)
        st.session_state.last_update = datetime.datetime.now()
        
        # Write to a status file that the app was updated
        with open(LAST_UPDATE_FILE, "w") as f:
            f.write(st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S'))
        
        print(f"Data updated at {st.session_state.last_update}")
        
    except Exception as e:
        print(f"Error in data refresh: {e}")
        st.error(f"Error refreshing data: {e}")

def background_job():
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

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

# Load data from last update file if it exists
def load_last_update():
    if os.path.exists(LAST_UPDATE_FILE):
        try:
            with open(LAST_UPDATE_FILE, "r") as f:
                last_update_str = f.read().strip()
                st.session_state.last_update = datetime.datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"Error loading last update: {e}")

# Initial data fetch if needed
if len(st.session_state.location_data) == 0 or check_needs_refresh():
    with st.spinner("Updating data..."):
        # First try to load the last update time
        load_last_update()
        # Then fetch fresh data if needed
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
else:
    st.warning("No location data available to display on the map.")

# Display the map
st_folium(job_map, width=1200, height=600)

# Add footer
st.markdown("---")
st.markdown("© 2025 - Job Location Heatmap")

# Add button to force refresh for convenience
if st.button("Force Refresh Data"):
    with st.spinner("Refreshing data..."):
        fetch_and_process_data()
    st.experimental_rerun()
