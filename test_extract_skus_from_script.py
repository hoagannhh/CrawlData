#!/usr/bin/env python3
"""
Extract product SKU codes từ script tags (JSON data) và test API.
"""

import time
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests

BASE_URL = 'https://nhathuoclongchau.com.vn'

print("=== Extract SKUs from script tags ===\n")

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

all_skus = set()

# Lấy từ nhiều trang để test
for page in range(1, 4):
    url = f'{BASE_URL}/thuoc?page={page}'
    print(f"📄 Page {page}: {url}")
    
    driver.get(url)
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, 'lxml')
    scripts = soup.find_all('script')
    
    page_skus = set()
    
    # Tìm script tags chứa product data
    for script in scripts:
        content = script.string or ""
        if not content:
            continue
            
        # Tìm JSON patterns với "sku" field
        # Pattern: "sku":"00004206"
        sku_matches = re.findall(r'"sku"\s*:\s*"([^"]+)"', content)
        if sku_matches:
            print(f"  Found {len(sku_matches)} SKUs in script tag")
            page_skus.update(sku_matches)
    
    all_skus.update(page_skus)
    print(f"  Page SKUs: {len(page_skus)} | Cumulative: {len(all_skus)}")
    
    if page_skus:
        print(f"  Sample SKUs: {list(page_skus)[:3]}")

driver.quit()

print(f"\n✅ Total unique SKUs: {len(all_skus)}")
print(f"All SKUs: {list(all_skus)[:10]}...")

# === Test API with extracted SKUs ===
print("\n\n=== Test API with extracted SKUs ===\n")

if all_skus:
    test_skus = list(all_skus)[:5]
    print(f"Testing with {len(test_skus)} SKUs: {test_skus}\n")
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Referer": "https://nhathuoclongchau.com.vn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
        "X-Channel": "EStore",
        "order-channel": "1",
    }
    
    api_url = "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product/without-inventory/search/list"
    
    try:
        r = requests.post(api_url, json=test_skus, headers=headers, timeout=10)
        print(f"📡 API Status: {r.status_code}")
        
        if r.status_code == 200:
            products = r.json()
            print(f"✅ Retrieved {len(products)} products from API\n")
            
            if products:
                print("Sample products:")
                for idx, p in enumerate(products[:3], 1):
                    print(f"\n{idx}. {p.get('name', 'N/A')[:50]}")
                    print(f"   SKU: {p.get('sku')}")
                    print(f"   Price: {p.get('price')}")
                    print(f"   Category: {p.get('category')}")
                    print(f"   Description: {str(p.get('shortDescription', 'N/A'))[:60]}")
        else:
            print(f"❌ API Error: {r.status_code}")
            print(f"   Response: {r.text[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("✅ Test completed!")
