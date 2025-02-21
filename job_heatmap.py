import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets API setup
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_JSON = "your_google_credentials.json"  # Upload this JSON file in Streamlit
SPREADSHEET_ID = "1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA"

# Authenticate Google Sheets
def load_google_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_JSON, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Load data
df = load_google_sheet()

# Ensure the dataset has latitude and longitude columns
if "latitude" not in df.columns or "longitude" not in df.columns:
    st.error("The dataset must contain 'latitude' and 'longitude' columns.")
    st.stop()

# Remove duplicates
heat_data = df[['latitude', 'longitude']].drop_duplicates().values.tolist()

# Create a heatmap
st.title("Heat Map of Locations")
map_ = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], zoom_start=10)
HeatMap(heat_data).add_to(map_)

# Display the map
st_folium(map_, width=700, height=500)
