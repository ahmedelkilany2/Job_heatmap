import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Google Sheets CSV export link
google_sheets_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"

def fetch_data():
    """Fetch data from Google Sheets."""
    df = pd.read_csv(google_sheets_url)
    return df

def get_coordinates(suburb):
    """Get latitude and longitude for a given suburb."""
    geolocator = Nominatim(user_agent="geo_locator")
    try:
        location = geolocator.geocode(f"{suburb}, Australia")
        if location:
            return location.latitude, location.longitude
    except GeocoderTimedOut:
        return None
    return None

def generate_heatmap(df):
    """Generate heatmap using folium."""
    m = folium.Map(location=[-25.2744, 133.7751], zoom_start=5)  # Centered in Australia
    
    for suburb in df['Suburb'].dropna().unique():
        coords = get_coordinates(suburb)
        if coords:
            folium.CircleMarker(location=coords, radius=5, color='red', fill=True, fill_color='red').add_to(m)
    
    return m

def main():
    st.title("Job Locations Heatmap - Australia")
    st.write("This map visualizes job locations based on suburbs from the Google Sheet.")
    
    df = fetch_data()
    
    if 'Suburb' not in df.columns:
        st.error("No 'Suburb' column found in the dataset.")
        return
    
    heatmap = generate_heatmap(df)
    folium_static(heatmap)

if __name__ == "__main__":
    main()
