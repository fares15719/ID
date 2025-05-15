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
    failed_urls = []
    connector = aiohttp.TCPConnector(limit=100)  # تحكم في العدد徐
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        url_map = {}  # لربط الروابط بنتائجها
        for url in urls:
            url = url.strip()
            if url:
                tasks.append(fetch(session, url))
                url_map[url] = None  # تهيئة الرابط بدون إيدي

        results = await asyncio.gather(*tasks)

        # ربط النتائج بالروابط
        for url, fb_id in zip([url.strip() for url in urls if url.strip()], results):
            if fb_id:
                ids.append(fb_id)
                url_map[url] = fb_id
            else:
                failed_urls.append(url)

    return ids, failed_urls

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/get_ids', methods=['POST'])
def extract_ids():
    data = request.get_json()
    urls = data.get("urls", [])

    ids, failed_urls = asyncio.run(extract_ids_async(urls))

    return jsonify(success=True, ids=ids, failed_urls=failed_urls)

if __name__ == '__main__':
    app.run()