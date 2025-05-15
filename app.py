import asyncio
import aiohttp
import re
import logging
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder='templates')

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch(session, url, retry=False):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',  # Explicitly include brotli (br)
        'Connection': 'keep-alive',
        'Referer': 'https://www.facebook.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Alternate headers for retry
    retry_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.facebook.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        logging.debug(f"Fetching URL: {url}")
        await asyncio.sleep(3)  # Increase delay to 3 seconds to avoid rate limiting
        async with session.get(url, headers=headers if not retry else retry_headers, timeout=15, allow_redirects=True) as response:
            # Try to read the response text
            try:
                html = await response.text()
            except Exception as e:
                logging.error(f"Error decoding response for {url}: {str(e)}")
                html = ""

            logging.debug(f"Response status: {response.status}, Final URL: {response.url}")

            # Check if the page is accessible
            if response.status != 200:
                logging.debug(f"Non-200 status code: {response.status}")
                # Retry once with different headers if status is 400
                if response.status == 400 and not retry:
                    logging.debug("Retrying with alternate headers...")
                    return await fetch(session, url, retry=True)
                
                # Fallback: If status is 400 but HTML contains profile indicators, consider it valid
                if response.status == 400 and ('profile' in html.lower() or re.search(r'\b(\d{10,})\b', html)):
                    logging.debug("Page seems to be a valid profile despite 400 status")
                    return "valid_profile"
                
                return None

            # Try multiple patterns to find the ID
            match = re.search(r'fb://profile/(\d+)', html)
            if match:
                logging.debug(f"Found ID via fb://profile: {match.group(1)}")
                return match.group(1)

            match = re.search(r'"entity_id":"(\d+)"', html)
            if match:
                logging.debug(f"Found ID via entity_id: {match.group(1)}")
                return match.group(1)

            match = re.search(r'profile_id=(\d+)', html)
            if match:
                logging.debug(f"Found ID via profile_id: {match.group(1)}")
                return match.group(1)

            match = re.search(r'"userID":"(\d+)"', html)
            if match:
                logging.debug(f"Found ID via userID: {match.group(1)}")
                return match.group(1)

            # Fallback: Look for any 10+ digit ID in the HTML
            match = re.search(r'\b(\d{10,})\b', html)
            if match:
                logging.debug(f"Found ID in HTML content: {match.group(1)}")
                return match.group(1)

            # Fallback: Check if the page looks like a valid profile
            if 'profile' in html.lower() or 'user' in html.lower():
                logging.debug("Page seems to be a valid profile, but no ID found")
                return "valid_profile"

            logging.debug("No ID or profile indicators found in HTML")
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
        for input_line in inputs:
            input_line = input_line.strip()
            if not input_line:
                continue
            # Check if the input is a URL
            if input_line.startswith(('http://', 'https://')):
                logging.debug(f"Processing URL: {input_line}")
                tasks.append((input_line, fetch(session, input_line)))
            else:
                # Try to extract an ID (10 digits or more) from anywhere in the input line
                match = re.search(r'(\d{10,})', input_line)
                if match:
                    fb_id = match.group(1)
                    url = f"https://www.facebook.com/profile.php?id={fb_id}"
                    logging.debug(f"Extracted ID {fb_id} from line: {input_line}, checking URL: {url}")
                    tasks.append((input_line, fetch(session, url)))
                else:
                    logging.debug(f"No valid ID found in line: {input_line}")
                    invalid_results.append(input_line)

        # Execute all fetch tasks
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

        # Process results
        for (input_line, _), result in zip(tasks, results):
            if isinstance(result, Exception) or result is None:
                logging.debug(f"Invalid result for line: {input_line}, result: {result}")
                invalid_results.append(input_line)
            else:
                logging.debug(f"Valid result for line: {input_line}, ID: {result}")
                if input_line.startswith(('http://', 'https://')):
                    valid_results.append(result)  # For URLs, return the ID
                else:
                    valid_results.append(input_line)  # For IDs, return the original line

    return valid_results, invalid_results

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/get_ids', methods=['POST'])
def extract_ids():
    data = request.get_json()
    inputs = data.get("urls", [])

    valid_results, invalid_results = asyncio.run(extract_ids_async(inputs))

    return jsonify(success=True, valid_results=valid_results, invalid_results=invalid_results)

if __name__ == '__main__':
    app.run(debug=True)