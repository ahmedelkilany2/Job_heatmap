import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import geocoder
import os
from dotenv import load_dotenv

# Load environment variables (optional, for customization)
load_dotenv()

# Set up the Streamlit app
st.set_page_config(page_title="Job Locations Heatmap", layout="wide")
st.title("Job Locations Heatmap")

# Function to load data from the direct Google Sheets CSV link
@st.cache_data
def load_data(csv_url):
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Function to geocode addresses
@st.cache_data
def geocode_addresses(df, address_column):
    if address_column not in df.columns:
        st.error(f"Column '{address_column}' not found in the data. Available columns: {', '.join(df.columns)}")
        return None
    
    # Create new columns for latitude and longitude
    df['latitude'] = None
    df['longitude'] = None
    
    with st.spinner('Geocoding addresses... This may take a while.'):
        progress_bar = st.progress(0)
        for i, row in df.iterrows():
            address = row[address_column]
            if pd.isna(address) or address == '':
                continue
                
            try:
                g = geocoder.osm(address)
                if g.ok:
                    df.at[i, 'latitude'] = g.lat
                    df.at[i, 'longitude'] = g.lng
                else:
                    st.warning(f"Could not geocode address: {address}")
            except Exception as e:
                st.warning(f"Error geocoding address '{address}': {e}")
            
            # Update progress
            progress_bar.progress((i + 1) / len(df))
    
    # Drop rows with missing coordinates
    df_clean = df.dropna(subset=['latitude', 'longitude'])
    
    if len(df_clean) == 0:
        st.error("No valid coordinates found after geocoding")
        return None
        
    return df_clean

# Function to create heatmap
def create_heatmap(df, address_column):
    # Create a map centered around the mean coordinates
    center_lat = df['latitude'].mean()
    center_lng = df['longitude'].mean()
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=10)
    
    # Add heatmap layer
    heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]
    HeatMap(heat_data).add_to(m)
    
    # Add markers for each location with job details
    for _, row in df.iterrows():
        # Create popup content with relevant job information
        popup_html = f"""
        <div style="width: 300px">
            <h4>{row.get('Title', 'Job')}</h4>
            <p><b>Location:</b> {row.get(address_column, '')}</p>
        """
        
        # Add other relevant columns to popup
        for col in df.columns:
            if col not in ['latitude', 'longitude', 'Title', address_column] and not pd.isna(row[col]) and row[col] != '':
                popup_html += f"<p><b>{col}:</b> {row[col]}</p>"
                
        popup_html += "</div>"
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(icon="briefcase", prefix="fa")
        ).add_to(m)
    
    return m

# Main app logic
def main():
    # Default Google Sheets CSV URL
    default_csv_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"
    csv_url = default_csv_url
    
    # Load data automatically
    with st.spinner("Loading data from Google Sheets..."):
        df = load_data(csv_url)
    
    if df is not None:
        st.success(f"Data loaded successfully with {len(df)} rows")
        
        # Display the raw data
        with st.expander("Show raw data"):
            st.dataframe(df)
        
        # Automatically determine the address column
        address_column = None
        
        # First try to find a column called exactly "Address"
        if "Address" in df.columns:
            address_column = "Address"
        else:
            # Try to find columns with "address" in the name (case insensitive)
            address_cols = [col for col in df.columns if "address" in col.lower()]
            if address_cols:
                address_column = address_cols[0]
            else:
                # Try to find columns with "location" in the name
                location_cols = [col for col in df.columns if "location" in col.lower()]
                if location_cols:
                    address_column = location_cols[0]
        
        # If we still don't have an address column, let the user select one
        if not address_column:
            st.warning("Could not automatically detect the address column.")
            address_column = st.selectbox(
                "Please select the column containing address information:", 
                options=df.columns.tolist()
            )
        else:
            st.info(f"Using '{address_column}' as the address column")
        
        # Automatically geocode the addresses
        with st.spinner("Geocoding addresses..."):
            geocoded_df = geocode_addresses(df, address_column)
        
        if geocoded_df is not None:
            # Show stats
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Jobs", len(df))
            col2.metric("Geocoded Locations", len(geocoded_df))
            col3.metric("Success Rate", f"{len(geocoded_df)/len(df)*100:.1f}%")
            
            # Create and display the map
            st.subheader("Job Locations Heatmap")
            map_obj = create_heatmap(geocoded_df, address_column)
            folium_static(map_obj, width=1200, height=600)
            
            # Show the geocoded data
            with st.expander("Show geocoded data"):
                st.dataframe(geocoded_df)
                
            # Add download button for geocoded data
            csv = geocoded_df.to_csv(index=False)
            st.download_button(
                label="Download geocoded data as CSV",
                data=csv,
                file_name="geocoded_job_locations.csv",
                mime="text/csv",
            )
    else:
        st.error("Failed to load data from Google Sheets. Please check the URL or try again later.")

if __name__ == "__main__":
    main()
