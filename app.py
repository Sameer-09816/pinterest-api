# app.py
from flask import Flask, request, jsonify
import requests
from urllib.parse import quote
import os # For Render port

app = Flask(__name__)

TARGET_API_BASE_URL = "https://pinterestdownloader.io/frontendService/DownloaderService?url="

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://pinterestdownloader.io/', # Important: Pretend request comes from their site
    'Origin': 'https://pinterestdownloader.io',   # Important: Same as above
}

@app.route('/')
def home():
    # A simple home route to check if the app is running
    return jsonify({
        "message": "Pinterest Downloader Proxy API is running.",
        "usage": "Send a GET request to /get_pinterest_data?url=<PINTEREST_POST_URL>"
    })

@app.route('/get_pinterest_data', methods=['GET'])
def get_pinterest_data():
    pinterest_post_url = request.args.get('url')

    if not pinterest_post_url:
        return jsonify({"error": "Missing 'url' parameter in the query string."}), 400

    encoded_pinterest_url = quote(pinterest_post_url, safe='')
    target_url = f"{TARGET_API_BASE_URL}{encoded_pinterest_url}"

    print(f"Attempting to fetch data from: {target_url}")

    try:
        response = requests.get(target_url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        try:
            data = response.json()
            if isinstance(data.get("message"), str):
                try:
                    import json
                    message_data = json.loads(data["message"])
                    if isinstance(message_data, (dict, list)):
                        return jsonify(message_data)
                except json.JSONDecodeError:
                    pass # If 'message' is not valid JSON, fall through to return original 'data'
            return jsonify(data)

        except requests.exceptions.JSONDecodeError:
            print(f"Warning: Response from {target_url} was not valid JSON. Content: {response.text[:200]}...")
            return jsonify({
                "error": "The external API did not return valid JSON.",
                "status_code_from_external": response.status_code,
                "content_preview": response.text[:500]
            }), 502

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Status: {http_err.response.status_code if http_err.response else 'N/A'}")
        error_response_data = {
            "error": "Failed to fetch data from external API due to HTTP error.",
            "details": str(http_err)
        }
        if http_err.response is not None:
            error_response_data["status_code_from_external"] = http_err.response.status_code
            try:
                error_response_data["external_api_response_body"] = http_err.response.json()
            except requests.exceptions.JSONDecodeError:
                 error_response_data["external_api_response_body"] = http_err.response.text[:500]

        return jsonify(error_response_data), 502

    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
        return jsonify({"error": "Failed to connect to external API.", "details": str(conn_err)}), 503
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
        return jsonify({"error": "Request to external API timed out.", "details": str(timeout_err)}), 504
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred with the request: {req_err}")
        return jsonify({"error": "An unexpected error occurred while fetching data.", "details": str(req_err)}), 500

if __name__ == '__main__':
    # For local development. Render will use Gunicorn and its own port management.
    # The PORT environment variable is used by Render and other hosting providers.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) # debug=False for production-like local testing
