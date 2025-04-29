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
    connector = aiohttp.TCPConnector(limit=100)  # تحكم في العدد لو عايز
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url.strip()) for url in urls if url.strip()]
        results = await asyncio.gather(*tasks)

        for fb_id in results:
            if fb_id:
                ids.append(fb_id)

    return ids

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/get_ids', methods=['POST'])
def extract_ids():
    data = request.get_json()
    urls = data.get("urls", [])

    ids = asyncio.run(extract_ids_async(urls))

    return jsonify(success=True, ids=ids)

if __name__ == '__main__':
    app.run()
