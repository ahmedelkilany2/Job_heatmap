import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Photon  # More stable geocoding service
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# Set up Photon geocoder (alternative to Nominatim)
geolocator = Photon(user_agent="vic_job_analysis")

# Google Sheets URL (Make sure it's a public CSV link)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=14400)  # Cache data for 4 hours
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

@st.cache_data(ttl=14400)  # Cache geocoded results
def geocode_location(location):
    """Convert location names to latitude & longitude using Photon."""
    try:
        full_location = f"{location}, Victoria, Australia"  # Ensure correct region
        location_data = geolocator.geocode(full_location, timeout=10)
        if location_data:
            return location_data.latitude, location_data.longitude
    except (GeocoderTimedOut, GeocoderServiceError):
        st.warning(f"⚠️ Geocoding timed out for {location}. Retrying in 2 seconds...")
        time.sleep(2)
        return geocode_location(location)
    except Exception as e:
        st.warning(f"⚠️ Geocoding failed for {location}: {str(e)}")
    return None, None

def main():
    """Main function to run the job heatmap dashboard."""
    st.subheader("📍 Job Posting Location Analysis (Victoria)")

    # Load data
    df = load_data()

    if df is not None:
        st.success("✅ Data Loaded Successfully!")
        
        # Apply geocoding with caching
        df["lat"], df["lon"] = zip(*df["location"].apply(geocode_location))
        df = df.dropna(subset=["lat", "lon"])  # Remove rows with missing coordinates

        # Create Map
        st.subheader("📍 Job Posting Density Heatmap For Seek")
        m = folium.Map(location=[-37.8136, 144.9631], zoom_start=6)  # Default: Melbourne, VIC

        # Add Heatmap
        from folium.plugins import HeatMap
        heat_data = df[["lat", "lon"]].values.tolist()
        HeatMap(heat_data, radius=15, blur=10).add_to(m)

        # Display Map
        folium_static(m)
    else:
        st.error("⚠️ No data available! Please check your Google Sheet connection.")

if __name__ == "__main__":
    main()
