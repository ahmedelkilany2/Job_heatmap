import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

# Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Initialize geocoder with longer timeout
geolocator = Nominatim(user_agent="python-job-heatmap-au", timeout=10)

@st.cache_data(ttl=14_400)  # Cache for 4 hours
def fetch_data(file_path):
    """Fetch job locations from uploaded CSV file."""
    try:
        df = pd.read_csv(file_path)
        locations = df['location'].dropna().tolist()
        return locations
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

@st.cache_data(ttl=14_400)
def geocode_location(location):
    """Geocodes a location and ensures it falls within Australia."""
    if not location:
        return None

    formatted_loc = f"{location.strip()}, Australia"

    try:
        time.sleep(1)  # Delay to prevent rate limiting
        geo = geolocator.geocode(formatted_loc, timeout=10)
        if geo:
            lat, lon = geo.latitude, geo.longitude
            if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                return lat, lon
    except GeocoderTimedOut:
        st.sidebar.warning(f"Geocoder timeout for: {location}")
    except Exception as e:
        st.sidebar.error(f"Error geocoding {location}: {str(e)}")

    return None

@st.cache_data(ttl=14_400)
def get_location_data(file_path):
    """Converts job locations to latitude & longitude with caching."""
    locations = fetch_data(file_path)
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
    st.write("Upload a CSV file containing job locations to generate a heatmap.")

    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            with st.spinner("Loading location data..."):
                location_data = get_location_data(uploaded_file)

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
