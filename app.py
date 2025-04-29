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

@app.route('/get_ids', methods=['POST'])
def extract_ids():
    data = request.get_json()
    urls = data.get("urls", [])
    ids = []

    for url in urls:
        url = url.strip()
        if url:
            fb_id = get_fb_id(url)
            if fb_id:
                ids.append(fb_id)

    return jsonify(success=True, ids=ids)

if __name__ == '__main__':
    app.run()
