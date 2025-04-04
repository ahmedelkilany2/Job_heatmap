import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Photon
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import hashlib

# Set up Photon geocoder (alternative to Nominatim)
geolocator = Photon(user_agent="vic_job_analysis")

# Google Sheets URL (Make sure it's a public CSV link)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=600)  # Cache data for 10 minutes instead of 4 hours
def load_data():
    """Load job location data from Google Sheets."""
    try:
        df = pd.read_csv(GOOGLE_SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()  # Normalize column names
        if "location" not in df.columns:
            st.error("⚠️ 'location' column missing in the dataset!")
            return None
        return df
    except Exception as e:
        st.error(f"⚠️ Failed to load data: {str(e)}")
        return None

# Create a hash for each location to help with caching
def get_location_hash(location):
    return hashlib.md5(location.encode()).hexdigest()

@st.cache_data(ttl=86400)  # Cache geocoded results for 1 day
def geocode_location(location):
    """Convert location names to latitude & longitude using Photon."""
    try:
        full_location = f"{location}, Victoria, Australia"  # Ensure correct region
        location_data = geolocator.geocode(full_location, timeout=10)
        if location_data:
            return location_data.latitude, location_data.longitude
    except (GeocoderTimedOut, GeocoderServiceError):
        time.sleep(1)  # Shorter retry delay
        try:
            full_location = f"{location}, Victoria, Australia"
            location_data = geolocator.geocode(full_location, timeout=15)
            if location_data:
                return location_data.latitude, location_data.longitude
        except Exception:
            pass
    except Exception as e:
        pass
    return None, None

def main():
    """Main function to run the job heatmap dashboard."""
    st.subheader("📍Jora Job Posting Location Analysis (Victoria)")
    
    # Add auto-refresh button and interval selection
    col1, col2 = st.columns([3, 1])
    with col1:
        refresh_interval = st.selectbox(
            "Auto-refresh interval:",
            [None, "1 minute", "5 minutes", "10 minutes", "30 minutes"],
            index=0
        )
    with col2:
        refresh_button = st.button("🔄 Refresh Data")
    
    # Set up auto-refresh if selected
    if refresh_interval:
        interval_seconds = {
            "1 minute": 60,
            "5 minutes": 300, 
            "10 minutes": 600,
            "30 minutes": 1800
        }[refresh_interval]
        st.write(f"Auto-refreshing every {refresh_interval}")
        st.experimental_rerun_after(interval_seconds)
    
    # Force data reload if refresh button is clicked
    if refresh_button:
        st.cache_data.clear()
        st.success("✅ Cache cleared and data refreshed!")
    
    # Load data
    with st.spinner("Loading data from Google Sheets..."):
        df = load_data()
        
    if df is not None:
        st.success(f"✅ Data Loaded Successfully! Found {len(df)} job postings.")
        
        # Create a progress bar for geocoding
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process locations in batches for better performance
        locations = df["location"].unique()
        
        # Create a geocoding cache dictionary to avoid reprocessing same locations
        geocoded_locations = {}
        
        with st.spinner("Geocoding locations (this may take a moment)..."):
            for i, location in enumerate(locations):
                # Update progress
                progress = int((i + 1) / len(locations) * 100)
                progress_bar.progress(progress)
                status_text.text(f"Geocoding {i+1}/{len(locations)}: {location}")
                
                # Get coordinates
                lat, lon = geocode_location(location)
                geocoded_locations[location] = (lat, lon)
            
            # Apply the cached coordinates to the dataframe
            df["lat"] = df["location"].map(lambda x: geocoded_locations.get(x, (None, None))[0])
            df["lon"] = df["location"].map(lambda x: geocoded_locations.get(x, (None, None))[1])
            
            # Remove rows with missing coordinates
            valid_data = df.dropna(subset=["lat", "lon"])
            
            # Show stats
            status_text.text(f"Successfully geocoded {len(valid_data)} out of {len(df)} job postings.")
        
        if len(valid_data) > 0:
            # Create Map
            st.subheader("📍 Job Posting Density Heatmap For Jora")
            
            # Add map type selection
            map_type = st.radio(
                "Map Display Type:", 
                ["Heatmap", "Clustered Markers", "Both"],
                horizontal=True
            )
            
            m = folium.Map(location=[-37.8136, 144.9631], zoom_start=7)
            
            # Add Heatmap
            if map_type in ["Heatmap", "Both"]:
                from folium.plugins import HeatMap
                heat_data = valid_data[["lat", "lon"]].values.tolist()
                HeatMap(heat_data, radius=15, blur=10).add_to(m)
            
            # Add clustered markers
            if map_type in ["Clustered Markers", "Both"]:
                from folium.plugins import MarkerCluster
                marker_cluster = MarkerCluster().add_to(m)
                
                for _, row in valid_data.iterrows():
                    folium.Marker(
                        [row["lat"], row["lon"]],
                        popup=row["location"]
                    ).add_to(marker_cluster)
            
            # Display Map
            folium_static(m)
            
            # Download option
            st.download_button(
                "Download Geocoded Data (CSV)",
                valid_data.to_csv(index=False).encode('utf-8'),
                "geocoded_job_data.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.error("⚠️ No valid geocoded locations found.")
    else:
        st.error("⚠️ No data available! Please check your Google Sheet connection.")

if __name__ == "__main__":
    st.set_page_config(page_title="Job Posting Map", layout="wide")
    main()
