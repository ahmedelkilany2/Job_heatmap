import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import urllib.error
import time

# Google Sheets CSV URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"

# Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Initialize geocoder with caching
geolocator = Nominatim(user_agent="job_location_geocoder")

@st.cache_data  # Cache function to avoid redundant API calls
def fetch_data():
    """Fetches latest job locations from GitHub CSV with error handling."""
    try:
        df = pd.read_csv(GITHUB_CSV_URL)
        return df["location"].dropna().tolist()
    except urllib.error.HTTPError as e:
        st.error(f"⚠️ HTTP Error: {e.code}. Check your GitHub link or file permissions.")
        return []
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {str(e)}")
        return []

@st.cache_data
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
            continue  # Retry on timeout

    return None  # Return None if geocoding fails

def get_location_data():
    """Processes job locations and converts them to latitude & longitude."""
    locations = fetch_data()
    geocoded_data = [geocode_location(loc) for loc in locations if geocode_location(loc) is not None]
    return geocoded_data

# Streamlit UI
st.title("🔍 Job Heatmap Analytics (Australia)")
st.write("Real-time job location heatmap from GitHub CSV.")

# Generate heatmap
location_data = get_location_data()

if location_data:
    # Create a Folium map centered on Australia
    map_center = [-25.2744, 133.7751]
    job_map = folium.Map(location=map_center, zoom_start=5)

    # Add HeatMap layer
    HeatMap(location_data, radius=15, blur=10).add_to(job_map)

    # Render the map in Streamlit
    st_folium(job_map, width=800, height=500)

    # Auto-refresh every 30 seconds
    st.write("🔄 **Auto-refreshing every 30 seconds** to get the latest data.")
    st.experimental_rerun()
else:
    st.warning("⚠ No valid job locations found. Please check the data source.")
