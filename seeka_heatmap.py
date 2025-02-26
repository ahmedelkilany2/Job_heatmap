import streamlit as st
import pandas as pd
import plotly.express as px
import geopandas as gpd
import requests

# Set page title and configuration
st.set_page_config(page_title="Australia Job Location Heatmap", layout="wide")
st.title("Australia Job Location Heatmap")

# Direct CSV link
CSV_URL = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/export?format=csv"

# Load data function
@st.cache_data
def load_data(csv_url):
    try:
        data = pd.read_csv(csv_url)
        return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Function to clean and geocode locations
@st.cache_data
def process_locations(df):
    if 'Location' not in df.columns:
        st.error("No 'Location' column found in the data")
        return None
    
    # Create a copy of the dataframe with just the location column
    location_df = df[['Location']].copy()
    
    # Clean location data
    location_df['clean_location'] = location_df['Location'].str.strip()
    
    # Handle VIC as Victoria
    location_df['clean_location'] = location_df['clean_location'].str.replace(r'\bVIC\b', 'Victoria', regex=True)
    
    # Australian states and territories
    australian_locations = [
        'Australia', 'New South Wales', 'NSW', 'Victoria', 'VIC', 
        'Queensland', 'QLD', 'South Australia', 'SA', 'Western Australia', 'WA',
        'Tasmania', 'TAS', 'Northern Territory', 'NT', 'Australian Capital Territory', 'ACT',
        'Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Hobart', 'Darwin', 'Canberra'
    ]
    
    # Filter for Australian locations
    aus_pattern = '|'.join([rf'\b{loc}\b' for loc in australian_locations])
    mask = location_df['clean_location'].str.contains(aus_pattern, case=False, na=False, regex=True)
    aus_locations = location_df[mask]
    
    # Count occurrences of each location
    location_counts = aus_locations['clean_location'].value_counts().reset_index()
    location_counts.columns = ['location', 'count']
    
    return location_counts

# Load Australian states shapefile
@st.cache_data
def load_aus_map():
    # URL to Australian states GeoJSON
    aus_states_url = "https://raw.githubusercontent.com/rowanhogan/australian-states/master/states.geojson"
    try:
        gdf = gpd.read_file(aus_states_url)
        return gdf
    except Exception as e:
        st.error(f"Error loading Australia map data: {e}")
        return None

# Main function to create the heatmap
def create_heatmap(location_counts, aus_gdf):
    if location_counts is None or aus_gdf is None:
        return None
    
    # Mapping of common names/abbreviations to state names in the GeoJSON
    state_mapping = {
        'New South Wales': 'New South Wales',
        'NSW': 'New South Wales',
        'Victoria': 'Victoria',
        'VIC': 'Victoria',
        'Queensland': 'Queensland',
        'QLD': 'Queensland',
        'South Australia': 'South Australia',
        'SA': 'South Australia',
        'Western Australia': 'Western Australia',
        'WA': 'Western Australia',
        'Tasmania': 'Tasmania',
        'TAS': 'Tasmania',
        'Northern Territory': 'Northern Territory',
        'NT': 'Northern Territory',
        'Australian Capital Territory': 'Australian Capital Territory',
        'ACT': 'Australian Capital Territory',
        'Sydney': 'New South Wales',
        'Melbourne': 'Victoria',
        'Brisbane': 'Queensland',
        'Perth': 'Western Australia',
        'Adelaide': 'South Australia',
        'Hobart': 'Tasmania',
        'Darwin': 'Northern Territory',
        'Canberra': 'Australian Capital Territory'
    }
    
    # Add state column based on mapping
    location_counts['state'] = location_counts['location'].map(
        lambda x: next((state_mapping[k] for k in state_mapping.keys() 
                       if k.lower() in x.lower()), 'Unknown')
    )
    
    # Aggregate counts by state
    state_counts = location_counts.groupby('state')['count'].sum().reset_index()
    
    # Merge with GeoJSON data
    merged_data = aus_gdf.merge(state_counts, left_on='STATE_NAME', right_on='state', how='left')
    merged_data['count'] = merged_data['count'].fillna(0)
    
    # Create choropleth map
    fig = px.choropleth_mapbox(
        merged_data,
        geojson=merged_data.geometry,
        locations=merged_data.index,
        color='count',
        color_continuous_scale='Viridis',
        mapbox_style='carto-positron',
        zoom=3,
        center={"lat": -25.2744, "lon": 133.7751},  # Center of Australia
        opacity=0.7,
        labels={'count': 'Number of Jobs'},
        hover_data=['STATE_NAME', 'count']
    )
    
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=600
    )
    
    return fig

# Main app flow
with st.sidebar:
    st.header("Settings")
    refresh_data = st.button("Refresh Data & Generate Heatmap")

# Load and process data
if 'data' not in st.session_state or refresh_data:
    with st.spinner("Loading job data..."):
        data = load_data(CSV_URL)
        if data is not None:
            st.session_state.data = data
            st.success("Data loaded successfully!")
        else:
            st.error("Failed to load data. Please check the CSV URL.")

if 'data' in st.session_state:
    data = st.session_state.data
    
    # Display raw data
    with st.expander("View Raw Data"):
        st.dataframe(data)
    
    # Process locations
    with st.spinner("Processing location data..."):
        location_counts = process_locations(data)
        aus_gdf = load_aus_map()
    
    # Create and display heatmap
    if location_counts is not None and aus_gdf is not None:
        st.subheader("Australian Job Locations Heatmap")
        fig = create_heatmap(location_counts, aus_gdf)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        
        # Display location counts table
        st.subheader("Job Counts by Location")
        st.dataframe(location_counts.sort_values('count', ascending=False))
    else:
        st.error("Could not process location data or load map.")
else:
    st.info("Click 'Refresh Data & Generate Heatmap' to load the data and generate the visualization.")

# GitHub information
st.sidebar.markdown("---")
st.sidebar.subheader("About this app")
st.sidebar.markdown(
    "This app visualizes job locations from Google Sheets data, "
    "specifically filtering for Australian locations and treating 'VIC' as Victoria. "
    "The code can be uploaded to GitHub and deployed on Streamlit Cloud."
)
