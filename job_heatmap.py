import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets API Setup
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/edit#gid=0"

# Authenticate and fetch Google Sheets data
def load_google_sheets(sheet_url):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Path to your Google Service Account JSON key file
    creds = ServiceAccountCredentials.from_json_keyfile_name("YOUR_SERVICE_ACCOUNT.json", scope)
    client = gspread.authorize(creds)

    # Extract Google Sheets ID from URL
    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
    sheet = client.open_by_key(sheet_id).sheet1

    # Convert to DataFrame
    data = pd.DataFrame(sheet.get_all_records())
    return data

# Load Data
try:
    df = load_google_sheets(SHEET_URL)
except Exception as e:
    st.error(f"Error loading Google Sheets: {e}")
    st.stop()

# Ensure the Location column exists
if "Location" not in df.columns:
    st.error("Error: 'Location' column not found in the Google Sheet.")
    st.stop()

# Process Data - Count jobs per city
city_counts = df["Location"].value_counts().reset_index()
city_counts.columns = ["City", "Job Count"]

# Streamlit UI
st.title("Job Distribution Heatmap (Jora Data)")

# Interactive Heatmap using Plotly
fig = px.density_mapbox(city_counts, 
                        lat=[3.1390] * len(city_counts),  # Default to Kuala Lumpur for now
                        lon=[101.6869] * len(city_counts),
                        z="Job Count", 
                        hover_name="City",
                        radius=30,
                        center={"lat": 3.1390, "lon": 101.6869},
                        zoom=6,
                        mapbox_style="carto-positron")

st.plotly_chart(fig, use_container_width=True)
