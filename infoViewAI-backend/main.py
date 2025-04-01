from flask import Flask, request
from flask_cors import CORS
import json
import requests
from postprocessing import processAIOutput

app = Flask(__name__)
CORS(app)

with open("config.json","r") as f:
    config_file = f.read()

config_file = json.loads(config_file)

API_URL = config_file["API_URL"]

@app.route("/GetInfoViewFromPrompt", methods=["POST"])
def generate_json():

    data = request.get_json()
    if('infoViewSettings' not in data):
        return {"error": "infoViewSettings parameter is missing"}
    if('userPrompt' not in data):
        return {"error": "userPrompt parameter is missing"}
    infoViewSettings = data['infoViewSettings']
    userPrompt = data['userPrompt']

    response = None
    if (('useMockData' in data) and data['useMockData']==True):
        with open("mock_data.json","r") as f:
            response = f.read()
        response = json.loads(response)
    else:
        response = requests.post(url=API_URL,json={"userPrompt":userPrompt})
        if(response.status_code != 200):
            return {"error": "There is an error fetching from Azure API"}
        response = response.json()

    # Optional debug parameter for debugging AI generated output before postprocessing
    if(('debug' in data) and data['debug']==True):
        return response

    response = processAIOutput(response,infoViewSettings)

    return response

# main driver function
if __name__ == '__main__':

    # run() method of Flask class runs the application 
    # on the local development server.
    app.run()
