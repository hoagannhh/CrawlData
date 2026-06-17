#!/usr/bin/env python3
"""
Test spider mới sử dụng pagination thay vì scroll.
Strategy: Dùng /thuoc?page=N để lấy toàn bộ sản phẩm từ tất cả danh mục.
"""

import time
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

PRODUCT_PATTERN = re.compile(r'/thuoc/[a-z0-9\-]+-\d+\.html$')
BASE_URL = 'https://nhathuoclongchau.com.vn'

# === Strategy 1: Sử dụng pagination URL ===
print("=== Strategy 1: Pagination via ?page=N ===")
all_products = []
product_urls = set()

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

try:
    for page in range(1, 11):  # Thử 10 trang
        url = f'{BASE_URL}/thuoc?page={page}'
        print(f"\n📄 Trang {page}: {url}")
        driver.get(url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        links = soup.find_all('a', href=True)
        
        page_products = [
            BASE_URL + a['href'] 
            for a in links 
            if PRODUCT_PATTERN.search(a['href'])
        ]
        
        before = len(product_urls)
        product_urls.update(page_products)
        new_count = len(product_urls) - before
        
        print(f"   Found: {len(page_products)} | New: {new_count} | Total: {len(product_urls)}")
        
        if new_count == 0 and page > 3:
            print("   → Không có sản phẩm mới, dừng.")
            break
            
        if page == 1 and page_products:
            for p in page_products[:2]:
                print(f"     • {p}")
                
finally:
    driver.quit()

print(f"\n✅ Tổng sản phẩm: {len(product_urls)}")

# === Strategy 2: Sử dụng API để lấy chi tiết sản phẩm ===
print("\n\n=== Strategy 2: Lấy chi tiết sản phẩm từ API ===")

sample_urls = list(product_urls)[:3]
# Extract product codes từ URLs
product_codes = []
for url in sample_urls:
    # Format: /thuoc/product-name-CODE.html
    match = re.search(r'-(\d+)\.html$', url)
    if match:
        product_codes.append(match.group(1))

print(f"Product codes từ URLs: {product_codes}")

if product_codes:
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
        r = requests.post(api_url, json=product_codes, headers=headers, timeout=10)
        print(f"\n📡 API Response: {r.status_code}")
        
        if r.status_code == 200:
            products = r.json()
            print(f"   ✅ Lấy được {len(products)} sản phẩm")
            
            if products:
                p = products[0]
                print(f"\n   Sample product:")
                print(f"     • Name: {p.get('name', 'N/A')[:50]}")
                print(f"     • SKU: {p.get('sku', 'N/A')}")
                print(f"     • Slug: {p.get('slug', 'N/A')}")
                print(f"     • Category: {p.get('category', 'N/A')}")
                print(f"     • Price: {p.get('price', 'N/A')}")
                print(f"     • Description: {str(p.get('shortDescription', 'N/A'))[:60]}")
        else:
            print(f"   ❌ Error: {r.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "="*60)
print("✅ Test hoàn tất!")
