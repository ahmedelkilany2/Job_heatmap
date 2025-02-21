import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
import time

# Prevent Streamlit from sleeping
def keep_alive():
    while True:
        time.sleep(300)  # Keeps running every 5 minutes

# Google Sheets URL (converted to CSV format)
sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/edit?gid=0#gid=0"

@st.cache_data
def load_data():
    try:
        # Fetch data from Google Sheets
        response = requests.get(sheet_url)
        response.raise_for_status()  # Raise error for failed requests
        
        # Read CSV data
        df = pd.read_csv(sheet_url)
        
        # Set first column as index
        df = df.set_index(df.columns[0])
        
        # Convert to numeric (handling errors)
        df = df.apply(pd.to_numeric, errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Streamlit UI
st.title("📊 Google Sheets Heatmap")
st.write("This heatmap visualizes the data from the provided Google Sheet.")

# Load data
df = load_data()

if df is not None:
    st.write("### 🔹 Data Preview")
    st.dataframe(df)

    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(df, annot=True, cmap="coolwarm", linewidths=0.5, fmt=".1f", ax=ax)
    st.pyplot(fig)
else:
    st.warning("No data available. Please check the Google Sheets link.")

# Run the keep-alive function in the background
import threading
threading.Thread(target=keep_alive, daemon=True).start()
