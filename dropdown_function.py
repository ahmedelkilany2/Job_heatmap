import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# --- 1. Streamlit page configuration ---
st.set_page_config(
    page_title="Adzuna Job Scraping Analysis",
    page_icon="📊",
    layout="wide",
)

# Title and description
st.title("Adzuna Job Scraping Analysis - Australia 📊")
st.markdown("This is an interactive dashboard to analyze job postings data scraped from Adzuna website.")

# --- 2. Data Loading ---
# Google Sheets CSV URL
sheet_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/export?format=csv&gid=553613618"

# Cache
@st.cache_data
def load_data():
    """Loads data from Google Sheets CSV URL."""
    try:
        # Load the data
        df = pd.read_csv(sheet_url)
        
        # First, show a preview of the DataFrame columns to help with debugging
        st.sidebar.write("Available columns:", df.columns.tolist())
        
        # Validate required columns exist
        required_columns = ['latitude', 'longitude', 'category', 'contract_type', 'contract_time', 'Day', 'salary_min', 'salary_max']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Error: Missing required columns: {', '.join(missing_columns)}")
            st.error("Please ensure your Google Sheet has all required columns.")
            return None
            
        # Convert latitude and longitude to numeric, handling errors
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        
        # Remove rows with NaN values in latitude or longitude
        df = df.dropna(subset=['latitude', 'longitude'])
        
        if df.empty:
            st.warning("No valid location data found after cleaning.")
            return None
            
        # Convert salary columns to numeric if they exist
        if 'salary_min' in df.columns and 'salary_max' in df.columns:
            df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce')
            df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce')
        
        return df
        
    except pd.errors.EmptyDataError:
        st.error("The CSV file is empty.")
        return None
    except FileNotFoundError:
        st.error("Could not access the Google Sheet. Please check the URL.")
        return None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.error("Please verify the Google Sheet URL and ensure it's publicly accessible.")
        return None

# --- 3. Plotting Functions ---
# --- Chart 1 ---
def plot_total_job_postings(df_full, df):
    """Displays the total number of job postings as a metric and the percentage of filtered jobs."""
    if df_full is None:
        st.warning("Cannot display total job postings: Data loading failed.")
        return

    total_jobs_full = len(df_full)
    total_jobs = len(df)
    percentage_filtered = (total_jobs / total_jobs_full) * 100 if total_jobs_full > 0 else 0

    st.metric(
        label="Total Job Postings 💼",
        value=f"{total_jobs} out of   {total_jobs_full}",
        delta=f"{percentage_filtered:.2f}%",
    )

# --- Chart 2 ---
def plot_job_density_heatmap(df):
    """Plots a heatmap using Folium."""
    if df is None:
        st.warning("Cannot plot heatmap: Data loading failed.")
        return

    if df.empty:
        st.warning("No valid location data to plot heatmap.")
        return

    location_data = list(zip(df['latitude'], df['longitude']))

    # Create a map centered on Australia
    map_center = [-25.2744, 133.7751]
    job_map = folium.Map(location=map_center, zoom_start=4)

    # Add HeatMap
    HeatMap(location_data, radius=15, blur=10).add_to(job_map)

    # Display the map using streamlit-folium
    st_folium(job_map, height=600, width=1200)

# --- Chart 3 ---
def plot_job_postings_by_categories(df):
    """Plots the top 10 job categories in descending order."""
    if df is None:
        st.warning("Cannot plot category data: Data loading failed.")
        return

    category_counts = df['category'].value_counts().reset_index()
    category_counts.columns = ['category', 'count']

    fig = px.bar(category_counts, x='count', y='category',
                 labels={'count': 'Number of Jobs', 'category': 'Category'},
                 color='category')  # Add color for better visualization

    fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=1200, showlegend=False) # Sort in descending order

    st.plotly_chart(fig, use_container_width=True)

