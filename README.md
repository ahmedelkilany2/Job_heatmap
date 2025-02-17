# Job_heatmap
# Job Location Heatmap - Australia

This Streamlit app creates a heatmap of job postings across Australia, with data sourced from a Google Sheet.

## Features

- Displays job posting locations on an interactive map
- Auto-refreshes data every 4 hours
- Caches geocoding results to improve performance
- Shows key metrics like total job postings and unique locations

## Setup Instructions

1. Clone this repository
2. Install the required packages: `pip install -r requirements.txt`
3. Run the Streamlit app: `streamlit run app.py`

## Deployment

Can deploy this app on Streamlit Cloud for free:
1. Push this code to your GitHub repository
2. Connect your repository to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy the app

## Data Source

The app pulls data from a Google Sheet containing job listings. The sheet must have a `location` column.

## Configuration

Can customize the app by modifying the following:
- Google Sheet URL in the `fetch_and_process_data()` function
- Map center coordinates and zoom level
- Heatmap parameters (radius, blur)
- Update frequency (currently set to 4 hours)
