from google import genai
from google.genai import types
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import io
import re
import numpy as np

app = Flask(__name__)
cors = CORS(app)

CONFIG = None
with open("config.json","r") as f:
    CONFIG = f.read()
API_KEY = json.loads(CONFIG)["API_KEY"]
client = genai.Client(api_key=API_KEY)

SYSTEM_INSTRUCTION_1 = None
with open("system_instruction_1.txt","r") as f:
    SYSTEM_INSTRUCTION_1 = f.read()

SYSTEM_INSTRUCTION_2 = None
with open("system_instruction_2.txt","r") as f:
    SYSTEM_INSTRUCTION_2 = f.read()

def generate_plain_html_table(data):
    base64image = data['base64Image']
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[types.Part.from_bytes(data=base64image,mime_type="image/png"),"Generate an HTML table from the given image."],
        config=types.GenerateContentConfig(
            temperature=0,
            system_instruction=SYSTEM_INSTRUCTION_1,
            response_mime_type="application/json"
        )
    )
    response = json.loads(response.text)
    result = response['HTMLContent'].replace('\n','')
    return result

def generate_dataframe(html_string):
    df = pd.read_html(io.StringIO(html_string))[0]
    return df

def extract_relevant_metadata(html_string, data):
    if 'userPrompt' in data and data['userPrompt'] != '':
        userPrompt = data['userPrompt']
    else:
        userPrompt = "Return json with relevant columns"
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[userPrompt, html_string],
        config=types.GenerateContentConfig(
            temperature=0,
            system_instruction=SYSTEM_INSTRUCTION_2,
            response_mime_type="application/json"
        )
    )
    response = json.loads(response.text)
    return response

def clean_text(text):
    # If text is a bytes-like object, decode it to a string.
    if isinstance(text, (bytes, bytearray, np.bytes_)):
        try:
            text = text.decode('utf-8', errors='replace')
        except Exception as e:
            print("Decoding error:", e, "for text:", text)
            text = str(text)
    # If text is not a string, convert it.
    if not isinstance(text, str):
        text = str(text)
    result = re.sub(r"[^\w]+", "_", text)
    return result

def fill_table(df, relevant_columns):
    tags = []
    columnsToFill = relevant_columns['columnsToFill']
    prefix = relevant_columns['prefix']
    suffix = relevant_columns['suffix']

        # Process each column to fill
    for col_idx in columnsToFill:
        col_name = df.columns[col_idx]

        # Create the base string for each row
        base_series = df.iloc[:, prefix].apply(clean_text) + "_" + clean_text(col_name)
        
        # Count how many times each base value occurs
        base_counts = base_series.value_counts()
        
        # Dictionary to track the numbering for duplicates
        duplicate_tracker = {}
        new_values = []
        
        # Loop over each base value (row by row)
        for base in base_series:
            if base_counts[base] == 1:
                # Only one occurrence: no number added.
                new_val = f"{base}{suffix}"
            else:
                # More than one occurrence: add an increasing number.
                duplicate_tracker[base] = duplicate_tracker.get(base, 0) + 1
                new_val = f"{base}_{duplicate_tracker[base]}{suffix}"
            new_values.append("$["+new_val+"]")
            tags.append(new_val)
        # Assign the new values back to the DataFrame column
        df.iloc[:, col_idx] = new_values
    
    return tags
  

@app.route("/GenerateTable",methods=['POST'])
def generate_table():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request must be JSON formatted'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Empty request body'}), 400
    
    if not 'base64Image' in data or not data['base64Image']:
        return jsonify({'status': 'error', 'message': 'Base64 image parameter not found'}), 400
    
    result = generate_plain_html_table(data)
    result_df = generate_dataframe(result)
    relevant_metadata = extract_relevant_metadata(result, data)
    tags = fill_table(result_df, relevant_metadata)
    result = result_df.to_html(border=0,index=False).replace('\n','').replace('<table class="dataframe">', '<table>').replace('<tr style="text-align: right;">','<tr>').replace('NaN','')

    response = { 
                "ViewType": "HTML",
                "StartTime": 0, 
                "EndTime": 0, 
                "Interval": 0, 
                "HTMLContent": result,
                "SectionName": relevant_metadata["tableName"], 
                "TagDetails": 
                    {
                        "NumberOfTags": len(tags),
                        "TagNames": tags,
                        "Descriptions": tags, 
                    }
                }
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5001)