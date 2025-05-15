--- app.py ---
import asyncio
import aiohttp
import re
import logging
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder='templates')

# ✅ وضع الصيانة - غيرها لـ False لفتح الموقع
MAINTENANCE_MODE = True

# Logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch(session, url, retry=False):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.facebook.com/'
    }
    try:
        logging.debug(f"Fetching URL: {url}")
        await asyncio.sleep(3)
        async with session.get(url, headers=headers, timeout=15) as response:
            html = await response.text()
            for pattern in [
                r'fb://profile/(\d+)',
                r'"entity_id":"(\d+)",',
                r'profile_id=(\d+)',
                r'"userID":"(\d+)",',
                r'\b(\d{10,})\b'
            ]:
                match = re.search(pattern, html)
                if match:
                    return match.group(1)
            if 'profile' in html.lower():
                return "valid_profile"
            return None
    except Exception as e:
        logging.error(f"Error fetching {url}: {str(e)}")
        return None

async def extract_ids_async(inputs):
    valid_results = []
    invalid_results = []
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for line in inputs:
            line = line.strip()
            if not line:
                continue
            if line.startswith(('http://', 'https://')):
                tasks.append((line, fetch(session, line)))
            else:
                match = re.search(r'(\d{10,})', line)
                if match:
                    url = f"https://www.facebook.com/profile.php?id={match.group(1)}"
                    tasks.append((line, fetch(session, url)))
                else:
                    invalid_results.append(line)
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        for (line, _), result in zip(tasks, results):
            if isinstance(result, Exception) or result is None:
                invalid_results.append(line)
            else:
                valid_results.append(result)
    return valid_results, invalid_results

@app.route('/')
def home():
    if MAINTENANCE_MODE:
        return render_template("maintenance.html")
    return render_template("index.html")

@app.route('/get_ids', methods=['POST'])
def extract_ids():
    if MAINTENANCE_MODE:
        return jsonify(success=False, message="🚧 الموقع تحت الصيانة حالياً.")
    data = request.get_json()
    urls = data.get("urls", [])
    valid, invalid = asyncio.run(extract_ids_async(urls))
    return jsonify(success=True, valid_results=valid, invalid_results=invalid)

if __name__ == '__main__':
    app.run(debug=True)

--- templates/maintenance.html ---
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>🚧 الموقع تحت الصيانة</title>
  <style>
    body {
      background-color: #121212;
      color: #fff;
      font-family: 'Tajawal', sans-serif;
      text-align: center;
      padding: 50px;
    }
    .box {
      max-width: 600px;
      margin: auto;
      background: #1e1e1e;
      padding: 30px;
      border-radius: 10px;
      box-shadow: 0 0 10px #000;
    }
    h1 {
      color: #ffcc00;
    }
  </style>
</head>
<body>
  <div class="box">
    <h1>🚧 الموقع تحت الصيانة</h1>
    <p>نقوم ببعض التحديثات حالياً لتحسين تجربتك، نقدر صبرك ❤️</p>
  </div>
</body>
</html>

--- requirements.txt ---
flask
aiohttp

--- vercel.json ---
{
  "version": 2,
  "builds": [
    { "src": "app.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "app.py" }
  ]
}
