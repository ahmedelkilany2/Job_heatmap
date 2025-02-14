import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim, Photon
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time
import datetime
from typing import Optional, Tuple, List
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets CSV URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"

# Australia's latitude & longitude range
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Initialize geocoders
primary_geolocator = Nominatim(user_agent="python-job-heatmap-au-v2")
backup_geolocator = Photon(user_agent="python-job-heatmap-au-v2")

# Australian state mappings
STATE_MAPPINGS = {
    'VIC': 'Victoria',
    'NSW': 'New South Wales',
    'QLD': 'Queensland',
    'WA': 'Western Australia',
    'SA': 'South Australia',
    'TAS': 'Tasmania',
    'NT': 'Northern Territory',
    'ACT': 'Australian Capital Territory'
}

def clean_location(location: str) -> str:
    """Clean and standardize location string."""
    if not location or not isinstance(location, str):
        return ""
    
    # Convert to uppercase for consistent processing
    loc = location.upper().strip()
    
    # Remove common problematic characters and extra spaces
    loc = re.sub(r'[^\w\s,]', ' ', loc)
    loc = re.sub(r'\s+', ' ', loc)
    
    # Convert back to title case
    loc = loc.title()
    
    return loc

def format_location(location: str) -> str:
    """Format location string for geocoding."""
    if not location:
        return ""
    
    # Clean the location first
    loc = clean_location(location)
    
    # Check for state abbreviations
    for abbrev, full_name in STATE_MAPPINGS.items():
        if abbrev in loc.upper():
            # Replace abbreviation with full state name
            loc = loc.upper().replace(abbrev, full_name)
            break
    
    # Ensure "Australia" is added if not present
    if "AUSTRALIA" not in loc.upper():
        loc += ", Australia"
    
    return loc

@st.cache_data(ttl=14_400)  # Cache for 4 hours
def fetch_data() -> List[str]:
    """Fetch job locations from Google Sheets."""
    try:
        df = pd.read_csv(SHEET_URL)
        locations = df.iloc[:, 0].dropna().tolist()
        
        # Debug information
        st.sidebar.write("📊 **Data Statistics**")
        st.sidebar.write(f"Total locations found: {len(locations)}")
        st.sidebar.write("First 5 locations (raw):")
        for loc in locations[:5]:
            st.sidebar.write(f"- {loc}")
            formatted_loc = format_location(loc)
            if formatted_loc != loc:
                st.sidebar.write(f"  → formatted to: {formatted_loc}")
            
        return locations
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        st.error(f"Unable to fetch data from Google Sheets: {str(e)}")
        return []

@st.cache_data(ttl=14_400)
def geocode_location(location: str, attempt_number: int = 0) -> Optional[Tuple[float, float]]:
    """Geocodes a location using multiple services with fallback."""
    if not location:
        return None

    # Format location string
    formatted_loc = format_location(location)
    
    if debug_mode:
        st.sidebar.write(f"Geocoding: {location}")
        if formatted_loc != location:
            st.sidebar.write(f"Formatted to: {formatted_loc}")

    try:
        # Try primary geocoder first
        geo = primary_geolocator.geocode(formatted_loc, timeout=10)
        if geo:
            lat, lon = geo.latitude, geo.longitude
            if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                if debug_mode:
                    st.sidebar.success(f"✅ Successfully geocoded: {formatted_loc}")
                return lat, lon
            else:
                if debug_mode:
                    st.sidebar.warning(f"📍 Location outside Australia: {formatted_loc}")
            
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        if debug_mode:
            st.sidebar.warning(f"Primary geocoder failed ({str(e)}), trying backup for: {formatted_loc}")
        try:
            # Try backup geocoder
            time.sleep(1)  # Add delay before trying backup
            geo = backup_geolocator.geocode(formatted_loc, timeout=10)
            if geo:
                lat, lon = geo.latitude, geo.longitude
                if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                    return lat, lon
                
        except Exception as e:
            if debug_mode:
                st.sidebar.error(f"Both geocoders failed for: {formatted_loc}")
                st.sidebar.error(f"Error: {str(e)}")
            
    except Exception as e:
        if debug_mode:
            st.sidebar.error(f"Geocoding error for {formatted_loc}: {str(e)}")
        
    # If we're here, both geocoders failed or returned invalid coordinates
    if attempt_number < 2:  # Try up to 3 times
        time.sleep(2 ** attempt_number)  # Exponential backoff
        return geocode_location(location, attempt_number + 1)
        
    return None

def get_location_data() -> List[Tuple[float, float]]:
    """Converts job locations to latitude & longitude with progress bar."""
    locations = fetch_data()
    if not locations:
        return []

    valid_locations = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Debug counters
    total = len(locations)
    success = 0
    failed = 0
    failed_locations = []
    
    for idx, loc in enumerate(locations):
        result = geocode_location(loc)
        if result:
            valid_locations.append(result)
            success += 1
        else:
            failed += 1
            failed_locations.append(loc)
            
        # Update progress and stats
        progress = (idx + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Processing: {idx + 1}/{total} locations (Success: {success}, Failed: {failed})")
        
    progress_bar.empty()
    status_text.empty()
    
    # Show final stats in sidebar
    st.sidebar.write("📈 **Final Statistics**")
    st.sidebar.write(f"Total processed: {total}")
    st.sidebar.write(f"Successfully geocoded: {success}")
    st.sidebar.write(f"Failed to geocode: {failed}")
    
    if failed > 0 and debug_mode:
        st.sidebar.write("Failed Locations (first 10):")
        for loc in failed_locations[:10]:
            st.sidebar.write(f"- {loc}")
    
    return valid_locations

def main():
    # Add debug mode toggle
    st.sidebar.title("Debug Options")
    global debug_mode  # Make debug_mode accessible to other functions
    debug_mode = st.sidebar.checkbox("Enable Debug Mode")
    
    if debug_mode:
        st.sidebar.write("🔍 Debug Mode Enabled")
    
    # Rest of the main function remains the same...
    # (Keep the existing main function code)

if __name__ == "__main__":
    main()
