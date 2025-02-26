import pandas as pd
import folium
from folium.plugins import HeatMap
import geocoder
import requests
from io import StringIO
import webbrowser
import os
import time

def load_data_from_google_sheets_csv(csv_url):
    """Load data from Google Sheets CSV export URL"""
    try:
        # Use the CSV export URL directly
        response = requests.get(csv_url)
        response.encoding = 'utf-8'  # Ensure proper encoding
        
        if response.status_code == 200:
            # Read CSV data
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            
            # Check if 'Suburb' column exists
            if 'Suburb' not in df.columns:
                # Try to find a column that might contain suburb information
                potential_columns = [col for col in df.columns if 'suburb' in col.lower() or 'location' in col.lower()]
                
                if potential_columns:
                    print(f"'Suburb' column not found. Using '{potential_columns[0]}' instead.")
                    df = df.rename(columns={potential_columns[0]: 'Suburb'})
                else:
                    print("Error: The spreadsheet does not contain a 'Suburb' column.")
                    print("Available columns:", df.columns.tolist())
                    return None
            
            return df
        else:
            print(f"Error accessing the CSV: HTTP Status {response.status_code}")
            return None
    
    except Exception as e:
        print(f"Error loading data from Google Sheets CSV: {str(e)}")
        return None

def geocode_suburbs(suburbs):
    """Geocode suburbs to get latitude and longitude"""
    locations = {}
    total = len(suburbs)
    
    print(f"Geocoding {total} suburbs...")
    
    for i, suburb in enumerate(suburbs):
        # Skip empty suburbs
        if pd.isna(suburb) or suburb == "":
            continue
            
        # Add Australia to improve geocoding accuracy if not already specified
        if "VIC" not in str(suburb) and "Australia" not in str(suburb):
            search_term = f"{suburb}, Australia"
        else:
            search_term = suburb
        
        # Print progress
        print(f"Geocoding ({i+1}/{total}): {search_term}")
            
        # Try geocoding with OSM (doesn't require API key)
        g = geocoder.osm(search_term)
            
        # If we get coordinates, save them
        if g.latlng:
            locations[suburb] = g.latlng
            print(f"  Found: {g.latlng}")
        else:
            # Try with more specific search
            g = geocoder.osm(f"{suburb}, Melbourne, Australia")
            if g.latlng:
                locations[suburb] = g.latlng
                print(f"  Found with Melbourne context: {g.latlng}")
            else:
                print(f"  Could not geocode: {suburb}")
                
        # Small delay to avoid overwhelming the geocoding service
        time.sleep(0.5)
    
    print(f"Successfully geocoded {len(locations)} out of {total} suburbs")
    return locations

def create_heatmap(geocoded_data, suburb_counts):
    """Create a heatmap based on geocoded data and suburb frequencies"""
    # Create a base map centered on Australia (Melbourne focus)
    m = folium.Map(location=[-37.8136, 144.9631], zoom_start=10)
    
    # Create a list of [lat, lng, intensity] for each location
    heat_data = []
    for suburb, (lat, lng) in geocoded_data.items():
        # Count occurrences of each suburb (frequency becomes heat intensity)
        count = suburb_counts[suburb]
        heat_data.append([lat, lng, count])
    
    # Add the heatmap layer to the map
    HeatMap(heat_data, radius=15, blur=10, max_zoom=13).add_to(m)
    
    # Add a title
    title_html = '''
        <h3 align="center" style="font-size:16px"><b>Job Locations Heatmap in Australia</b></h3>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add a legend
    legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 150px; height: 90px; 
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white;
                    padding: 10px">
          <b>Job Frequency</b><br>
          <i style="background: red; opacity: 0.7"></i> High<br>
          <i style="background: orange; opacity: 0.7"></i> Medium<br>
          <i style="background: green; opacity: 0.7"></i> Low
        </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def save_frequency_data(suburb_counts, filename="suburb_frequencies.csv"):
    """Save suburb frequency data to CSV"""
    freq_df = pd.DataFrame(list(suburb_counts.items()), columns=['Suburb', 'Job Count'])
    freq_df = freq_df.sort_values('Job Count', ascending=False)
    freq_df.to_csv(filename, index=False)
    print(f"Suburb frequency data saved to {filename}")
    return freq_df

def main():
    """Main function to run the heatmap generation"""
    print("Australian Job Locations Heatmap")
    print("--------------------------------")
    
    # URL of the Google Sheets CSV export
    csv_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"
    print(f"Loading data from: {csv_url}")
    
    # Load data from Google Sheets CSV
    df = load_data_from_google_sheets_csv(csv_url)
    
    if df is not None:
        print(f"Loaded {len(df)} rows of data")
        
        # Handle potential non-string values
        df['Suburb'] = df['Suburb'].astype(str)
        suburbs = df['Suburb'].unique().tolist()
        suburb_counts = df['Suburb'].value_counts().to_dict()
        
        print(f"Found {len(suburbs)} unique suburbs")
        
        # Geocode the suburbs
        geocoded_suburbs = geocode_suburbs(suburbs)
        
        if geocoded_suburbs:
            # Save frequency data
            freq_df = save_frequency_data(suburb_counts)
            print("\nTop 10 suburbs by job count:")
            print(freq_df.head(10))
            
            # Create and save the heatmap
            print("\nCreating heatmap...")
            heatmap = create_heatmap(geocoded_suburbs, suburb_counts)
            
            # Save the map as an HTML file
            map_filename = "australian_job_heatmap.html"
            heatmap.save(map_filename)
            print(f"Heatmap saved as {map_filename}")
            
            # Open the map in a web browser
            print(f"Opening heatmap in web browser...")
            webbrowser.open('file://' + os.path.realpath(map_filename))
        else:
            print("Error: Could not geocode any suburbs. Please check your data.")
    else:
        print("Error: Failed to load data. Please check the URL and try again.")

if __name__ == "__main__":
    main()
