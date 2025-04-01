from flask import Flask, request, jsonify
import requests
import config

app = Flask(__name__)

# Azure Logic App API URL
API_URL = config.copilot_api_for_generate_logbook_widget


@app.route('/GenerateLogbookWidget', methods=['POST'])
def send_request():
    try:
        # Define the body to be sent to the API
        body = request.json

        # Make a POST request to the API
        response = requests.post(
            API_URL,
            
            json=body
        )

        # Return the response from the API
        return jsonify({
            "status": response.status_code,
            "response": response.json()
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


def start_app():
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    start_app()
