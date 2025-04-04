import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# Helper functions that don't use Streamlit widgets
def make_donut(input_response, input_text, input_color):
    """Creates donut chart function for Charts 4 and 5"""
    if input_color == 'blue':
        chart_color = ['#29b5e8', '#155F7A']
    elif input_color == 'green':
        chart_color = ['#27AE60', '#12783D']
    elif input_color == 'orange':
        chart_color = ['#F39C12', '#875A12']
    elif input_color == 'red':
        chart_color = ['#E74C3C', '#781F16']
    else:
        chart_color = ['#AAAAAA', '#555555']

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

@st.cache_data
def load_data():
    """Loads data from Google Sheets CSV URL."""
    # Convert edit URL to export URL
    sheet_id = "154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k"
    gid = "553613618"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        # Load the data with more robust CSV reading parameters
        df = pd.read_csv(
            sheet_url,
            on_bad_lines='warn',  # Don't fail on problematic lines
            encoding='utf-8',     # Specify encoding
            low_memory=False      # Handle large files better
        )
        
        # Rename day_of_week to Day to match the rest of the code
        if 'day_of_week' in df.columns:
            df = df.rename(columns={'day_of_week': 'Day'})
        
        # Clean up column names (remove any whitespace)
        df.columns = df.columns.str.strip()
        
        # Validate required columns exist
        required_columns = ['latitude', 'longitude', 'category', 'contract_type', 'contract_time', 'Day', 'salary_min', 'salary_max']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return None
            
        # Convert latitude and longitude to numeric, handling errors
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        
        # Remove rows with NaN values in latitude or longitude
        df = df.dropna(subset=['latitude', 'longitude'])
        
        if df.empty:
            return None
            
        # Convert salary columns to numeric if they exist
        if 'salary_min' in df.columns and 'salary_max' in df.columns:
            df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce')
            df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce')
        
        return df
        
    except Exception:
        return None

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

# Plotting functions that don't create Streamlit elements
def plot_total_job_postings(df_full, df):
    """Calculates total jobs for displaying as metric."""
    if df_full is None:
        return None, None, None

    total_jobs_full = len(df_full)
    total_jobs = len(df)
    percentage_filtered = (total_jobs / total_jobs_full) * 100 if total_jobs_full > 0 else 0
    
    return total_jobs, total_jobs_full, percentage_filtered

def create_job_density_heatmap(df):
    """Creates a heatmap using Folium without displaying it."""
    if df is None or df.empty:
        return None

    location_data = list(zip(df['latitude'], df['longitude']))

    # Create a map centered on Australia
    map_center = [-25.2744, 133.7751]
    job_map = folium.Map(location=map_center, zoom_start=4)

    # Add HeatMap
    HeatMap(location_data, radius=15, blur=10).add_to(job_map)
    
    return job_map

def create_job_postings_by_categories_chart(df):
    """Creates the category bar chart without displaying it."""
    if df is None:
        return None

    category_counts = df['category'].value_counts().reset_index()
    category_counts.columns = ['category', 'count']

    fig = px.bar(category_counts, x='count', y='category',
                 labels={'count': 'Number of Jobs', 'category': 'Category'},
                 color='category')

    fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=1200, showlegend=False)
    
    return fig

def create_contract_time_donuts(df):
    """Creates donut charts for contract times without displaying them."""
    if df is None:
        return None, None

    full_time_count = len(df[df['contract_time'] == 'full_time'])
    total_count = len(df)
    full_time_percentage = (full_time_count / total_count) * 100 if total_count > 0 else 0

    part_time_count = len(df[df['contract_time'] == 'part_time'])
    part_time_percentage = (part_time_count / total_count) * 100 if total_count > 0 else 0

    full_time_donut = make_donut(round(full_time_percentage,1), "Full-Time", "blue")
    part_time_donut = make_donut(round(part_time_percentage,1), "Part-Time", "red")
    
    return full_time_donut, part_time_donut

def create_contract_type_donuts(df):
    """Creates donut charts for contract types without displaying them."""
    if df is None:
        return None, None

    contract_count = len(df[df['contract_type'] == 'contract'])
    total_count = len(df)
    contract_percentage = (contract_count / total_count) * 100 if total_count > 0 else 0

    permanent_count = len(df[df['contract_type'] == 'permanent'])
    permanent_percentage = (permanent_count / total_count) * 100 if total_count > 0 else 0

    contract_donut = make_donut(round(contract_percentage,1), "Contract", "blue")
    permanent_donut = make_donut(round(permanent_percentage,1), "Permanent", "red")
    
    return contract_donut, permanent_donut

def create_total_jobs_by_day_chart(df):
    """Creates the jobs by day chart without displaying it."""
    if df is None:
        return None

    day_counts = df['Day'].value_counts().reset_index()
    day_counts.columns = ['Day', 'count']

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_counts['Day'] = pd.Categorical(day_counts['Day'], categories=day_order, ordered=True)
    day_counts = day_counts.sort_values('Day')

    fig = px.bar(
        day_counts,
        x='Day',
        y='count',
        labels={'Day': 'Day of the Week', 'count': 'Number of Job Postings'},
        color='Day',
        height=300
    )

    fig.update_layout(showlegend=False)
    
    return fig

