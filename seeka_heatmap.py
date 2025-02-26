import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import geocoder
import os
from dotenv import load_dotenv
import time
import re

# Load environment variables (optional, for customization)
load_dotenv()

# Set up the Streamlit app
st.set_page_config(page_title="Victorian Suburbs Job Heatmap", layout="wide")
st.title("Victorian Suburbs Job Heatmap")

# Function to load data from the direct Google Sheets CSV link
@st.cache_data
def load_data(csv_url):
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Improve suburb data for geocoding with Victorian context
def prepare_victorian_suburb(suburb):
    if pd.isna(suburb) or suburb == '':
        return None
        
    # If it's just a suburb name without VIC, add it
    if "VIC" not in suburb and "Victoria" not in suburb:
        suburb = f"{suburb}, VIC, Australia"
    # If it has VIC but no Australia, add Australia
    elif "VIC" in suburb and "Australia" not in suburb:
        suburb = f"{suburb}, Australia"
    # If it doesn't have either, add both
    elif "VIC" not in suburb and "Victoria" not in suburb and "Australia" not in suburb:
        suburb = f"{suburb}, VIC, Australia"
        
    return suburb

# Function to geocode Victorian suburbs
@st.cache_data
def geocode_victorian_suburbs(df, suburb_column):
    if suburb_column not in df.columns:
        st.error(f"Column '{suburb_column}' not found in the data. Available columns: {', '.join(df.columns)}")
        return None
    
    # Create new columns for latitude and longitude
    result_df = df.copy()
    result_df['latitude'] = None
    result_df['longitude'] = None
    result_df['geocoded_address'] = None
    
    # Set bounds for Victoria to improve geocoding accuracy
    victoria_bounds = {
        'min_lon': 140.9,
        'max_lon': 150.0,
        'min_lat': -39.2,
        'max_lat': -33.9
    }
    
    with st.spinner('Geocoding Victorian suburbs... This may take a while.'):
        progress_bar = st.progress(0)
        total_rows = len(df)
        
        for i, row in df.iterrows():
            # Get suburb and prepare it
            suburb = prepare_victorian_suburb(row[suburb_column])
            if not suburb:
                continue
                
            try:
                # First try with Nominatim (OSM) with Australia as region
                g = geocoder.osm(suburb, country='Australia')
                
                # If that fails, try with ArcGIS
                if not g.ok:
                    g = geocoder.arcgis(suburb)
                    
                # If that fails too, try with the OpenCage if API key is available
                if not g.ok and os.getenv('OPENCAGE_API_KEY'):
                    g = geocoder.opencage(suburb, key=os.getenv('OPENCAGE_API_KEY'))
                
                if g.ok:
                    # Verify the coordinates are within Victoria
                    if (victoria_bounds['min_lat'] <= g.lat <= victoria_bounds['max_lat'] and 
                        victoria_bounds['min_lon'] <= g.lng <= victoria_bounds['max_lon']):
                        
                        result_df.at[i, 'latitude'] = g.lat
                        result_df.at[i, 'longitude'] = g.lng
                        result_df.at[i, 'geocoded_address'] = g.address
                    else:
                        st.warning(f"Geocoded coordinates for '{suburb}' are outside Victoria")
                else:
                    st.warning(f"Could not geocode suburb: {suburb}")
            except Exception as e:
                st.warning(f"Error geocoding suburb '{suburb}': {e}")
            
            # Update progress
            progress_bar.progress((i + 1) / total_rows)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.2)
    
    # Drop rows with missing coordinates
    geocoded_df = result_df.dropna(subset=['latitude', 'longitude'])
    
    if len(geocoded_df) == 0:
        st.error("No valid coordinates found after geocoding")
        return None
        
    return geocoded_df

# Function to create heatmap
def create_heatmap(df, suburb_column):
    # Create a map centered around Melbourne, Victoria
    center_lat = df['latitude'].mean() if not df['latitude'].empty else -37.8136
    center_lng = df['longitude'].mean() if not df['longitude'].empty else 144.9631
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=10)
    
    # Add heatmap layer
    heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]
    HeatMap(heat_data).add_to(m)
    
    # Add markers for each location with job details
    for _, row in df.iterrows():
        # Create popup content with suburb information
        popup_html = f"""
        <div style="width: 200px">
            <h4>{row.get(suburb_column, 'Unknown Suburb')}</h4>
            <p><b>Geocoded Address:</b> {row.get('geocoded_address', '')}</p>
        """
        
        # Add other relevant columns to popup
        for col in df.columns:
            if col not in ['latitude', 'longitude', suburb_column, 'geocoded_address'] and not pd.isna(row[col]) and row[col] != '':
                popup_html += f"<p><b>{col}:</b> {row[col]}</p>"
                
        popup_html += "</div>"
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(icon="home", prefix="fa")
        ).add_to(m)
    
    return m

