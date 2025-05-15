import asyncio
import aiohttp
import re
import logging
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder='templates')

# إعداد التسجيل لتصحيح الأخطاء
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch(session, url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # محاولة استخراج الإيدي من عنوان URL أولاً
        match = re.search(r'(?:id=|fbid=)(\d+)', url)
        if match:
            logging.debug(f"ID extracted from URL for {url}: {match.group(1)}")
            return match.group(1)

        # إجراء طلب HTTP
        async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
            # تسجيل رمز الاستجابة
            logging.debug(f"HTTP status for {url}: {response.status}")

            # التحقق من رمز الاستجابة
            if response.status not in [200, 302]:
                logging.debug(f"Non-200/302 status for {url}: {response.status}")
                return None

            html = await response.text()

            # التحقق من عبارات تشير إلى حساب مقفول
            blocked_indicators = [
                "account has been disabled",
                "this account is not available",
                "الحساب تم تعطيله",
                "هذا الحساب غير متاح"
            ]
            for phrase in blocked_indicators:
                if phrase in html.lower():
                    logging.debug(f"Blocked indicator found in {url}: {phrase}")
                    return None

            # محاولة استخراج الإيدي من الـ HTML
            match = re.search(r'fb://profile/(\d+)', html)
            if match:
                logging.debug(f"ID extracted from fb://profile for {url}: {match.group(1)}")
                return match.group(1)

            match = re.search(r'"entity_id":"(\d+)"', html)
            if match:
                logging.debug(f"ID extracted from entity_id for {url}: {match.group(1)}")
                return match.group(1)

            match = re.search(r'profile_id=(\d+)', html)
            if match:
                logging.debug(f"ID extracted from profile_id for {url}: {match.group(1)}")
                return match.group(1)

            match = re.search(r'"userID":"(\d+)"', html)
            if match:
                logging.debug(f"ID extracted from userID for {url}: {match.group(1)}")
                return match.group(1)

            match = re.search(r'data-profileid="(\d+)"', html)
            if match:
                logging.debug(f"ID extracted from data-profileid for {url}: {match.group(1)}")
                return match.group(1)

            logging.debug(f"No ID found for {url}")
            return None
    except Exception as e:
        logging.error(f"Exception for {url}: {str(e)}")
        return None

async def extract_ids_async(urls):
    ids = []
    failed_urls = []
    connector = aiohttp.TCPConnector(limit=100)  # تحكم في العدد
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