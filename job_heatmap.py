import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import GoogleV3
import time
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
import datetime
from concurrent.futures import ThreadPoolExecutor

# Google Maps API Key (Replace with your own key)
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
geolocator = GoogleV3(api_key=GOOGLE_API_KEY)

# Set page config
st.set_page_config(page_title="Job Location Heatmap", page_icon="🗺️", layout="wide")
st.title("Job Location Heatmap - Australia")
st.markdown("This map shows the distribution of job postings across Australia.")

# Show last update time
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.datetime.now()
st.sidebar.info(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.info("Data updates every 4 hours")

# Database cache setup
def init_db():
    conn = sqlite3.connect("geocode_cache.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS geocode_cache (
            location TEXT PRIMARY KEY,
            latitude REAL,
            longitude REAL
        )
    """)
    conn.commit()
    conn.close()

def get_cached_coords(location):
    conn = sqlite3.connect("geocode_cache.db")
    c = conn.cursor()
    c.execute("SELECT latitude, longitude FROM geocode_cache WHERE location = ?", (location,))
    result = c.fetchone()
    conn.close()
    return result if result else None

def save_coords_to_cache(location, lat, lon):
    conn = sqlite3.connect("geocode_cache.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO geocode_cache (location, latitude, longitude) VALUES (?, ?, ?)", (location, lat, lon))
    conn.commit()
    conn.close()

# Fetch and process data
@st.cache_data(ttl=14400)  # Cache for 4 hours
def fetch_and_process_data():
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"
        df = pd.read_csv(sheet_url)
        locations = df["location"].dropna().tolist()
        
        total_jobs = len(df['location'].dropna())
        unique_locations = len(set(locations))
        
        def get_lat_lon(location, retries=5):
            cached = get_cached_coords(location)
            if cached:
                return location, cached
            
            for attempt in range(retries):
                try:
                    time.sleep(0.5)  # Reduce rate limit chances
                    geo = geolocator.geocode(location + ", Australia", timeout=10)
                    if geo:
                        lat, lon = geo.latitude, geo.longitude
                        save_coords_to_cache(location, lat, lon)
                        return location, (lat, lon)
                except Exception:
                    time.sleep(2 ** attempt)  # Exponential backoff
            return location, None
        
        location_data = []
        failed_locations = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = dict(executor.map(get_lat_lon, locations))
        
        for loc, coords in results.items():
            if coords:
                location_data.append(coords)
            else:
                failed_locations.append(loc)
        
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

# Run DB init
init_db()

# Get the data
data = fetch_and_process_data()
if data:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Job Postings", data['total_jobs'])
    col2.metric("Unique Locations", data['unique_locations'])
    col3.metric("Geocoded Locations", data['success_count'])

    map_center = [-25.2744, 133.7751]
    job_map = folium.Map(location=map_center, zoom_start=5)
    
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
