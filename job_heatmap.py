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
from geopy.extra.rate_limiter import RateLimiter
import concurrent.futures
import requests.exceptions

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

def geocode_location(geolocator, location, geocode_cache):
    """Geocode a single location with better error handling"""
    if location in geocode_cache:
        return location, geocode_cache[location]
    
    formatted_loc = location.replace("VIC", "").strip() + ", Victoria, Australia" if "VIC" in location else location + ", Australia"
    
    try:
        geo = geolocator(formatted_loc, timeout=5)
        if geo:
            lat, lon = geo.latitude, geo.longitude
            if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                coords = (lat, lon)
                return location, coords
    except (GeocoderTimedOut, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        st.warning(f"Timeout error for {location}: {str(e)}")
    except Exception as e:
        st.warning(f"Error geocoding {location}: {str(e)}")
    
    return location, None

@st.cache_data(ttl=14400)  # Cache for 4 hours
def fetch_and_process_data():
    try:
        # Google Sheets CSV URL
        sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"
        
        # Load dataset from Google Sheets
        try:
            df = pd.read_csv(sheet_url)
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return None
        
        # Get unique locations to reduce API calls
        locations = df["location"].dropna().unique().tolist()
        total_jobs = len(df['location'].dropna())
        unique_locations = len(locations)
        
        # Initialize geocoder with rate limiting
        geolocator = Nominatim(user_agent="job_location_geocoder_batch")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2)
        
        # Load cache
        geocode_cache = load_cache()
        
        # Process locations in batches
        batch_size = 50
        location_data = []
        failed_locations = []
        processed_count = 0
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process locations in batches
        for i in range(0, len(locations), batch_size):
            batch = locations[i:i + batch_size]
            status_text.text(f"Processing batch {i//batch_size + 1} of {(len(locations) + batch_size - 1)//batch_size}")
            
            # Process batch with parallel execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_location = {
                    executor.submit(geocode_location, geocode, loc, geocode_cache): loc 
                    for loc in batch
                }
                
                for future in concurrent.futures.as_completed(future_to_location):
                    location, coords = future.result()
                    if coords:
                        location_data.append(coords)
                        geocode_cache[location] = coords
                    else:
                        failed_locations.append(location)
                    
                    processed_count += 1
                    progress_bar.progress(processed_count / len(locations))
            
            # Save cache after each batch
            save_cache(geocode_cache)
            
            # Add a small delay between batches
            time.sleep(2)
        
        progress_bar.empty()
        status_text.empty()
        
        # Update session state
        st.session_state.last_update = datetime.datetime.now()
        
        # Count actual job positions (not just unique locations)
        final_locations = []
        for _, row in df.iterrows():
            if row['location'] in geocode_cache:
                final_locations.append(geocode_cache[row['location']])
        
        return {
            'location_data': final_locations,
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
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Job Postings", data['total_jobs'])
    col2.metric("Unique Locations", data['unique_locations'])
    col3.metric("Successfully Geocoded", data['success_count'])
    col4.metric("Failed Geocoding", data['failed_count'])

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
