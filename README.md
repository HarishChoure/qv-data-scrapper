# Excel to JSON Converter

A Python script to read Excel files and convert them to JSON format.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Read the default Excel file (`New Microsoft Excel Worksheet.xlsx`):

```bash
python read_excel_to_json.py
```

### Custom Excel File

Read a specific Excel file:

```bash
python read_excel_to_json.py path/to/your/file.xlsx
```

### Read Specific Sheet

Read a specific sheet from the Excel file:

```bash
python read_excel_to_json.py path/to/your/file.xlsx Sheet1
```

### Save to JSON File

Read Excel and save to a JSON file:

```bash
python read_excel_to_json.py path/to/your/file.xlsx Sheet1 output.json
```

## Python Code Usage

You can also use the function directly in your Python code:

```python
from read_excel_to_json import read_excel_to_json

# Read all sheets
json_data = read_excel_to_json("New Microsoft Excel Worksheet.xlsx")

# Read specific sheet
json_data = read_excel_to_json("New Microsoft Excel Worksheet.xlsx", sheet_name="Sheet1")

# Read and save to file
json_data = read_excel_to_json("New Microsoft Excel Worksheet.xlsx", output_file="output.json")
```

## Output Format

- **Single sheet**: Returns a dictionary with `sheet_name` and `data` keys
- **Multiple sheets**: Returns a dictionary where each key is a sheet name and value is the data

Each sheet's data is converted to a list of dictionaries, where each dictionary represents a row with column names as keys.

