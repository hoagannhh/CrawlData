#!/usr/bin/env python3
"""
Debug - tìm tất cả sub-categories của Long Châu
"""

import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = 'https://nhathuoclongchau.com.vn'

print("=== Tìm tất cả danh mục và sub-categories ===\n")

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

try:
    # Lấy trang chủ danh mục
    driver.get(f'{BASE_URL}/thuoc')
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    # Tìm tất cả category links
    category_links = soup.find_all('a', href=re.compile(r'^/thuoc/[a-z-]+/?$'))
    
    print(f"Total category links: {len(category_links)}\n")
    
    categories = {}
    for link in category_links:
        href = link.get('href', '').strip('/')
        text = link.get_text(strip=True)
        if href and text and '/thuoc' in href:
            # Remove /thuoc/ prefix
            cat_slug = href.replace('/thuoc/', '')
            if cat_slug:  # Skip empty
                if cat_slug not in categories:
                    categories[cat_slug] = text
    
    print(f"Unique categories: {len(categories)}\n")
    for slug, name in sorted(categories.items()):
        print(f"  {slug:40s} | {name}")
    
    # Bây giờ test xem mỗi category có sub-categories không
    print("\n\n=== Checking for sub-categories ===\n")
    
    sub_categories = {}
    for cat_slug in list(categories.keys())[:5]:  # Test 5 danh mục đầu
        url = f'{BASE_URL}/thuoc/{cat_slug}'
        driver.get(url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        
        # Tìm sub-category links (pattern: /thuoc/category/subcategory)
        sub_links = soup.find_all('a', href=re.compile(rf'^/thuoc/{cat_slug}/[a-z-]+/?$'))
        
        if sub_links:
            print(f"Category: {cat_slug}")
            for link in sub_links[:5]:  # Show first 5
                sub_href = link.get('href', '').strip('/')
                sub_text = link.get_text(strip=True)
                print(f"  → {sub_href:50s} | {sub_text}")
            print()

finally:
    driver.quit()

print("\n" + "="*60)
print("Note: If there are many sub-categories, they can provide")
print("more products to reach 1200 target")
