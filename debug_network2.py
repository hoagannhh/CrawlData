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
api_calls = []
for entry in perf_logs:
    try:
        msg = json.loads(entry["message"])["message"]
        if msg.get("method") == "Network.responseReceived":
            req_url = msg["params"]["response"]["url"]
            # In TẤT CẢ api calls
            if "/api/" in req_url or "estore" in req_url or "gateway" in req_url:
                api_calls.append(req_url)
    except Exception:
        pass

driver.quit()

# In tất cả để tìm endpoint sản phẩm
print(f"Tổng: {len(api_calls)} API calls\n")
for u in api_calls:
    print(u[:150])
    