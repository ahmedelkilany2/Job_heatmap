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

# Australian state mappings
STATE_MAPPINGS = {
    'VIC': 'Victoria',
    'NSW': 'New South Wales',
    'QLD': 'Queensland',
    'SA': 'South Australia',
    'WA': 'Western Australia',
    'TAS': 'Tasmania',
    'NT': 'Northern Territory',
    'ACT': 'Australian Capital Territory'
}

# --- 2. Data Loading and Processing ---
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
    Handles Australian state abbreviations and adds proper context for better accuracy.
    """
    geolocator = Nominatim(user_agent="my_job_analysis_app")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    
    coordinates = {}
    for loc in locations:
        try:
            # Process the location string
            location_parts = loc.strip().split()
            
            # Handle state abbreviations
            if location_parts[-1] in STATE_MAPPINGS:
                state_full = STATE_MAPPINGS[location_parts[-1]]
                city = ' '.join(location_parts[:-1])
                location_str = f"{city}, {state_full}, Australia"
            else:
                location_str = f"{loc}, Australia"

            # Try geocoding with formatted string
            location = geocode(location_str)
            
            # If failed, try with just city and country
            if not location and len(location_parts) > 1:
                city = ' '.join(location_parts[:-1])
                location = geocode(f"{city}, Australia")
            
            if location:
                coordinates[loc] = (location.latitude, location.longitude)
            else:
                st.warning(f"Could not geocode location: {loc}")
                # Fallback coordinates for Victorian locations if geocoding fails
                if 'VIC' in loc:
                    coordinates[loc] = (-37.8136, 144.9631)  # Melbourne coordinates as fallback
                else:
                    coordinates[loc] = None
                    
            time.sleep(1)  # Respect rate limits
            
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
    unique_locations = df['location'].dropna().unique()
    
    # Show progress
    with st.spinner('Geocoding locations... This may take a few minutes.'):
        coordinates_dict = geocode_locations(unique_locations)
    
    # Create a list of coordinates with their counts
    location_data = []
    for loc, count in df['location'].value_counts().items():
        if coordinates_dict.get(loc):
            # Add the same coordinates multiple times based on job count
            location_data.extend([coordinates_dict[loc]] * count)
    
    if not location_data:
        st.error("No valid coordinates found for the locations.")
        return
    
    # Create the map centered on Victoria, Australia
    m = folium.Map(location=[-37.8136, 144.9631], zoom_start=7)
    
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
        
        # Show location table
        st.subheader("Location Distribution")
        location_counts = df['location'].value_counts().reset_index()
        location_counts.columns = ['Location', 'Number of Jobs']
        st.dataframe(location_counts)
        
        # Optional: Show raw data
        if st.checkbox("Show Raw Data"):
            st.subheader("Raw Data")
            st.dataframe(df)
    else:
        st.error("Failed to load data. Please check the Google Sheets URL and try again.")

if __name__ == "__main__":
    main()
