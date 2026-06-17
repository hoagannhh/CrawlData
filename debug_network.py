import sys, time, json
sys.path.insert(0, '.')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
# Bật logging network
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=options)

url = "https://nhathuoclongchau.com.vn/thuoc/thuoc-tieu-hoa-and-gan-mat"
driver.get(url)
time.sleep(4)

# Lấy tất cả network request
logs = driver.execute_script("return window.performance.getEntriesByType('resource');")

print("=== API calls liên quan đến thuốc ===")
for log in logs:
    name = log.get("name", "")
    if any(k in name for k in ["api", "product", "drug", "medicine", "item", "list", "search"]):
        print(f"  {name[:120]}")

# Tìm thêm trong performance logs
perf_logs = driver.get_log("performance")
print(f"\n=== Performance logs ({len(perf_logs)} entries) ===")
api_calls = []
for entry in perf_logs:
    try:
        msg = json.loads(entry["message"])["message"]
        if msg.get("method") == "Network.responseReceived":
            req_url = msg["params"]["response"]["url"]
            if any(k in req_url for k in ["/api/", "product", "drug", "thuoc", "item"]):
                api_calls.append(req_url)
                print(f"  {req_url[:120]}")
    except Exception:
        pass

driver.quit()
print(f"\nTổng API calls tìm được: {len(api_calls)}")