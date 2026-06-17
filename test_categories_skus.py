#!/usr/bin/env python3
"""
Debug - lấy SKU từ từng danh mục (/thuoc/category-name)
"""

import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = 'https://nhathuoclongchau.com.vn'

# Danh mục từ spider
CATEGORIES = [
    "/thuoc/thuoc-tim-mach-and-mau",
    "/thuoc/thuoc-tieu-hoa-and-gan-mat",
    "/thuoc/thuoc-khang-sinh-khang-nam",
    "/thuoc/thuoc-ho-hap",
    "/thuoc/thuoc-than-kinh",
    "/thuoc/thuoc-giam-dau-ha-sot-khang-viem",
    "/thuoc/thuoc-mat-tai-mui-hong",
    "/thuoc/thuoc-tiet-nieu-sinh-duc",
    "/thuoc/thuoc-bo-and-vitamin",
    "/thuoc/thuoc-ung-thu",
    "/thuoc/thuoc-co-xuong-khop",
    "/thuoc/thuoc-da-lieu",
    "/thuoc/thuoc-tri-tieu-duong",
    "/thuoc/thuoc-tiem-chich-and-dich-truyen",
    "/thuoc/thuoc-di-ung",
]

print("=== Lấy SKU từ từng danh mục ===\n")

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

all_skus = set()
category_stats = []

try:
    for cat_path in CATEGORIES:
        cat_url = BASE_URL + cat_path
        cat_name = cat_path.split('/')[-1][:30]
        print(f"📁 {cat_name:30s}: ", end='', flush=True)
        
        # Lấy trang 1 của danh mục
        url = f'{cat_url}?page=1'
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
        category_stats.append((cat_name, len(page_skus), new_count))

finally:
    driver.quit()

print(f"\n{'='*70}")
print(f"Category Stats:")
print(f"{'='*70}")
for cat, total, new in category_stats:
    print(f"  {cat:30s}: {total:3d} SKU | +{new:3d} new")

print(f"{'='*70}")
print(f"✅ Total unique SKUs from all categories: {len(all_skus)}")
print(f"{'='*70}")

# Estimate for max_pages
estimated_at_current_rate = len(all_skus) * 100 / len(CATEGORIES)
print(f"\n💡 Estimate:")
print(f"   With {len(CATEGORIES)} categories × 1 page each: {len(all_skus)} SKU")
print(f"   To get 1200 SKUs, need ~{1200 / len(all_skus) * len(CATEGORIES):.0f} categories or {1200 / (len(all_skus) / len(CATEGORIES)):.0f} pages per category")