def create_salary_range_by_category_chart(df):
    """Creates the salary range chart without displaying it."""
    if df is None:
        return None

    df_cleaned = df.dropna(subset=['salary_min', 'salary_max', 'category'])

    try:
        df_cleaned['salary_min'] = pd.to_numeric(df_cleaned['salary_min'])
        df_cleaned['salary_max'] = pd.to_numeric(df_cleaned['salary_max'])
    except ValueError:
        return None

    df_cleaned['average_salary'] = (df_cleaned['salary_min'] + df_cleaned['salary_max']) / 2

    top_10_categories = df_cleaned['category'].value_counts().nlargest(10).index.tolist()
    df_top_10 = df_cleaned[df_cleaned['category'].isin(top_10_categories)]

    median_salaries = df_top_10.groupby('category')['average_salary'].median().sort_values(ascending=False)
    category_order = list(median_salaries.index)

    chart = alt.Chart(df_top_10).mark_boxplot().encode(
        y=alt.Y('category:N', title='Job Category', sort=category_order),
        x=alt.X('average_salary:Q', title='Average Salary', scale=alt.Scale(zero=False)),
        tooltip=['category', 'salary_min', 'salary_max', 'average_salary']
    ).properties(
        height=500
    )
    
    return chart

# Main function that will be called by the main app
def main():
    """Main function to run the Adzuna dashboard."""
    # Title and description
    st.title("Adzuna Job Scraping Analysis - Australia 📊")
    st.markdown("This is an interactive dashboard to analyze job postings data scraped from Adzuna website.")
    
    # Load data
    df_full = load_data()
    
    if df_full is not None:
        # Show available columns in sidebar for debugging
        st.sidebar.write("Available columns:", df_full.columns.tolist())
        st.sidebar.write(f"Data shape: {df_full.shape}")
        
        # Creating dropdown filtering sidebar
        st.sidebar.header("Filters")

        try:
            category_options = df_full['category'].unique().tolist()
            contract_type_options = df_full['contract_type'].unique().tolist()
            contract_time_options = df_full['contract_time'].unique().tolist()
        except KeyError as e:
            st.error(f"Error: Column '{e}' not found in DataFrame. Check your Google Sheet column names.")
            return

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

        # Apply filters
        filtered_df = filter_dataframe(df_full, contract_type_filter, contract_time_filter, category_filter)

        if not filtered_df.empty:
            # Main Area Dashboard Layout
            col1, col2, col3 = st.columns([2, 4, 2])

            with col1:
                st.subheader("Total Job Postings 💼")
                total_jobs, total_jobs_full, percentage_filtered = plot_total_job_postings(df_full, filtered_df)
                st.metric(
                    label="Total Job Postings 💼",
                    value=f"{total_jobs} out of {total_jobs_full}",
                    delta=f"{percentage_filtered:.2f}%",
                )
                
                st.subheader("Total Job Postings by day")
                day_chart = create_total_jobs_by_day_chart(filtered_df)
                if day_chart is not None:
                    st.plotly_chart(day_chart, use_container_width=True)
                else:
                    st.warning("Cannot plot total jobs by day: Data loading failed.")
                
                st.subheader("Contract Time")
                full_time_donut, part_time_donut = create_contract_time_donuts(filtered_df)
                if full_time_donut is not None and part_time_donut is not None:
                    col1a, col1b = st.columns(2)
                    with col1a:
                        st.subheader("Full-Time")
                        st.altair_chart(full_time_donut, use_container_width=True)
                    with col1b:
                        st.subheader("Part-Time")
                        st.altair_chart(part_time_donut, use_container_width=True)
                else:
                    st.warning("Cannot plot contract time donuts: Data loading failed.")
                
                st.subheader("Contract Type")
                contract_donut, permanent_donut = create_contract_type_donuts(filtered_df)
                if contract_donut is not None and permanent_donut is not None:
                    col1c, col1d = st.columns(2)
                    with col1c:
                        st.subheader("Contract")
                        st.altair_chart(contract_donut, use_container_width=True)
                    with col1d:
                        st.subheader("Permanent")
                        st.altair_chart(permanent_donut, use_container_width=True)
                else:
                    st.warning("Cannot plot contract type donuts: Data loading failed.")

            with col2:
                st.subheader("Job Posting Density Heatmap 🔍") 
                job_map = create_job_density_heatmap(filtered_df)
                if job_map is not None:
                    st_folium(job_map, height=600, width=1200)
                else:
                    st.warning("Cannot plot heatmap: No valid location data.")
                
                st.subheader("Top 10 Salary and its Range")
                salary_chart = create_salary_range_by_category_chart(filtered_df)
                if salary_chart is not None:
                    st.altair_chart(salary_chart, use_container_width=True)
                else:
                    st.warning("Cannot plot salary range: Data issue.")

            with col3:
                st.subheader("Total Job Postings Job Categories")
                category_chart = create_job_postings_by_categories_chart(filtered_df)
                if category_chart is not None:
                    st.plotly_chart(category_chart, use_container_width=True)
                else:
                    st.warning("Cannot plot category data: Data loading failed.")

            # Show raw data if checkbox is selected
            if st.checkbox("Show Raw Data"):
                st.subheader("Raw Data")
                st.dataframe(filtered_df)
        else:
            st.warning("No data matches your selection. Change the filters!")
    else:
        st.error("Data loading failed. Please check the credentials file path and Google Sheet.")
