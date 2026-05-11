import pandas as pd
import os
import json

path = 'D:/work/stock/33'
files = [f for f in os.listdir(path) if f.endswith('.xlsx')]

result = {}

for f in files:
    try:
        file_path = os.path.join(path, f)
        # Read the first sheet
        df = pd.read_excel(file_path)
        # Convert first 10 rows to a list of dicts to understand structure
        result[f] = {
            "columns": df.columns.tolist(),
            "sample_data": df.head(5).to_dict(orient='records')
        }
    except Exception as e:
        result[f] = {"error": str(e)}

with open('excel_analysis.json', 'w', encoding='utf-8') as jf:
    json.dump(result, jf, ensure_ascii=False, indent=2)

print("Analysis completed and saved to excel_analysis.json")
