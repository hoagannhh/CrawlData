import sys, time, json, requests

BASE_API = "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Access-Control-Allow-Origin": "*",
    "Content-Type": "application/json",
    "Referer": "https://nhathuoclongchau.com.vn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "X-Channel": "EStore",
    "order-channel": "1",
    "Origin": "https://nhathuoclongchau.com.vn",
}

# Test 1: Gọi without-inventory/search/list với mã sản phẩm đã biết
print("=== Test 1: Lấy chi tiết sản phẩm theo mã ===")
product_codes = ["00004206", "00009723", "00002990"]
r = requests.post(
    f"{BASE_API}/without-inventory/search/list",
    json=product_codes,
    headers=headers,
    timeout=10
)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Số sản phẩm trả về: {len(data)}")
    if data:
        first = data[0]
        print(f"Keys có trong response: {list(first.keys())}")
        print(f"\nSample product:")
        print(f"  name: {first.get('name','')[:80]}")
        print(f"  slug: {first.get('slug','')}")
        print(f"  shortDescription: {str(first.get('shortDescription',''))[:200]}")
        print(f"  webDescription: {str(first.get('webDescription',''))[:200]}")
        # In tất cả keys để xem có field nào hữu ích không
        print(f"\nFull keys: {list(first.keys())}")
else:
    print(f"Response: {r.text[:300]}")

time.sleep(2)

# Test 2: Tìm API lấy danh sách mã theo danh mục
print("\n=== Test 2: Tìm API danh sách theo category ===")
test_payloads = [
    {"slug": "thuoc/thuoc-tieu-hoa-and-gan-mat", "pageIndex": 1, "pageSize": 20},
    {"categorySlug": "thuoc-tieu-hoa-and-gan-mat", "pageIndex": 1, "pageSize": 20},
    {"slugs": ["thuoc/thuoc-tieu-hoa-and-gan-mat"], "pageIndex": 1, "pageSize": 20},
]
endpoints = [
    f"{BASE_API}/search/list",
    f"{BASE_API}/ecom/list",
    "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product/list",
]
for ep in endpoints[:2]:
    for payload in test_payloads[:1]:
        time.sleep(1.5)
        try:
            r2 = requests.post(ep, json=payload, headers=headers, timeout=10)
            print(f"POST {ep.split('/')[-1]}: {r2.status_code} | {r2.text[:200]}")
        except Exception as e:
            print(f"Lỗi: {e}")