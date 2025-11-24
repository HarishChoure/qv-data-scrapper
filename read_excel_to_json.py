#!/usr/bin/env python3
"""
Excel to JSON Converter
Reads Excel file and converts data to JSON format
"""

import pandas as pd
import json
import sys
from pathlib import Path


def read_excel_to_json(excel_file_path, sheet_name=None, output_file=None):
    """
    Read Excel file and convert to JSON format
    
    Args:
        excel_file_path (str): Path to the Excel file
        sheet_name (str, optional): Specific sheet name to read. If None, reads all sheets
        output_file (str, optional): Path to save JSON file. If None, returns JSON string
    
    Returns:
        dict or str: JSON data as dictionary or JSON string
    """
    try:
        # Check if file exists
        if not Path(excel_file_path).exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
        
        # Read Excel file
        if sheet_name:
            # Read specific sheet
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
            data = {
                'sheet_name': sheet_name,
                'data': df.to_dict(orient='records')
            }
        else:
            # Read all sheets
            excel_data = pd.read_excel(excel_file_path, sheet_name=None)
            data = {}
            for sheet, df in excel_data.items():
                data[sheet] = df.to_dict(orient='records')
        
        # Convert NaN values to None for proper JSON serialization
        json_data = json.loads(json.dumps(data, default=str, allow_nan=False))
        
        # Save to file if output_file is specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"JSON data saved to: {output_file}")
        
        return json_data
    
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}", file=sys.stderr)
        raise


def main():
    """Main function to run the script"""
    # Default Excel file path
    excel_file = "New Microsoft Excel Worksheet.xlsx"
    
    # Check if custom file path is provided as command line argument
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    # Optional: specify sheet name as second argument
    sheet_name = None
    if len(sys.argv) > 2:
        sheet_name = sys.argv[2]
    
    # Optional: specify output file as third argument
    output_file = None
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    
    try:
        # Read Excel and convert to JSON
        json_data = read_excel_to_json(excel_file, sheet_name, output_file)
        
        # Print JSON to console
        print("\n" + "="*50)
        print("Excel Data in JSON Format:")
        print("="*50)
        print(json.dumps(json_data, indent=2, ensure_ascii=False))
        
        return json_data
    
    except Exception as e:
        print(f"Failed to process Excel file: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