# --- Chart 4 & 5 ---
def make_donut(input_response, input_text, input_color):
    """This is creating donuts chart function for later Chart 4 and 5"""
    if input_color == 'blue':
        chart_color = ['#29b5e8', '#155F7A']
    elif input_color == 'green':
        chart_color = ['#27AE60', '#12783D']
    elif input_color == 'orange':
        chart_color = ['#F39C12', '#875A12']
    elif input_color == 'red':
        chart_color = ['#E74C3C', '#781F16']
    else:
        chart_color = ['#AAAAAA', '#555555']  # Default gray

    source = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100-input_response, input_response]
    })
    source_bg = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100, 0]
    })

    plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=25).encode(
        theta="% value",
        color= alt.Color("Topic:N",
                        scale=alt.Scale(
                            domain=[input_text, ''],
                            range=chart_color),
                        legend=None),
    ).properties(width=130, height=130)

    text = plot.mark_text(align='center', color=chart_color[0], font="Lato", fontSize=32, fontWeight=700, fontStyle="italic").encode(text=alt.value(f'{input_response} %'))
    plot_bg = alt.Chart(source_bg).mark_arc(innerRadius=45, cornerRadius=20).encode(
        theta="% value",
        color= alt.Color("Topic:N",
                        scale=alt.Scale(
                            domain=[input_text, ''],
                            range=chart_color),
                        legend=None),
    ).properties(width=130, height=130)
    return plot_bg + plot + text

def plot_contract_time_donuts(df):
    """Plots separate donut charts for Full-Time and Part-Time contract times."""
    if df is None:
        st.warning("Cannot plot contract time donuts: Data loading failed.")
        return

    # Calculate percentages for Full-Time
    full_time_count = len(df[df['contract_time'] == 'full_time'])
    total_count = len(df)
    full_time_percentage = (full_time_count / total_count) * 100 if total_count > 0 else 0

    # Calculate percentages for Part-Time
    part_time_count = len(df[df['contract_time'] == 'part_time'])
    part_time_percentage = (part_time_count / total_count) * 100 if total_count > 0 else 0

    # Create donut charts
    full_time_donut = make_donut(round(full_time_percentage,1), "Full-Time", "blue")
    part_time_donut = make_donut(round(part_time_percentage,1), "Part-Time", "red")

    # Display the charts using columns for better layout
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Full-Time")
        st.altair_chart(full_time_donut, use_container_width=True)
    with col2:
        st.subheader("Part-Time")
        st.altair_chart(part_time_donut, use_container_width=True)

def plot_contract_type_donuts(df):
    """Plots separate donut charts for Contract and Permanent contract types."""
    if df is None:
        st.warning("Cannot plot contract type donuts: Data loading failed.")
        return

    # Calculate percentages for Contract
    contract_count = len(df[df['contract_type'] == 'contract'])
    total_count = len(df)
    contract_percentage = (contract_count / total_count) * 100 if total_count > 0 else 0

    # Calculate percentages for Permanent
    permanent_count = len(df[df['contract_type'] == 'permanent'])
    permanent_percentage = (permanent_count / total_count) * 100 if total_count > 0 else 0

    # Create donut charts
    contract_donut = make_donut(round(contract_percentage,1), "Contract", "blue")
    permanent_donut = make_donut(round(permanent_percentage,1), "Permanent", "red")

    # Display the charts using columns for better layout
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Contract")
        st.altair_chart(contract_donut, use_container_width=True)
    with col2:
        st.subheader("Permanent")
        st.altair_chart(permanent_donut, use_container_width=True)

# --- Chart 6 ---
def plot_total_jobs_by_day(df):
    """
    Plots the total number of job postings by day of the week using Plotly Express.
    """
    if df is None:
        st.warning("Cannot plot total jobs by day: Data loading failed.")
        return

    # Group by day of the week and count the postings
    day_counts = df['Day'].value_counts().reset_index()
    day_counts.columns = ['Day', 'count']

    # Order days of the week
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_counts['Day'] = pd.Categorical(day_counts['Day'], categories=day_order, ordered=True)
    day_counts = day_counts.sort_values('Day')

    # Create the Plotly Express bar chart
    fig = px.bar(
        day_counts,
        x='Day',
        y='count',
        labels={'Day': 'Day of the Week', 'count': 'Number of Job Postings'},
        color='Day',  # Add color based on the Day
        height = 300
    )

    # Remove the legend (side guide)
    fig.update_layout(showlegend=False)  # Add this line to remove the legend

    st.plotly_chart(fig, use_container_width=True)

