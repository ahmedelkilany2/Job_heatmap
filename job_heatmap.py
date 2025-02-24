import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# --- 1. Streamlit page configuration ---
st.set_page_config(
    page_title="Jora Job Analysis",
    page_icon="📊",
    layout="wide",
)

# Title and description
st.title("Jora Job Scraping Analysis - Australia 📊")
st.markdown("Interactive dashboard analyzing job postings data scraped from Jora website.")

# --- 2. Data Loading and Processing ---
# Modified Google Sheets CSV URL
sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/export?format=csv&gid=0"

@st.cache_data
def load_data():
    """Loads data from Google Sheets CSV URL."""
    try:
        df = pd.read_csv(sheet_url)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

@st.cache_data
def geocode_locations(locations):
    """
    Geocodes a list of locations to get their coordinates.
    Uses caching to avoid re-geocoding the same locations.
    """
    geolocator = Nominatim(user_agent="my_job_analysis_app")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    
    coordinates = {}
    for loc in locations:
        try:
            # Add 'Australia' to the location string to improve accuracy
            location_str = f"{loc}, Australia"
            location = geocode(location_str)
            if location:
                coordinates[loc] = (location.latitude, location.longitude)
            else:
                st.warning(f"Could not geocode location: {loc}")
                coordinates[loc] = None
            time.sleep(1)  # Additional delay to respect rate limits
        except Exception as e:
            st.warning(f"Error geocoding {loc}: {str(e)}")
            coordinates[loc] = None
    
    return coordinates

def create_location_heatmap(df):
    """Creates a heatmap of job locations."""
    if df is None or 'location' not in df.columns:
        st.error("Required location data not found in the dataset.")
        return
    
    # Get unique locations
    unique_locations = df['location'].unique()
    
    # Show progress
    with st.spinner('Geocoding locations... This may take a few minutes.'):
        coordinates_dict = geocode_locations(unique_locations)
    
    # Create a list of coordinates with their counts
    location_data = []
    for loc in df['location']:
        if coordinates_dict.get(loc):
            location_data.append(coordinates_dict[loc])
    
    if not location_data:
        st.error("No valid coordinates found for the locations.")
        return
    
    # Create the map centered on Australia
    m = folium.Map(location=[-25.2744, 133.7751], zoom_start=4)
    
    # Add the heatmap layer
    HeatMap(location_data, radius=15, blur=10).add_to(m)
    
    # Display the map
    st_folium(m, height=600, width=None)

# --- 3. Main Dashboard Layout ---
def main():
    # Load the data
    df = load_data()
    
    if df is not None:
        # Display basic statistics
        st.subheader("Dataset Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Job Postings", len(df))
        
        with col2:
            unique_locations = len(df['location'].unique())
            st.metric("Unique Locations", unique_locations)
        
        with col3:
            if 'category' in df.columns:
                unique_categories = len(df['category'].unique())
                st.metric("Job Categories", unique_categories)
        
        # Display the heatmap
        st.subheader("Job Posting Locations Heatmap 🗺️")
        create_location_heatmap(df)
        
        # Optional: Show raw data
        if st.checkbox("Show Raw Data"):
            st.subheader("Raw Data")
            st.dataframe(df)
    else:
        st.error("Failed to load data. Please check the Google Sheets URL and try again.")

if __name__ == "__main__":
    main()
