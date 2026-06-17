#!/usr/bin/env python3
"""
Debug chi tiết - xem product codes extract thế nào và API trả về gì.
"""

import time
import re
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = 'https://nhathuoclongchau.com.vn'
PRODUCT_PATTERN = re.compile(r'/thuoc/[a-z0-9\-]+-\d+\.html$')

print("=== 1. Lấy trang đầu tiên ===")
options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

url = f'{BASE_URL}/thuoc'
driver.get(url)
time.sleep(3)

soup = BeautifulSoup(driver.page_source, 'lxml')
links = soup.find_all('a', href=True)

# Filter sản phẩm
product_links = [
    a['href'] 
    for a in links 
    if PRODUCT_PATTERN.search(a['href'])
][:10]  # Lấy 10 cái đầu

print(f"Product links found: {len(product_links)}")
for idx, link in enumerate(product_links, 1):
    print(f"  {idx}. {link}")

driver.quit()

# === 2. Thử các cách extract product codes ===
print("\n=== 2. Extract product codes ===")
for link in product_links[:5]:
    # Method 1: Last number
    match1 = re.search(r'-(\d+)\.html$', link)
    code1 = match1.group(1) if match1 else "N/A"
    
    # Method 2: Full URL
    code2 = link
    
    # Method 3: Slug part
    slug_match = re.search(r'/thuoc/([^/]+)\.html$', link)
    slug = slug_match.group(1) if slug_match else "N/A"
    
    print(f"  Link: {link}")
    print(f"    → Last-num: {code1}")
    print(f"    → Slug: {slug}")

# === 3. Test API với các product codes khác nhau ===
print("\n=== 3. Test API với product codes ===")

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://nhathuoclongchau.com.vn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "X-Channel": "EStore",
    "order-channel": "1",
}

api_url = "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product/without-inventory/search/list"

# Test 1: Với product codes từ regex
test_codes_1 = []
for link in product_links[:3]:
    match = re.search(r'-(\d+)\.html$', link)
    if match:
        test_codes_1.append(match.group(1))

print(f"Test 1 - Codes from regex: {test_codes_1}")
if test_codes_1:
    r1 = requests.post(api_url, json=test_codes_1, headers=headers, timeout=10)
    print(f"  Status: {r1.status_code}")
    data1 = r1.json() if r1.status_code == 200 else []
    print(f"  Results: {len(data1)} products")
    if data1:
        print(f"  First product keys: {list(data1[0].keys())[:5]}")

# Test 2: Với known codes từ debug_api3.py
known_codes = ["00004206", "00009723", "00002990"]
print(f"\nTest 2 - Known codes: {known_codes}")
r2 = requests.post(api_url, json=known_codes, headers=headers, timeout=10)
print(f"  Status: {r2.status_code}")
data2 = r2.json() if r2.status_code == 200 else []
print(f"  Results: {len(data2)} products")
if data2:
    p = data2[0]
    print(f"  Sample: {p.get('name', 'N/A')[:50]}")
    print(f"  Keys: {list(p.keys())[:8]}")

# === 4. Cố gắng parse SKU/code từ response ===
print("\n=== 4. Parse SKU từ API response ===")
if data2:
    for idx, p in enumerate(data2[:3], 1):
        code = p.get('sku') or p.get('displayCode') or p.get('code')
        print(f"  Product {idx}:")
        print(f"    • SKU: {p.get('sku')}")
        print(f"    • displayCode: {p.get('displayCode')}")
        print(f"    • code: {p.get('code')}")
        print(f"    → Effective code: {code}")
