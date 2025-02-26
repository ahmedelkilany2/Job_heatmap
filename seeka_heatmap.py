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
st.set_page_config(page_title="Australian Job Locations Heatmap", layout="wide")
st.title("Australian Job Locations Heatmap")

# Function to load data from the direct Google Sheets CSV link
@st.cache_data
def load_data(csv_url):
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Improve address for geocoding with Australian context
def prepare_australian_address(address):
    if pd.isna(address) or address == '':
        return None
        
    # Ensure "Australia" is in the address
    if "australia" not in address.lower():
        address = f"{address}, Australia"
        
    # Handle Victoria abbreviation
    if " VIC " in address and not " Victoria " in address:
        address = address.replace(" VIC ", " Victoria ")
        
    return address

# Function to geocode addresses with focus on Australia
@st.cache_data
def geocode_australian_addresses(df, address_column):
    if address_column not in df.columns:
        st.error(f"Column '{address_column}' not found in the data. Available columns: {', '.join(df.columns)}")
        return None
    
    # Create new columns for latitude and longitude
    df['latitude'] = None
    df['longitude'] = None
    df['geocoded_address'] = None
    
    # Set bounds for Australia to improve geocoding accuracy
    australia_bounds = {
        'min_lon': 113.338953078,
        'max_lon': 153.569469029,
        'min_lat': -43.6345972634,
        'max_lat': -10.6681857235
    }
    
    # List to store successfully geocoded rows
    geocoded_rows = []
    
    with st.spinner('Geocoding Australian addresses... This may take a while.'):
        progress_bar = st.progress(0)
        total_rows = len(df)
        
        for i, row in df.iterrows():
            # Get address and prepare it
            address = prepare_australian_address(row[address_column])
            if not address:
                continue
                
            try:
                # First try with Nominatim (OSM) with Australia as region
                g = geocoder.osm(address, country='Australia')
                
                # If that fails, try with Google (if API key available)
                if not g.ok and os.getenv('GOOGLE_API_KEY'):
                    g = geocoder.google(address, key=os.getenv('GOOGLE_API_KEY'))
                
                # If that fails too, try ArcGIS
                if not g.ok:
                    g = geocoder.arcgis(address)
                
                if g.ok:
                    # Verify the coordinates are within Australia
                    if (australia_bounds['min_lat'] <= g.lat <= australia_bounds['max_lat'] and 
                        australia_bounds['min_lon'] <= g.lng <= australia_bounds['max_lon']):
                        
                        # Create a copy of the row
                        geocoded_row = row.copy()
                        geocoded_row['latitude'] = g.lat
                        geocoded_row['longitude'] = g.lng
                        geocoded_row['geocoded_address'] = g.address
                        
                        # Add to our list of geocoded rows
                        geocoded_rows.append(geocoded_row)
                    else:
                        st.warning(f"Geocoded coordinates for '{address}' are outside Australia")
                else:
                    st.warning(f"Could not geocode address: {address}")
            except Exception as e:
                st.warning(f"Error geocoding address '{address}': {e}")
            
            # Update progress
            progress_bar.progress((i + 1) / total_rows)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.2)
    
    # If we have geocoded rows, create a new dataframe
    if geocoded_rows:
        geocoded_df = pd.DataFrame(geocoded_rows)
        return geocoded_df
    else:
        st.error("No valid coordinates found after geocoding")
        return None

# Function to create heatmap
def create_heatmap(df, address_column):
    # Create a map centered around the mean coordinates
    # Default to Victoria, Australia if no coordinates
    center_lat = df['latitude'].mean() if not df['latitude'].empty else -37.8136
    center_lng = df['longitude'].mean() if not df['longitude'].empty else 144.9631
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=10)
    
    # Add heatmap layer
    heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]
    HeatMap(heat_data).add_to(m)
    
    # Add markers for each location with job details
    for _, row in df.iterrows():
        # Create popup content with relevant job information
        popup_html = f"""
        <div style="width: 300px">
            <h4>{row.get('Title', 'Job Location')}</h4>
            <p><b>Original Address:</b> {row.get(address_column, '')}</p>
            <p><b>Geocoded Address:</b> {row.get('geocoded_address', '')}</p>
        """
        
        # Add other relevant columns to popup
        for col in df.columns:
            if col not in ['latitude', 'longitude', 'Title', address_column, 'geocoded_address'] and not pd.isna(row[col]) and row[col] != '':
                popup_html += f"<p><b>{col}:</b> {row[col]}</p>"
                
        popup_html += "</div>"
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(icon="briefcase", prefix="fa")
        ).add_to(m)
    
    return m

