import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import os

# --- 1. Streamlit page configuration ---
st.set_page_config(
    page_title="Adzuna Job Scraping Analysis",
    page_icon="📊",
    layout="wide",
)

# Title and description
st.title("Adzuna Job Scraping Analysis - Australia 📊")
st.markdown("Interactive dashboard to analyze job postings data.")



# --- 2. Data Loading ---

# Google Sheets CSV URL
sheet_url = "https://docs.google.com/spreadsheets/d/1VTMPy-dvropKZANZeMJMxfuRmFrAYJ2YFC1kbLznT9Q/export?format=csv"

# データの読み込み (キャッシュ)
@st.cache_data
def load_data():
    """Loads data from Google Sheets CSV URL."""
    try:
        df = pd.read_csv(sheet_url)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


# --- 3. Plotting Functions ---
# --- Chart 1 ---
def plot_total_job_postings(df):
    """Displays the total number of job postings as a metric."""
    if df is None:
        st.warning("Cannot display total job postings: Data loading failed.")
        return
    total_jobs = len(df)
    st.metric(label=" ", value=total_jobs)

# --- Chart 2 ---
def plot_average_salary_by_contract_type(df):
    """Plots the average salary by contract type using Altair."""
    if df is None:
        st.warning("Cannot plot salary data: Data loading failed.")
        return

    try:
        df["salary_min"] = pd.to_numeric(df["salary_min"], errors="coerce")
        df["salary_max"] = pd.to_numeric(df["salary_max"], errors="coerce")
    except KeyError as e:
        st.error(f"Error: Required salary columns '{e}' not found. Check your Google Sheet column names.")
        return

    df_cleaned = df.dropna(subset=["salary_min", "salary_max"])

    if df_cleaned.empty:
        st.warning("No valid salary data to plot.")
        return

    stats = df_cleaned.groupby("contract_type").agg(
        avg_salary=("salary_min", "mean")
    ).reset_index()  # Reset index for Altair

    chart = alt.Chart(stats).mark_bar().encode(
        x=alt.X('contract_type:N', title="Contract Type"),
        y=alt.Y('avg_salary:Q', title="Average Salary ($)"),
        tooltip=['contract_type', 'avg_salary']
    ).properties(
        title=" "
    )
    st.altair_chart(chart, use_container_width=True)

# --- Chart 3 ---
def plot_contract_time_distribution(df):
    """Plots the distribution of job postings by contract time using Plotly."""
    if df is None:
        st.warning("Cannot plot distribution: Data loading failed.")
        return

    contract_time_counts = df['contract_time'].value_counts().reset_index()
    contract_time_counts.columns = ['contract_time', 'count'] # Rename for Plotly Express

    fig = px.bar(contract_time_counts, x='contract_time', y='count',
                 labels={'contract_time': 'Contract Time', 'count': 'Number of Job Postings'})
    st.plotly_chart(fig, use_container_width=True)

# --- Chart 4 ---
def plot_contract_type_distribution(df):
    """Plots the distribution of job postings by contract type using Plotly."""
    if df is None:
        st.warning("Cannot plot distribution: Data loading failed.")
        return

    contract_type_counts = df['contract_type'].value_counts().reset_index()
    contract_type_counts.columns = ['contract_type', 'count'] # Rename for Plotly Express

    fig = px.pie(contract_type_counts, values='count', names='contract_type',)
    st.plotly_chart(fig, use_container_width=True)

# --- Chart 5 ---
def plot_job_density_heatmap(df):
    """Plots the job density heatmap using Plotly."""
    if df is None:
        st.warning("Cannot plot job density: Data loading failed.")
        return

    try:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    except KeyError as e:
        st.error(f"Error: Required location columns '{e}' not found. Check your Google Sheet column names.")
        return #Do not proceed

    df_cleaned = df.dropna(subset=["latitude", "longitude"])

    if df_cleaned.empty:
        st.warning("No valid location data to plot heatmap.")
        return

    fig = px.density_mapbox(df_cleaned, lat='latitude', lon='longitude', z=None, radius=10,
                            center=dict(lat=-25, lon=133), zoom=2, #approximate center of Australia
                            mapbox_style="carto-positron", #Or other styles, like "open-street-map"
                            height = 600)
    st.plotly_chart(fig, use_container_width=True)




# --- 4. Main App ---
df = load_data()

if df is not None:
    # Print DataFrame (for debugging/ viewing purpose):
    st.write("First few rows of DataFrame:")
    st.dataframe(df.head())

# --- Creating dropdown filtering sidebar ---
    st.sidebar.header("Filters")

    try:
        contract_type_options = df['contract_type'].unique()
        contract_time_options = df['contract_time'].unique()
        category_options = df['category'].unique() 
    except KeyError as e:
        st.error(f"Error: Column '{e}' not found in DataFrame. Check your Google Sheet column names and code.  The available columns are in the dataframe preview above.")
        st.stop()
        contract_type_options = []
        contract_time_options = []
        category_options = []

    contract_type_filter = st.sidebar.multiselect(
        "Contract Type", options=contract_type_options, default=contract_type_options
    )
    contract_time_filter = st.sidebar.multiselect(
        "Contract Time", options=contract_time_options, default=contract_time_options
    )

    category_filter = st.sidebar.multiselect( 
        "Industry", options=category_options, default = category_options
    )

    # --- Data Filtering ---
    filtered_df = df[
        df['contract_type'].isin(contract_type_filter)
        & df['contract_time'].isin(contract_time_filter)
        & df['category'].isin(category_filter)
    ]

    # Check that there are rows in the filtered dataframe:
    if not filtered_df.empty:
        # --- Main Area Dashboard Layout (organize the charts)---
        col1, col2, col3 = st.columns(3)  # Creates three columns, it will devide main area into 3 columns

        with col1:
            st.subheader("Total Job Postings")
            plot_total_job_postings(filtered_df) 
            st.subheader("Contract Type Distribution ")
            plot_contract_type_distribution(filtered_df)
            # add more charts

        with col2:
            st.subheader("Contract Time Distribution")
            plot_contract_time_distribution(filtered_df)
            # add more charts

        with col3:
            st.subheader("Average Salary by Contract Type")
            plot_average_salary_by_contract_type(filtered_df)

        # if you want more colmn just increas number and repeat same with col4:....

        st.subheader("Job Posting Density Heatmap")  # This chart will be plotted across col1 to col3
        plot_job_density_heatmap(filtered_df)

        # Raw Data Display (moved outside columns):
        if st.checkbox("Show Raw Data"):
            st.subheader("Raw Data")
            st.dataframe(filtered_df)
    else:
        st.warning("No data matches your selection. Change the filters!")
else:
    st.warning("Data loading failed. Please check the credentials file path and Google Sheet.")
