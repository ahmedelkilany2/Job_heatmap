import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# Initialize Streamlit App
st.title("Job Listings Map")

# File Upload
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file:
    # Read CSV
    df = pd.read_csv(uploaded_file)

    # Display Raw Data
    st.subheader("Raw Data")
    st.dataframe(df.head())

    # Ensure 'address' column exists
    if "address" not in df.columns:
        st.error("🚨 The CSV file must contain an 'address' column!")
    else:
        # Geolocator Setup
        geolocator = Nominatim(user_agent="job_locator")

        @st.cache_data(ttl=14400)  # Cache geocoded results
        def geocode_location(address):
            """Convert address to latitude & longitude using Photon, ensuring a single valid result."""
            try:
                full_address = f"{address}, Australia"  # Ensure correct region
                location_data = geolocator.geocode(full_address, timeout=10)

                if isinstance(location_data, list):  # If multiple results, take the first one
                    location_data = location_data[0]

                if location_data:
                    return location_data.latitude, location_data.longitude

            except (GeocoderTimedOut, GeocoderServiceError):
                st.warning(f"⚠️ Geocoding timed out for {address}. Retrying in 2 seconds...")
                time.sleep(2)
                return geocode_location(address)
            except Exception as e:
                st.warning(f"⚠️ Geocoding failed for {address}: {str(e)}")

            return None, None  # Return None if geocoding fails

        # Apply Geocoding to Address Column
        st.subheader("Geocoding Job Locations")
        if "latitude" not in df.columns or "longitude" not in df.columns:
            df["latitude"], df["longitude"] = zip(*df["address"].apply(geocode_location))

        # Drop rows where geocoding failed
        df = df.dropna(subset=["latitude", "longitude"])

        # Display Data with Coordinates
        st.subheader("Processed Data with Coordinates")
        st.dataframe(df)

        # Save Processed Data (Optional)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Processed CSV", csv, "processed_jobs.csv", "text/csv")