# --- Chart 7 ---
def plot_salary_range_by_category(df):
    """Plots the salary range by top 10 job categories using a box plot."""
    if df is None:
        st.warning("Cannot plot salary range by category: Data loading failed.")
        return

    # Data Cleaning: Remove rows with missing salary information
    df_cleaned = df.dropna(subset=['salary_min', 'salary_max', 'category'])

    # Convert salary columns to numeric (handle potential errors)
    try:
        df_cleaned['salary_min'] = pd.to_numeric(df_cleaned['salary_min'])
        df_cleaned['salary_max'] = pd.to_numeric(df_cleaned['salary_max'])
    except ValueError:
        st.error("Could not convert salary columns to numeric.  Check your data.")
        return # Stop if there's a conversion error

    # Calculate average salary
    df_cleaned['average_salary'] = (df_cleaned['salary_min'] + df_cleaned['salary_max']) / 2

    # Get top 10 categories based on job posting count
    top_10_categories = df_cleaned['category'].value_counts().nlargest(10).index.tolist()

    # Filter the DataFrame to include only the top 10 categories
    df_top_10 = df_cleaned[df_cleaned['category'].isin(top_10_categories)]

    # Calculate median salary for sorting
    median_salaries = df_top_10.groupby('category')['average_salary'].median().sort_values(ascending=False)

    # Create an ordered list of categories for sorting the x-axis
    category_order = list(median_salaries.index)

    # Create the Altair box plot
    chart = alt.Chart(df_top_10).mark_boxplot().encode(
        y=alt.Y('category:N', title='Job Category', sort=category_order),  # Sort by median salary
        x=alt.X('average_salary:Q', title='Average Salary', scale=alt.Scale(zero=False)),  # Set zero=False for better visualization
        tooltip=['category', 'salary_min', 'salary_max', 'average_salary']
    ).properties(
        height = 500
    )

    st.altair_chart(chart, use_container_width=True)


# --- 4. Main App ---
df_full = load_data()  # this is to load and store whole dataset without filtering

if df_full is not None:

    # --- Creating dropdown filtering sidebar ---
    st.sidebar.header("Filters")

    try:
        category_options = df_full['category'].unique().tolist() # Convert to list
        contract_type_options = df_full['contract_type'].unique().tolist()  # Convert to list
        contract_time_options = df_full['contract_time'].unique().tolist()  # Convert to list
    except KeyError as e:
        st.error(f"Error: Column '{e}' not found in DataFrame. Check your Google Sheet column names and code.  The available columns are in the dataframe preview above.")
        st.stop()
        category_options = []
        contract_type_options = []
        contract_time_options = []

    # 'All' option to each filter
    category_options = ['All'] + category_options
    contract_type_options = ['All'] + contract_type_options
    contract_time_options = ['All'] + contract_time_options

    
    category_filter = st.sidebar.multiselect(
        "Category", options=category_options, default=['All']
    )

    contract_type_filter = st.sidebar.multiselect(
        "Contract Type", options=contract_type_options, default=['All']
    )
    contract_time_filter = st.sidebar.multiselect(
        "Contract Time", options=contract_time_options, default=['All']
    )

    # --- Data Filtering ---
    def filter_dataframe(df, contract_type, contract_time, category):
        """Filters the DataFrame based on selected options."""
        df_filtered = df.copy()

        if 'All' not in category:
            df_filtered = df_filtered[df_filtered['category'].isin(category)]

        if 'All' not in contract_type:
            df_filtered = df_filtered[df_filtered['contract_type'].isin(contract_type)]

        if 'All' not in contract_time:
            df_filtered = df_filtered[df_filtered['contract_time'].isin(contract_time)]

        return df_filtered

    filtered_df = filter_dataframe(df_full, contract_type_filter, contract_time_filter, category_filter)



    # Check that there are rows in the filtered dataframe:
    if not filtered_df.empty:
        # --- Main Area Dashboard Layout (organize the charts)---
        col1, col2, col3 = st.columns([2, 4, 2])  # You can adjust the proportions of the columns

        with col1:
            st.subheader("Total Job Postings 💼")
            plot_total_job_postings(df_full, filtered_df)
            st.subheader("Total Job Postings by day")
            plot_total_jobs_by_day(filtered_df)
            st.subheader("Contract Time")
            plot_contract_time_donuts(filtered_df)
            st.subheader("Contract Type")
            plot_contract_type_donuts(filtered_df)
            # add more charts

        with col2:
            st.subheader("Job Posting Density Heatmap 🔍")  
            plot_job_density_heatmap(filtered_df)
            st.subheader("Top 10 Salary and its Range")
            plot_salary_range_by_category(filtered_df)
            # add more charts

        with col3:
            st.subheader("Total Job Postings Job Categories")
            plot_job_postings_by_categories(filtered_df)

        # if you want more colmn just increas number and repeat same with col4: but each colmn will be bit narrow....

        # This chart will be plotted across col1 to col3
        if st.checkbox("Show Raw Data"):
            st.subheader("Raw Data")
            st.dataframe(filtered_df)
    else:
        st.warning("No data matches your selection. Change the filters!")

else:
    st.warning("Data loading failed. Please check the credentials file path and Google Sheet.")
