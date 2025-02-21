import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
import pandas as pd

# Google Sheets setup
SCOPE = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

# Your Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/edit?gid=0#gid=0"  
SHEET_ID = SHEET_URL.split('/d/')[1].split('/')[0]

def init_google_sheets():
    """Initialize Google Sheets connection"""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPE
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None

def load_data_from_sheets():
    """Load data directly from Google Sheets"""
    try:
        client = init_google_sheets()
        if client is None:
            return None

        # Open the spreadsheet
        sheet = client.open_by_key(SHEET_ID).sheet1
        
        # Get all values from the sheet
        data = sheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        return df
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def clean_data(df):
    """Clean and prepare the location data"""
    if df is None:
        return None
    
    # Assuming columns are named 'latitude' and 'longitude'
    # Adjust these based on your actual column names
    required_columns = ['latitude', 'longitude']
    
    # Check if required columns exist
    if not all(col in df.columns for col in required_columns):
        st.error("Please ensure your data has 'latitude' and 'longitude' columns")
        return None
    
    # Convert to numeric, replacing non-numeric values with NaN
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Remove any rows with missing coordinates
    df = df.dropna(subset=required_columns)
    
    # Remove duplicates but keep track of frequency
    location_counts = df.groupby(['latitude', 'longitude']).size().reset_index(name='count')
    
    return location_counts

def create_heatmap(data):
    """Create a folium heatmap from the location data"""
    # Calculate the center point for the map
    center_lat = data['latitude'].mean()
    center_lon = data['longitude'].mean()
    
    # Create the base map
    m = folium.Map(location=[center_lat, center_lon], 
                  zoom_start=10,
                  tiles='CartoDB positron')
    
    # Prepare the heatmap data
    heat_data = [[row['latitude'], row['longitude'], row['count']] 
                 for idx, row in data.iterrows()]
    
    # Add the heatmap layer
    HeatMap(heat_data,
            min_opacity=0.4,
            max_val=data['count'].max(),
            radius=15, 
            blur=15,
            max_zoom=1).add_to(m)
    
    return m

def main():
    st.title('Location Heatmap Visualization')
    
    # Add refresh button
    if st.button('Refresh Data'):
        st.experimental_rerun()
    
    # Load data from Google Sheets
    with st.spinner('Loading data from Google Sheets...'):
        df = load_data_from_sheets()
    
    if df is not None:
        # Clean and prepare data
        data = clean_data(df)
        
        if data is not None:
            # Create and display the map
            st.write("### Heatmap of Locations")
            st.write(f"Total unique locations: {len(data)}")
            
            map_object = create_heatmap(data)
            folium_static(map_object)
            
            # Display data statistics
            st.write("### Data Summary")
            st.write("Top 10 most frequent locations:")
            st.dataframe(data.nlargest(10, 'count'))
            
            # Display raw data option
            if st.checkbox('Show raw data'):
                st.write(df)

if __name__ == "__main__":
    main()
