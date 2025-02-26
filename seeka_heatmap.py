import pandas as pd

# Google Sheets URL (Change `edit` to `gviz/tq?tqx=out:csv` to get CSV format)
sheet_url = "https://docs.google.com/spreadsheets/d/154MnI4PV3-_OIDo2MZWw413gbzw9dVoS-aixCRujR5k/gviz/tq?tqx=out:csv"

# Read data into DataFrame
df = pd.read_csv(sheet_url)

# Debug: Print column names to check formatting issues
print("Columns in dataset:", df.columns.tolist())

# Trim spaces from column names (Fixes potential mismatch issues)
df.columns = df.columns.str.strip()

# Check if 'Suburb' column exists
if 'Suburb' in df.columns:
    print("✅ 'Suburb' column found!")
else:
    print("❌ 'Suburb' column NOT found. Columns available:", df.columns)

# Display the first few rows
print(df.head())
