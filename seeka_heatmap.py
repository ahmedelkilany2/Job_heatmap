import streamlit as st
import pandas as pd
import time
import folium
from streamlit_folium import folium_static
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Define the CSV URL (Replace with your actual link)
CSV_URL = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"

# Initialize Streamlit App
st.title("Job Listings Heatmap")

@st.cache_data(ttl=14400)  # Cache data to avoid re-downloading
def load_data(url):
    """Fetch data from the given CSV URL."""
    return pd.read_csv(url)

# Load Data
try:
    df = load_data(CSV_URL)
    st.subheader("Raw Data from URL")
    st.dataframe(df.head())
except Exception as e:
    st.error(f"🚨 Failed to load data from URL: {str(e)}")
    st.stop()

# Ensure 'address' column exists
if "address" not in df.columns:
    st.error("🚨 The CSV file must contain an 'address' column!")
    st.stop()

# Geolocator Setup
geolocator = Nominatim(user_agent="job_locator")

@st.cache_data(ttl=14400)  # Cache geocoded results
def geocode_location(address):
    """Convert address to latitude & longitude using Nominatim."""
    try:
        full_address = f"{address}, Australia"  # Ensure correct region
        location_data = geolocator.geocode(full_address, timeout=10)

        if location_data:
            return location_data.latitude, location_data.longitude
    except (GeocoderTimedOut, GeocoderServiceError):
        st.warning(f"⚠️ Geocoding timed out for {address}. Retrying in 2 seconds...")
        time.sleep(2)
        return geocode_location(address)
    except Exception as e:
        st.warning(f"⚠️ Geocoding failed for {address}: {str(e)}")
    
    return None, None  # Return None if geocoding fails

# Apply Geocoding to Address Column
st.subheader("Geocoding Job Locations")
if "latitude" not in df.columns or "longitude" not in df.columns:
    df["latitude"], df["longitude"] = zip(*df["address"].apply(geocode_location))

# Drop rows where geocoding failed
df = df.dropna(subset=["latitude", "longitude"])

# Display Processed Data
st.subheader("Processed Data with Coordinates")
st.dataframe(df)

# Generate Heatmap
st.subheader("Job Listings Heatmap")
map_center = [df["latitude"].mean(), df["longitude"].mean()]
job_map = folium.Map(location=map_center, zoom_start=6)
heat_data = df[["latitude", "longitude"]].values.tolist()
HeatMap(heat_data).add_to(job_map)

# Display the map
folium_static(job_map)

# Save Processed Data (Optional)
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Processed CSV", csv, "processed_jobs.csv", "text/csv")

