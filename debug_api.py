import sys, time, json
sys.path.insert(0, '.')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=options)

url = "https://nhathuoclongchau.com.vn/thuoc/thuoc-tieu-hoa-and-gan-mat"
driver.get(url)
time.sleep(4)

perf_logs = driver.get_log("performance")

# Tìm request ID của API search/list
target_apis = [
    "search/list",
    "without-inventory/search/list",
    "search/menu/cate"
]

requests_map = {}
responses_map = {}

for entry in perf_logs:
    try:
        msg = json.loads(entry["message"])["message"]
        method = msg.get("method", "")
        params = msg.get("params", {})

        # Bắt request
        if method == "Network.requestWillBeSent":
            req_url = params.get("request", {}).get("url", "")
            if any(k in req_url for k in target_apis):
                req_id = params.get("requestId")
                requests_map[req_id] = {
                    "url": req_url,
                    "method": params.get("request", {}).get("method"),
                    "postData": params.get("request", {}).get("postData", ""),
                    "headers": params.get("request", {}).get("headers", {})
                }

        # Bắt response body
        if method == "Network.responseReceived":
            resp_url = params.get("response", {}).get("url", "")
            if any(k in resp_url for k in target_apis):
                req_id = params.get("requestId")
                responses_map[req_id] = resp_url

    except Exception:
        pass

# In chi tiết từng API call
for req_id, req_info in requests_map.items():
    print(f"\n{'='*60}")
    print(f"URL: {req_info['url']}")
    print(f"Method: {req_info['method']}")
    print(f"Post Data: {req_info['postData'][:500] if req_info['postData'] else 'None'}")

    # Lấy response body
    try:
        result = driver.execute_cdp_cmd(
            "Network.getResponseBody", {"requestId": req_id}
        )
        body = result.get("body", "")
        try:
            parsed = json.loads(body)
            print(f"Response (tóm tắt): {json.dumps(parsed, ensure_ascii=False)[:600]}")
        except Exception:
            print(f"Response raw: {body[:300]}")
    except Exception as e:
        print(f"Không lấy được response body: {e}")

driver.quit()