import json, time, requests

BASE_API = "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://nhathuoclongchau.com.vn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
    "X-Channel": "EStore",
    "order-channel": "1",
    "Origin": "https://nhathuoclongchau.com.vn",
}

# Lấy chi tiết 1 sản phẩm
r = requests.post(
    f"{BASE_API}/without-inventory/search/list",
    json=["00004206"],
    headers=headers,
    timeout=10
)
data = r.json()
product = data[0]

# In toàn bộ để xem hết fields
print("=== FULL PRODUCT DATA ===")
print(json.dumps(product, ensure_ascii=False, indent=2))