# Helper function to handle pasted suburb data
def parse_suburb_data(suburb_text):
    # Split by newlines and remove any header rows
    suburbs = [line.strip() for line in suburb_text.split('\n') if line.strip()]
    
    # Remove any header row if it exists (e.g., "Suburb")
    if suburbs and suburbs[0].lower() == "suburb":
        suburbs = suburbs[1:]
    
    return pd.DataFrame({"Suburb": suburbs})

# Main app logic
def main():
    # Default Google Sheets CSV URL
    default_csv_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"
    
    # Add tabs for different data input methods
    tab1, tab2, tab3 = st.tabs(["Google Sheets", "Paste Suburbs", "Upload File"])
    
    df = None
    suburb_column = "Suburb"  # Default column name
    
    with tab1:
        st.subheader("Load from Google Sheets")
        use_default = st.checkbox("Use default Google Sheets URL", value=True)
        
        if use_default:
            csv_url = default_csv_url
        else:
            csv_url = st.text_input("Enter Google Sheets CSV URL", value=default_csv_url)
            
        if st.button("Load from Google Sheets", key="load_sheets"):
            with st.spinner("Loading data from Google Sheets..."):
                df = load_data(csv_url)
                
    with tab2:
        st.subheader("Paste Suburb Data")
        pasted_suburbs = st.text_area(
            "Paste suburb data (one suburb per line)",
            height=300,
            placeholder="Carlton\nDandenong\nMelbourne VIC\nRichmond\n..."
        )
        
        if st.button("Use Pasted Data", key="use_pasted"):
            if pasted_suburbs:
                df = parse_suburb_data(pasted_suburbs)
                st.success(f"Created dataset with {len(df)} suburbs")
            else:
                st.error("Please paste suburb data first")
                
    with tab3:
        st.subheader("Upload CSV File")
        uploaded_file = st.file_uploader("Upload a CSV file containing suburb data", type=["csv"])
        
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.success(f"Uploaded file with {len(df)} rows")
    
    if df is not None:
        st.success(f"Data loaded successfully with {len(df)} rows")
        
        # Display the raw data
        with st.expander("Show raw data"):
            st.dataframe(df)
        
        # Identify the suburb column if it's not already named "Suburb"
        if "Suburb" not in df.columns:
            # Look for likely suburb column names
            potential_columns = [col for col in df.columns if any(
                keyword in col.lower() for keyword in ["suburb", "location", "address", "place"])]
            
            if potential_columns:
                suburb_column = st.selectbox(
                    "Select the column containing suburb names:",
                    options=potential_columns,
                    index=0
                )
            else:
                suburb_column = st.selectbox(
                    "Select the column containing suburb names:",
                    options=df.columns.tolist(),
                    index=0
                )
        else:
            suburb_column = "Suburb"
            st.info(f"Using '{suburb_column}' as the suburb column")
        
        # Show a sample of the suburbs to be geocoded
        st.subheader("Sample Suburbs")
        st.write(df[suburb_column].head(5).tolist())
        
        # Create a button to start geocoding
        if st.button("Generate Heatmap"):
            # Geocode the suburbs
            geocoded_df = geocode_victorian_suburbs(df, suburb_column)
            
            if geocoded_df is not None and len(geocoded_df) > 0:
                # Show stats
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Suburbs", len(df))
                col2.metric("Geocoded Suburbs", len(geocoded_df))
                col3.metric("Success Rate", f"{len(geocoded_df)/len(df)*100:.1f}%")
                
                # Create and display the map
                st.subheader("Victorian Suburbs Heatmap")
                map_obj = create_heatmap(geocoded_df, suburb_column)
                folium_static(map_obj, width=1200, height=600)
                
                # Show the geocoded data
                with st.expander("Show geocoded data"):
                    st.dataframe(geocoded_df)
                    
                # Add download button for geocoded data
                csv = geocoded_df.to_csv(index=False)
                st.download_button(
                    label="Download geocoded data as CSV",
                    data=csv,
                    file_name="geocoded_victorian_suburbs.csv",
                    mime="text/csv",
                )
            else:
                st.error("Failed to geocode any suburbs. Please check the data format.")
                
                # Add debugging info
                st.subheader("Troubleshooting")
                st.markdown("""
                ### Try using more specific suburb formats:
                - Add "VIC, Australia" to suburb names (e.g., "Carlton, VIC, Australia")
                - For Melbourne suburbs, add the area (e.g., "South Melbourne, VIC, Australia")
                - Consider adding postal codes if available
                """)
    else:
        st.info("Please load data using one of the tabs above")

if __name__ == "__main__":
    main()
