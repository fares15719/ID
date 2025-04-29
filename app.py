from flask import Flask, request, jsonify, render_template
import requests
import re

app = Flask(__name__, template_folder='templates')

def get_fb_id(url):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text

        match = re.search(r'fb://profile/(\d+)', html)
        if match:
            return match.group(1)

        match = re.search(r'"entity_id":"(\d+)"', html)
        if match:
            return match.group(1)

        match = re.search(r'profile_id=(\d+)', html)
        if match:
            return match.group(1)

        return None
    except Exception:
        return None

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/get_id', methods=['POST'])
def extract_id():
    data = request.get_json()
    url = data.get("url")
    fb_id = get_fb_id(url)
    return jsonify({"fb_id": fb_id})

if __name__ == '__main__':
    app.run()
