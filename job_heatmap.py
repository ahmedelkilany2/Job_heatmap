import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
import streamlit as st
from streamlit_folium import st_folium
import datetime
import os
import json
from collections import defaultdict

# Set page config
st.set_page_config(
    page_title="Job Location Heatmap",
    page_icon="🗺️",
    layout="wide"
)

# Title and description
st.title("Job Location Heatmap - Australia")
st.markdown("This map shows the distribution of job postings across Australia.")

# Cache file for geocoding results
CACHE_FILE = "geocode_cache.json"

# Australia's bounds
AU_LAT_MIN, AU_LAT_MAX = -44, -10
AU_LON_MIN, AU_LON_MAX = 112, 154

# Load existing cache
def load_geocoding_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

# Save cache
def save_geocoding_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

@st.cache_data(ttl=14400)  # Cache for 4 hours
def process_locations(df):
    # Initialize geocoder
    geolocator = Nominatim(user_agent="job_location_geocoder")
    
    # Load cache
    geocode_cache = load_geocoding_cache()
    
    # Group locations to count frequency
    location_counts = df['location'].value_counts().to_dict()
    
    # Process locations
    location_data = defaultdict(int)
    processed = 0
    total = len(location_counts)
    
    # Create a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for location, count in location_counts.items():
        if location in geocode_cache:
            if geocode_cache[location]:  # If valid coordinates exist
                location_data[geocode_cache[location]] += count
        else:
            try:
                # Format location string
                search_loc = f"{location}, Australia"
                if "VIC" in location:
                    search_loc = f"{location.replace('VIC', '').strip()}, Victoria, Australia"
                
                # Geocode with increased timeout
                result = geolocator.geocode(search_loc, timeout=10)
                
                if result:
                    lat, lon = result.latitude, result.longitude
                    if AU_LAT_MIN <= lat <= AU_LAT_MAX and AU_LON_MIN <= lon <= AU_LON_MAX:
                        coords = (lat, lon)
                        geocode_cache[location] = coords
                        location_data[coords] += count
                    else:
                        geocode_cache[location] = None
                else:
                    geocode_cache[location] = None
                
            except Exception as e:
                st.warning(f"Error geocoding {location}: {str(e)}")
                geocode_cache[location] = None
            
            # Save cache periodically
            if processed % 10 == 0:
                save_geocoding_cache(geocode_cache)
        
        # Update progress
        processed += 1
        progress_bar.progress(processed / total)
        status_text.text(f"Processed {processed} of {total} locations")
    
    # Final cache save
    save_geocoding_cache(geocode_cache)
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Convert to format needed for heatmap
    heatmap_data = []
    for coords, count in location_data.items():
        heatmap_data.extend([coords] * count)
    
    return {
        'heatmap_data': heatmap_data,
        'total_jobs': sum(location_counts.values()),
        'unique_locations': len(location_counts),
        'geocoded_locations': len([v for v in geocode_cache.values() if v is not None])
    }

# Load and process data
try:
    # Load data from Google Sheets
    sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"
    df = pd.read_csv(sheet_url)
    
    # Process data
    data = process_locations(df)
    
    # Display statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Job Postings", data['total_jobs'])
    col2.metric("Unique Locations", data['unique_locations'])
    col3.metric("Geocoded Locations", data['geocoded_locations'])
    
    # Create map
    if data['heatmap_data']:
        map_center = [-25.2744, 133.7751]
        job_map = folium.Map(location=map_center, zoom_start=5)
        HeatMap(data['heatmap_data'], radius=15, blur=10).add_to(job_map)
        st_folium(job_map, width=1200, height=600)
    else:
        st.warning("No location data available to display on the map.")

except Exception as e:
    st.error(f"Error processing data: {str(e)}")

# Add footer
st.markdown("---")
st.markdown("© 2025 - Job Location Heatmap")

# Refresh button
if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()
