from flask import Flask, jsonify

# Initialize Flask app
app = Flask(__name__)

# Route to return a JSON response
@app.route('/CommentSummary/data')
def data():
    sample_data = {
        'name': 'John Doe',
        'age': 30,
        'city': 'New York'
    }
    return jsonify(sample_data)

# Run the app
if __name__ == '__main__':
    app.run()