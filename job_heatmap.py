import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
from streamlit_folium import folium_static

# Title for Streamlit app
st.title("Job Heatmap in Australia")

# Google Sheets CSV URL for "Sheet1" (with gid=0)
sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"

# Load dataset from Google Sheets
df = pd.read_csv(sheet_url)

# Display the raw data (optional)
st.write("### Job Locations Dataset", df.head())

# Keep all job locations (don't remove duplicates)
locations = df["location"].dropna().tolist()

# Initialize geocoder
geolocator = Nominatim(user_agent="job_location_geocoder")
geocode_cache = {}

# Define Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Function to get latitude & longitude within Australia's bounds
def get_lat_lon(location):
    if location in geocode_cache:
        return geocode_cache[location]

    formatted_loc = location + ", Australia"
    
    for attempt in range(5):  # Retry up to 5 times
        try:
            time.sleep(2)  # Prevent rate limiting
            geo = geolocator.geocode(formatted_loc)
            if geo:
                lat, lon = geo.latitude, geo.longitude
                if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                    coords = (lat, lon)
                    geocode_cache[location] = coords
                    return coords
                else:
                    return None
        except GeocoderTimedOut:
            continue
    return None

# Convert locations to lat/lon, filtering out invalid ones
with st.spinner("Geocoding locations..."):
    location_data = [get_lat_lon(loc) for loc in locations if get_lat_lon(loc) is not None]

# Display analytics
st.write(f"Total job postings: {len(df['location'].dropna())}")
st.write(f"Successfully geocoded locations: {len(location_data)}")

# Create a map centered on Australia
map_center = [-25.2744, 133.7751]
job_map = folium.Map(location=map_center, zoom_start=5)

# Add HeatMap
HeatMap(location_data, radius=15, blur=10).add_to(job_map)

# Display map in Streamlit
st.write("### Job Heatmap")
folium_static(job_map)
