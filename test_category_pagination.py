#!/usr/bin/env python3
"""
Debug - lấy tất cả SKU từ pagination của 1 danh mục
Ví dụ: /thuoc/thuoc-da-lieu?page=1, ?page=2, etc.
"""

import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = 'https://nhathuoclongchau.com.vn'

# Test với danh mục có nhiều sản phẩm nhất
test_category = "/thuoc/thuoc-da-lieu"  # Da liễu có nhiều mụn, chàm, etc.

print(f"=== Lấy SKU từ pagination của danh mục: {test_category} ===\n")

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

all_skus = set()

try:
    for page in range(1, 31):  # Thử 30 trang
        url = f'{BASE_URL}{test_category}?page={page}'
        print(f"Page {page:2d}: ", end='', flush=True)
        
        driver.get(url)
        time.sleep(1.5)
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        scripts = soup.find_all('script')
        
        page_skus = set()
        
        # Extract SKU codes
        for script in scripts:
            content = script.string or ""
            if not content:
                continue
            sku_matches = re.findall(r'"sku"\s*:\s*"([^"]+)"', content)
            page_skus.update(sku_matches)
        
        before = len(all_skus)
        all_skus.update(page_skus)
        new_count = len(all_skus) - before
        
        print(f"{len(page_skus):3d} SKU | +{new_count:3d} new | Total: {len(all_skus):4d}")
        
        # Stop if no new SKUs for 2 pages
        if new_count == 0 and page > 5:
            print("  → No new SKUs found, stopping")
            break

finally:
    driver.quit()

print(f"\n{'='*60}")
print(f"✅ Summary for {test_category}:")
print(f"   Unique SKUs: {len(all_skus)}")
print(f"   Pages checked: {page}")
print(f"{'='*60}")

if len(all_skus) > 0:
    # Estimate: Nếu danh mục này có X SKU, và có 15 danh mục
    estimated_total = len(all_skus) * 15 / 2  # Chia 2 vì danh mục không đều
    print(f"\n💡 Estimate:")
    print(f"   This category: {len(all_skus)} SKU")
    print(f"   15 categories avg: ~{estimated_total:.0f} SKU total")
