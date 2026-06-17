import sys, time, json, requests
sys.path.insert(0, '.')

# Thử gọi thẳng API danh mục để lấy danh sách mã sản phẩm
BASE_API = "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://nhathuoclongchau.com.vn",
    "Referer": "https://nhathuoclongchau.com.vn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
}

# Test 1: Thử API search với slug danh mục
print("=== Test 1: Search by category slug ===")
payload = {
    "slug": "thuoc/thuoc-tieu-hoa-and-gan-mat",
    "pageIndex": 1,
    "pageSize": 20
}
try:
    r = requests.post(f"{BASE_API}/search/list", json=payload, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Lỗi: {e}")

# Test 2: Thử format khác
print("\n=== Test 2: Search list format 2 ===")
payload2 = {
    "slugs": ["thuoc/thuoc-tieu-hoa-and-gan-mat"],
    "pageIndex": 1,
    "pageSize": 20
}
try:
    r2 = requests.post(f"{BASE_API}/search/list", json=payload2, headers=headers, timeout=10)
    print(f"Status: {r2.status_code}")
    print(f"Response: {r2.text[:500]}")
except Exception as e:
    print(f"Lỗi: {e}")

# Test 3: Thử endpoint khác
print("\n=== Test 3: Category list endpoint ===")
test_endpoints = [
    f"{BASE_API}/category/list",
    f"{BASE_API}/search/category",
    "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/category/list",
]
for ep in test_endpoints:
    try:
        r3 = requests.get(ep, headers=headers, timeout=5)
        print(f"GET {ep}: {r3.status_code} | {r3.text[:200]}")
    except Exception as e:
        print(f"Lỗi {ep}: {e}")

# Test 4: Dùng Selenium bắt API với tham số đầy đủ hơn
print("\n=== Test 4: Bắt full request qua Selenium ===")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
driver = webdriver.Chrome(options=options)

driver.get("https://nhathuoclongchau.com.vn/thuoc/thuoc-tieu-hoa-and-gan-mat")
time.sleep(5)

perf_logs = driver.get_log("performance")
for entry in perf_logs:
    try:
        msg = json.loads(entry["message"])["message"]
        if msg.get("method") == "Network.requestWillBeSent":
            req = msg["params"].get("request", {})
            req_url = req.get("url", "")
            if "search-product-service" in req_url and req.get("method") == "POST":
                print(f"\nURL: {req_url}")
                print(f"Headers: {json.dumps(dict(list(req.get('headers',{}).items())[:8]), ensure_ascii=False)}")
                post_data = req.get("postData", "")
                print(f"Body: {post_data[:300]}")
    except Exception:
        pass

driver.quit()