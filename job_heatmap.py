import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Google Sheets CSV export link (Modify based on your sheet)
sheet_url = "https://docs.google.com/spreadsheets/d/1iFZ71DNkAtlJL_HsHG6oT98zG4zhE6RrT2bbIBVitUA/export?format=csv"

# Load data into a DataFrame
df = pd.read_csv(sheet_url)

# Convert to numerical values (if needed)
df = df.set_index(df.columns[0])  # Set first column as index
df = df.apply(pd.to_numeric, errors='coerce')  # Convert all columns to numeric

# Create the heatmap
plt.figure(figsize=(12, 6))
sns.heatmap(df, annot=True, cmap="coolwarm", linewidths=0.5, fmt=".1f")

# Title and display
plt.title("Heatmap from Google Sheets Data")
plt.show()
