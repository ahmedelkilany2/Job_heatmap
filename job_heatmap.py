import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import datetime

# Google Sheets CSV URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/export?format=csv"

# Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Initialize geocoder
geolocator = Nominatim(user_agent="job_location_geocoder")

@st.cache_data(ttl=14_400)  # Cache for 4 hours
def fetch_data():
    """Fetch job locations from Google Sheets."""
    try:
        df = pd.read_csv(SHEET_URL)
        return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

@st.cache_data(ttl=14_400)
def geocode_location(location):
    """Geocodes a location and ensures it falls within Australia."""
    if "VIC" in location:
        formatted_loc = location.replace("VIC", "").strip() + ", Victoria, Australia"
    else:
        formatted_loc = location + ", Australia"

    for attempt in range(3):  # Retry up to 3 times
        try:
            time.sleep(1)  # Prevent API rate limiting
            geo = geolocator.geocode(formatted_loc)
            if geo:
                lat, lon = geo.latitude, geo.longitude
                if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                    return lat, lon
        except GeocoderTimedOut:
            continue

    return None  # Return None if geocoding fails

def get_location_data():
    """Converts job locations to latitude & longitude."""
    locations = fetch_data()
    return [geocode_location(loc) for loc in locations if geocode_location(loc) is not None]

# Auto-refresh logic using session state
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.datetime.now()

time_since_refresh = (datetime.datetime.now() - st.session_state.last_refresh).total_seconds()
if time_since_refresh > 14_400:  # 4 hours = 14,400 seconds
    st.session_state.last_refresh = datetime.datetime.now()
    st.experimental_rerun()

# Streamlit UI
st.title("🔍 Job Heatmap Analytics (Australia)")
st.write("Real-time job location heatmap from Google Sheets.")

# Generate heatmap
location_data = get_location_data()

if location_data:
    map_center = [-25.2744, 133.7751]
    job_map = folium.Map(location=map_center, zoom_start=5)
    HeatMap(location_data, radius=15, blur=10).add_to(job_map)

    st_folium(job_map, width=800, height=500)

    st.write("✅ **Auto-refreshing every 4 hours** ⏳")
else:
    st.warning("⚠ No valid job locations found. Please check the data source.")
