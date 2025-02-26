import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# Define CSV URL (Update this if needed)
CSV_URL = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"

st.title("🔥 Seek Listings Heatmap")

@st.cache_data(ttl=14400)  # Cache data to avoid re-downloading
def load_data(url):
    """Fetch data from the given CSV URL."""
    return pd.read_csv(url)

# Load Data
try:
    df = load_data(CSV_URL)
    st.subheader("📊 Raw Data from URL")
    st.dataframe(df.head())
except Exception as e:
    st.error(f"🚨 Failed to load data from URL: {str(e)}")
    st.stop()

# Print available column names for debugging
st.write("🔍 Available Columns:", df.columns.tolist())

# Ensure 'address' column exists (Check alternative column names)
address_column = None
for col in df.columns:
    if "address" in col.lower() or "location" in col.lower():
        address_column = col
        break

if not address_column:
    st.error("🚨 The CSV file must contain an 'address' or 'location' column!")
    st.stop()

# Geolocator Setup
geolocator = Nominatim(user_agent="job_locator")

@st.cache_data(ttl=14400)  # Cache geocoded results
def geocode_location(address):
    """Convert address to latitude & longitude using Nominatim."""
    try:
        location_data = geolocator.geocode(f"{address}, Australia", timeout=10)
        if location_data:
            return location_data.latitude, location_data.longitude
    except (GeocoderTimedOut, GeocoderServiceError):
        return None, None
    return None, None

# Apply Geocoding if lat/lon not in CSV
if "latitude" not in df.columns or "longitude" not in df.columns:
    df["latitude"], df["longitude"] = zip(*df[address_column].apply(geocode_location))

# Drop rows where geocoding failed
df = df.dropna(subset=["latitude", "longitude"])

# Display Processed Data
st.subheader("✅ Processed Data with Coordinates")
st.dataframe(df)

# Generate Heatmap
st.subheader("📍 Job Locations Heatmap")
m = folium.Map(location=[-25.2744, 133.7751], zoom_start=5)  # Centered on Australia

heat_data = df[["latitude", "longitude"]].values.tolist()
HeatMap(heat_data).add_to(m)

folium_static(m)

# Download Processed Data
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download Processed CSV", csv, "processed_jobs.csv", "text/csv")
