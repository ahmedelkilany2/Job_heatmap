import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
import time
from streamlit_folium import folium_static

def get_lat_lon(location):
    geolocator = Nominatim(user_agent="geoapiExercises")
    try:
        loc = geolocator.geocode(location + ", Australia", timeout=10)
        if loc:
            return loc.latitude, loc.longitude
    except:
        pass
    return None, None

def load_data():
    url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/export?format=csv&gid=1195434071"
    df = pd.read_csv(url)
    return df

def filter_australian_locations(df):
    df = df[df['Location'].str.contains("Australia|VIC|Victoria|NSW|Sydney|Melbourne|Queensland|Brisbane|Perth|Adelaide", case=False, na=False)]
    df['Latitude'], df['Longitude'] = zip(*df['Location'].apply(get_lat_lon))
    df = df.dropna(subset=['Latitude', 'Longitude'])
    return df

def create_heatmap(df):
    st.title("Job Locations Heatmap - Australia")
    
    # Initialize map
    m = folium.Map(location=[-25.2744, 133.7751], zoom_start=5)  # Centered in Australia
    
    # Add heatmap layer
    heat_data = [[row['Latitude'], row['Longitude']] for _, row in df.iterrows()]
    HeatMap(heat_data).add_to(m)
    
    folium_static(m)

def main():
    st.set_page_config(page_title="Job Locations Heatmap", layout="wide")
    df = load_data()
    df = filter_australian_locations(df)
    create_heatmap(df)

if __name__ == "__main__":
    main()
