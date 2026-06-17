#!/usr/bin/env python3
"""
Debug - tìm xem product code/SKU nằm ở đâu trong HTML
"""

import time
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = 'https://nhathuoclongchau.com.vn'

print("=== Lấy trang và tìm product codes ===")
options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

# Lấy trang danh sách
driver.get(f'{BASE_URL}/thuoc?page=1')
time.sleep(3)

# Lưu HTML để inspect
with open('page_inspect.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
print("✅ Đã lưu HTML → page_inspect.html")

soup = BeautifulSoup(driver.page_source, 'lxml')

# === Tìm product elements ===
print("\n=== 1. Tìm product elements ===")

# Tìm tất cả divs/cards có chứa class product, item, card
product_containers = soup.find_all(['div', 'article'], class_=re.compile(r'(product|item|card|drug)', re.I))
print(f"Found {len(product_containers)} potential product containers")

# Lấy element đầu tiên và in toàn bộ attributes
if product_containers:
    first_container = product_containers[0]
    print(f"\nFirst container HTML (first 500 chars):")
    print(str(first_container)[:500])
    print(f"\nContainer classes: {first_container.get('class')}")
    print(f"Container data attributes: ")
    for attr, val in first_container.attrs.items():
        if 'data' in attr or 'id' in attr or 'code' in attr:
            print(f"  {attr}={val}")

# === Tìm product links ===
print("\n=== 2. Tìm product links và attributes ===")
product_links = soup.find_all('a', href=re.compile(r'/thuoc/[a-z0-9\-]+-\d+\.html$'))
print(f"Found {len(product_links)} product links")

if product_links:
    link = product_links[0]
    print(f"\nFirst link:")
    print(f"  href: {link.get('href')}")
    print(f"  classes: {link.get('class')}")
    print(f"  data attributes:")
    for attr, val in link.attrs.items():
        if 'data' in attr.lower():
            print(f"    {attr}={val}")
    
    # Tìm parent container
    parent = link.find_parent(['div', 'article', 'li'])
    if parent:
        print(f"\n  Parent element:")
        print(f"    tag: {parent.name}")
        print(f"    class: {parent.get('class')}")
        print(f"    data attributes:")
        for attr, val in parent.attrs.items():
            if 'data' in attr.lower() or 'code' in attr.lower() or 'sku' in attr.lower():
                print(f"      {attr}={val}")

# === Tìm hidden data trong script tags ===
print("\n=== 3. Tìm product data trong <script> tags ===")
scripts = soup.find_all('script')
print(f"Found {len(scripts)} script tags")

for idx, script in enumerate(scripts):
    content = script.string or ""
    if content and len(content) > 100:
        # Tìm JSON patterns
        if any(k in content for k in ['product', 'item', 'data', 'code', 'sku']):
            # In đoạn có chứa product data
            print(f"\nScript {idx+1} (có product-related content):")
            
            # Tìm JSON object
            json_match = re.search(r'\{[^{}]*(?:[\'"](?:code|sku|id|name)[\'"]:[^,}]*[,}])', content)
            if json_match:
                snippet = json_match.group(0)[:200]
                print(f"  Sample: {snippet}")

# === Tìm trong window.__data hoặc state ===
print("\n=== 4. Tìm window data hoặc props ===")
window_data_scripts = [s for s in scripts if s.string and ('window' in (s.string or '') or 'props' in (s.string or ''))]
print(f"Found {len(window_data_scripts)} scripts with window/props data")

if window_data_scripts:
    for script in window_data_scripts[:2]:
        content = script.string or ""
        if 'product' in content.lower() or 'code' in content.lower():
            # In phần có product
            idx = content.find('product')
            if idx >= 0:
                print(f"\nSnippet around 'product':")
                print(f"  ...{content[max(0, idx-50):idx+150]}...")

# === Tìm trong data-* attributes của product elements ===
print("\n=== 5. Kiểm tra tất cả data-* attributes ===")
all_elements_with_data = soup.find_all(attrs={'data-code': True})
print(f"Elements with data-code: {len(all_elements_with_data)}")

all_elements_with_sku = soup.find_all(attrs={'data-sku': True})
print(f"Elements with data-sku: {len(all_elements_with_sku)}")

all_elements_with_id = soup.find_all(attrs={'data-id': True})
print(f"Elements with data-id: {len(all_elements_with_id)}")

# In samples
for attr_name in ['data-code', 'data-sku', 'data-id', 'data-product-code']:
    elements = soup.find_all(attrs={attr_name: True})
    if elements:
        print(f"\nFound {len(elements)} elements with {attr_name}:")
        for elem in elements[:3]:
            val = elem.get(attr_name)
            href = elem.get('href', '')[:50]
            print(f"  {attr_name}={val} | href={href}...")

driver.quit()
print("\n" + "="*60)
print("✅ Debug completed - check page_inspect.html for full HTML")
