from pathlib import Path
import pandas as pd

sales_path = Path(__file__).parent.parent / 'data' / 'sample_sales.xlsx'

# 1. Read data/sample_sales.xlsx via pandas.
# 2. Explicitly specify the Sales sheet.
df = pd.read_excel(sales_path, sheet_name='Sales', engine='openpyxl')

# 3. Print the first 5 lines.
print(df.head())

# 4. Print the number of rows and columns.
row_count, column_count = df.shape
print(f'Row count: {row_count}, Column count: {column_count}')

# 5. View all column types.
print(df.dtypes)

# 6. Determine which columns have missing values ​​and how many there are.
print(df.isna().sum())