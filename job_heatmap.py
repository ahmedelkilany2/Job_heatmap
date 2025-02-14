import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import time

# Google Sheets CSV URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"

# Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Initialize geocoder
geolocator = Nominatim(user_agent="python-job-heatmap-au")

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
    if not location:
        return None

    # Format location string
    formatted_loc = f"{location.strip()}, Australia"

    try:
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        geo = geolocator.geocode(formatted_loc)
        if geo:
            lat, lon = geo.latitude, geo.longitude
            if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                return lat, lon
    except Exception as e:
        st.sidebar.error(f"Error geocoding {location}: {str(e)}")
    
    return None

def get_location_data():
    """Converts job locations to latitude & longitude."""
    locations = fetch_data()
    if not locations:
        return []

    valid_locations = []
    progress_bar = st.progress(0)
    
    for idx, loc in enumerate(locations):
        result = geocode_location(loc)
        if result:
            valid_locations.append(result)
        progress_bar.progress((idx + 1) / len(locations))
        
    progress_bar.empty()
    return valid_locations

def main():
    st.title("🔍 Job Heatmap Analytics (Australia)")
    st.write("Real-time job location heatmap from Google Sheets.")

    try:
        with st.spinner("Loading location data..."):
            location_data = get_location_data()

        if location_data:
            map_center = [-25.2744, 133.7751]  # Center of Australia
            job_map = folium.Map(location=map_center, zoom_start=5)
            HeatMap(location_data, radius=15, blur=10).add_to(job_map)

            st_folium(job_map, width=800, height=500)
            
            st.write(f"✅ **Showing {len(location_data)} valid locations**")
            st.write("🔄 **Auto-refreshing every 4 hours** ⏳")
        else:
            st.warning("⚠ No valid job locations found. Please check the data source.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
