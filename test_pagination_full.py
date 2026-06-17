#!/usr/bin/env python3
"""
Debug - xem có bao nhiêu trang và SKU trong /thuoc?page=N
"""

import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = 'https://nhathuoclongchau.com.vn'

print("=== Lấy toàn bộ SKU codes từ /thuoc?page=N ===\n")

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

all_skus = set()
duplicates_count = 0

try:
    for page in range(1, 51):  # Thử 50 trang
        url = f'{BASE_URL}/thuoc?page={page}'
        print(f"Page {page:2d}: ", end='', flush=True)
        
        driver.get(url)
        time.sleep(1.5)
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        scripts = soup.find_all('script')
        
        page_skus = set()
        
        # Extract SKU codes from script tag JSON
        for script in scripts:
            content = script.string or ""
            if not content:
                continue
            
            # Match pattern: "sku":"00004206"
            sku_matches = re.findall(r'"sku"\s*:\s*"([^"]+)"', content)
            page_skus.update(sku_matches)
        
        before = len(all_skus)
        all_skus.update(page_skus)
        new_count = len(all_skus) - before
        duplicates = len(page_skus) - new_count
        duplicates_count += duplicates
        
        print(f"{len(page_skus)} SKU found | +{new_count} new | Total: {len(all_skus)}", end='')
        if duplicates > 0:
            print(f" | {duplicates} duplicates")
        else:
            print()
        
        # Stop if no new SKUs for 3 consecutive pages
        if new_count == 0:
            if page > 10:  # Nhưng phải chạy ít nhất 10 trang
                print("  → No new SKUs found for 3 pages, could stop here")
                break

finally:
    driver.quit()

print(f"\n{'='*60}")
print(f"✅ Summary:")
print(f"   Total unique SKUs: {len(all_skus)}")
print(f"   Total pages checked: {page}")
print(f"   Total duplicate SKUs across pages: {duplicates_count}")
print(f"{'='*60}")
