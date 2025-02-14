import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time
import datetime
from typing import Optional, Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets CSV URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"

# Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Initialize geocoder with a more specific user agent
geolocator = Nominatim(user_agent="python-job-heatmap-au")

@st.cache_data(ttl=14_400)  # Cache for 4 hours
def fetch_data() -> List[str]:
    """Fetch job locations from Google Sheets."""
    try:
        df = pd.read_csv(SHEET_URL)
        return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        st.error("Unable to fetch data from Google Sheets. Please check the URL and try again.")
        return []

@st.cache_data(ttl=14_400)
def geocode_location(location: str) -> Optional[Tuple[float, float]]:
    """
    Geocodes a location and ensures it falls within Australia.
    Includes better error handling and rate limiting.
    """
    if not location:
        return None

    # Format location string
    if "VIC" in location.upper():
        formatted_loc = f"{location.replace('VIC', '').strip()}, Victoria, Australia"
    else:
        formatted_loc = f"{location.strip()}, Australia"

    max_retries = 3
    base_delay = 1  # Base delay in seconds
    
    for attempt in range(max_retries):
        try:
            # Exponential backoff
            time.sleep(base_delay * (2 ** attempt))
            
            geo = geolocator.geocode(formatted_loc)
            if geo:
                lat, lon = geo.latitude, geo.longitude
                if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                    return lat, lon
                else:
                    logger.warning(f"Location outside Australia bounds: {formatted_loc}")
            else:
                logger.warning(f"Could not geocode location: {formatted_loc}")
                
        except GeocoderTimedOut:
            logger.warning(f"Geocoding timed out for {formatted_loc} (attempt {attempt + 1}/{max_retries})")
            continue
        except GeocoderUnavailable:
            logger.error(f"Geocoding service unavailable for {formatted_loc}")
            # Wait longer if service is unavailable
            time.sleep(5)
            continue
        except Exception as e:
            logger.error(f"Unexpected error geocoding {formatted_loc}: {str(e)}")
            break

    return None

def get_location_data() -> List[Tuple[float, float]]:
    """Converts job locations to latitude & longitude with progress bar."""
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

    try:
        # Generate heatmap
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
        logger.error(f"Application error: {str(e)}")
        st.error("An error occurred while generating the heatmap. Please try again later.")

if __name__ == "__main__":
    main()
