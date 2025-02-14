import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import urllib.error

# Set page title
st.set_page_config(page_title="Job Heatmap", layout="wide")

# Google Sheets CSV URL (Ensure it's public: "Anyone with the link can view")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/gviz/tq?tqx=out:csv&gid=0"

@st.cache_data
def fetch_data():
    """Fetches job data from Google Sheets with error handling."""
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except urllib.error.HTTPError as e:
        st.error(f"⚠️ HTTP Error {e.code}: Check Google Sheets permissions.")
        return None
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {str(e)}")
        return None

# Load data
df = fetch_data()

if df is not None:
    st.write("✅ **Data Loaded Successfully!**")
    
    # Display first few rows
    st.dataframe(df.head())

    # Ensure data contains expected columns
    required_columns = ["Job Title", "Location", "Count"]
    if all(col in df.columns for col in required_columns):

        # Pivot table for heatmap
        heatmap_data = df.pivot(index="Job Title", columns="Location", values="Count").fillna(0)

        # Create heatmap
        st.subheader("📊 Job Distribution Heatmap")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(heatmap_data, cmap="coolwarm", annot=True, fmt=".0f", linewidths=0.5)
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning("⚠ The dataset must contain 'Job Title', 'Location', and 'Count' columns.")

else:
    st.warning("⚠ No data found. Please check your Google Sheet URL or permissions.")
