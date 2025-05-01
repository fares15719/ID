import asyncio
import aiohttp
import re
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder='templates')

async def fetch(session, url):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            html = await response.text()

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

async def extract_ids_async(urls):
    ids = []
    invalid_urls = []
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url.strip()) for url in urls if url.strip()]
        results = await asyncio.gather(*tasks)

        for url, fb_id in zip(urls, results):
            if fb_id:
                ids.append(fb_id)
            else:
                invalid_urls.append(url.strip())

    return ids, invalid_urls

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/get_ids', methods=['POST'])
def extract_ids():
    data = request.get_json()
    urls = data.get("urls", [])

    ids, invalid_urls = asyncio.run(extract_ids_async(urls))

    return jsonify(success=True, ids=ids, invalid_urls=invalid_urls)

if __name__ == '__main__':
    app.run()