# Function to extract or create an address column from the data
def process_address_column(df):
    # First check if we already have an Address column
    if "Address" in df.columns:
        return "Address", df
    
    # Try to find columns with "address" in the name (case insensitive)
    address_cols = [col for col in df.columns if "address" in col.lower()]
    if address_cols:
        return address_cols[0], df
        
    # Look for columns with "location" in the name
    location_cols = [col for col in df.columns if "location" in col.lower()]
    if location_cols:
        return location_cols[0], df
    
    # If DataFrame has only one column, assume it contains addresses
    if len(df.columns) == 1:
        df = df.rename(columns={df.columns[0]: "Address"})
        return "Address", df
    
    # No address column found - check data to see if it looks like addresses
    # For demonstration, check the first column
    first_col = df.columns[0]
    first_values = df[first_col].dropna().astype(str)
    
    # Simple check: if values contain "VIC" or "Australia", likely addresses
    if first_values.str.contains("VIC").any() or first_values.str.contains("Australia").any():
        df = df.rename(columns={first_col: "Address"})
        return "Address", df
    
    # No address column found and couldn't determine one
    return None, df

# Main app logic
def main():
    # Default Google Sheets CSV URL
    default_csv_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"
    csv_url = default_csv_url
    
    # Add option to paste example addresses for testing
    test_mode = st.sidebar.checkbox("Use example addresses instead")
    
    if test_mode:
        example_addresses = st.sidebar.text_area(
            "Paste example addresses (one per line or as a Python list)",
            value="""['Aquila Shoes, 7 Saligna Dr, Tullamarine VIC 3043, Australia', 
'Aquila, Essendon Fields VIC 3041, Australia', 
'Aquila Shoes, Bulla Rd, Essendon VIC 3040, Australia']"""
        )
        
        if example_addresses:
            try:
                # Try to parse as Python list
                if example_addresses.strip().startswith('[') and example_addresses.strip().endswith(']'):
                    import ast
                    addresses_list = ast.literal_eval(example_addresses)
                else:
                    # Otherwise split by newline
                    addresses_list = [addr.strip() for addr in example_addresses.split('\n') if addr.strip()]
                
                # Create DataFrame from list
                df = pd.DataFrame({"Address": addresses_list})
                st.success(f"Created test dataset with {len(df)} addresses")
            except Exception as e:
                st.error(f"Error parsing addresses: {e}")
                df = None
        else:
            df = None
    else:
        # Load data automatically from Google Sheets
        with st.spinner("Loading data from Google Sheets..."):
            df = load_data(csv_url)
    
    if df is not None:
        st.success(f"Data loaded successfully with {len(df)} rows")
        
        # Display the raw data
        with st.expander("Show raw data"):
            st.dataframe(df)
        
        # Process to find or create address column
        address_column, df = process_address_column(df)
        
        if not address_column:
            st.warning("Could not automatically detect the address column.")
            address_column = st.selectbox(
                "Please select the column containing address information:", 
                options=df.columns.tolist()
            )
        else:
            st.info(f"Using '{address_column}' as the address column")
        
        # Automatically geocode the addresses
        with st.spinner("Geocoding addresses (this may take several minutes)..."):
            geocoded_df = geocode_australian_addresses(df, address_column)
        
        if geocoded_df is not None and not geocoded_df.empty:
            # Show stats
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Locations", len(df))
            col2.metric("Geocoded Locations", len(geocoded_df))
            col3.metric("Success Rate", f"{len(geocoded_df)/len(df)*100:.1f}%")
            
            # Create and display the map
            st.subheader("Job Locations Heatmap (Australia)")
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
                file_name="geocoded_australian_job_locations.csv",
                mime="text/csv",
            )
        else:
            st.error("Failed to geocode any addresses. Please check the address format.")
            
            # Show troubleshooting tips
            st.subheader("Troubleshooting")
            st.markdown("""
            - Make sure addresses include state (VIC, NSW, etc.) and "Australia"
            - Try adding more details to ambiguous addresses
            - Consider adding postal codes to improve geocoding
            - You may need to add a Google Maps API key for better results
            """)
            
            # Show example of a well-formatted address
            st.code("Example good address format: '7 Saligna Dr, Tullamarine VIC 3043, Australia'")
    else:
        st.error("Failed to load data. Please check the URL or try the example addresses option.")

if __name__ == "__main__":
    main()
