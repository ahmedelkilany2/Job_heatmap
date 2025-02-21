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

# Prevent Streamlit from sleeping
st.set_page_config(
    page_title="Job Location Heatmap",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add this line to keep the session active
if 'last_ping' not in st.session_state:
    st.session_state.last_ping = datetime.datetime.now()

# Ping every 5 minutes to keep the session alive
def keep_alive():
    now = datetime.datetime.now()
    if 'last_ping' not in st.session_state or (now - st.session_state.last_ping).seconds > 300:
        st.session_state.last_ping = now
        st.experimental_rerun()

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

# Load geocoding cache if it exists
def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.warning(f"Error loading cache: {e}")
    return {}

# Save geocoding cache
def save_cache(cache):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        st.warning(f"Error saving cache: {e}")

# Define Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

@st.cache_data(ttl=14400)  # Cache for 4 hours
def fetch_and_process_data():
    try:
        # Google Sheets CSV URL
        sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"
        
        # Load dataset from Google Sheets with error handling
        try:
            df = pd.read_csv(sheet_url)
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return None
        
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
                            save_cache(geocode_cache)  # Save cache after each successful geocoding
                            return coords
                except GeocoderTimedOut:
                    time.sleep(2)  # Longer delay on timeout
                    continue
                except Exception as e:
                    st.warning(f"Error geocoding {location}: {e}")
                    return None
            return None
        
        # Convert locations to lat/lon with progress bar
        location_data = []
        failed_locations = []
        
        progress_bar = st.progress(0)
        for idx, loc in enumerate(locations):
            coords = get_lat_lon(loc)
            if coords:
                location_data.append(coords)
            else:
                failed_locations.append(loc)
            progress_bar.progress((idx + 1) / len(locations))
        
        progress_bar.empty()
        
        # Update session state
        st.session_state.last_update = datetime.datetime.now()
        
        return {
            'location_data': location_data,
            'total_jobs': total_jobs,
            'unique_locations': unique_locations,
            'failed_count': len(failed_locations),
            'success_count': len(location_data)
        }
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None

# Keep the session alive
keep_alive()

# Get the data
data = fetch_and_process_data()

if data:
    # Display statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Job Postings", data['total_jobs'])
    col2.metric("Unique Locations", data['unique_locations'])
    col3.metric("Geocoded Locations", data['success_count'])

    # Create a map centered on Australia
    map_center = [-25.2744, 133.7751]
    job_map = folium.Map(location=map_center, zoom_start=5)

    # Add HeatMap
    if data['location_data']:
        HeatMap(data['location_data'], radius=15, blur=10).add_to(job_map)
        
        # Display the map
        st_folium(job_map, width=1200, height=600)
    else:
        st.warning("No location data available to display on the map.")
else:
    st.error("Failed to fetch or process data. Please try again later.")

# Add footer
st.markdown("---")
st.markdown("© 2025 - Job Location Heatmap")

# Add button to force refresh
if st.button("Force Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()
