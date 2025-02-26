import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

# Google Sheets CSV link
sheet_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"

# Load dataset
df = pd.read_csv(sheet_url)

# Trim spaces from column names
df.columns = df.columns.str.strip()

# Keep only relevant columns
df = df[['Suburb']].dropna()

# Initialize geocoder
geolocator = Nominatim(user_agent="geoapiExercises")

# Function to get latitude and longitude
def get_coordinates(suburb):
    try:
        location = geolocator.geocode(f"{suburb}, Australia", timeout=10)
        if location:
            return location.latitude, location.longitude
    except GeocoderTimedOut:
        time.sleep(1)
        return get_coordinates(suburb)
    return None, None

# Apply function to get coordinates
df[['Latitude', 'Longitude']] = df['Suburb'].apply(lambda x: pd.Series(get_coordinates(x)))

# Drop rows with missing coordinates
df = df.dropna()

# Create base map centered around Australia
australia_map = folium.Map(location=[-25.2744, 133.7751], zoom_start=5)

# Add heatmap layer
heat_data = df[['Latitude', 'Longitude']].values.tolist()
HeatMap(heat_data, radius=15).add_to(australia_map)

# Save map to an HTML file
australia_map.save("australia_heatmap.html")

# Display map in notebook (if running in Jupyter)
australia_map
