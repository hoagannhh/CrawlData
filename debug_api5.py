import sys, time, json
sys.path.insert(0, '.')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=options)

# Bật CDP để intercept response
driver.execute_cdp_cmd("Network.enable", {})

collected = []

# Load trang danh mục
url = "https://nhathuoclongchau.com.vn/thuoc/thuoc-tieu-hoa-and-gan-mat"
driver.get(url)
time.sleep(5)

# Lấy tất cả performance logs
perf_logs = driver.get_log("performance")

target_req_ids = []
for entry in perf_logs:
    try:
        msg = json.loads(entry["message"])["message"]
        if msg.get("method") == "Network.responseReceived":
            resp_url = msg["params"]["response"]["url"]
            # Tìm API trả về danh sách sản phẩm
            if "search-product-service" in resp_url and "POST" in str(msg):
                req_id = msg["params"]["requestId"]
                target_req_ids.append((req_id, resp_url))
    except Exception:
        pass

# Thử lấy response body của từng request
print(f"Tìm thấy {len(target_req_ids)} API calls\n")
for req_id, req_url in target_req_ids:
    print(f"URL: {req_url}")
    try:
        result = driver.execute_cdp_cmd(
            "Network.getResponseBody", {"requestId": req_id}
        )
        body = result.get("body", "")
        try:
            parsed = json.loads(body)
            if isinstance(parsed, list) and len(parsed) > 3:
                print(f"  → Array of {len(parsed)} items")
                if parsed and isinstance(parsed[0], dict):
                    print(f"  → Keys: {list(parsed[0].keys())[:8]}")
                    # Lấy SKU codes
                    skus = [p.get("sku") or p.get("code") or p.get("id") for p in parsed if isinstance(p, dict)]
                    print(f"  → SKUs: {skus[:5]}")
                elif parsed and isinstance(parsed[0], str):
                    print(f"  → String array: {parsed[:5]}")
            elif isinstance(parsed, dict):
                print(f"  → Dict keys: {list(parsed.keys())[:8]}")
                # Tìm nested list
                for k, v in parsed.items():
                    if isinstance(v, list) and len(v) > 3:
                        print(f"  → [{k}]: list of {len(v)}")
                        if v and isinstance(v[0], dict):
                            print(f"     Keys: {list(v[0].keys())[:6]}")
            else:
                print(f"  → {str(parsed)[:200]}")
        except Exception:
            print(f"  → Raw: {body[:200]}")
    except Exception as e:
        print(f"  → Không lấy được: {str(e)[:80]}")
    print()

driver.quit()
