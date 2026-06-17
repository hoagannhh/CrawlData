"""
Debug: Check if category pages have products and what format they use
"""
import sys
sys.path.insert(0, '.')
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://nhathuoclongchau.com.vn"
CATEGORIES = [
    "/thuoc/thuoc-tim-mach-and-mau",
    "/thuoc/thuoc-tieu-hoa-and-gan-mat",
]

PRODUCT_PATTERN = re.compile(r"/thuoc/[a-z0-9\-]+-\d+\.html$")

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

print(f"\n🔍 Checking {len(CATEGORIES)} categories...\n")

for cat_path in CATEGORIES:
    cat_url = BASE_URL + cat_path
    print(f"📍 Category: {cat_path}")
    print(f"   URL: {cat_url}")
    
    try:
        driver.get(cat_url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "lxml")
        
        # 1. Check for product links with standard pattern
        product_links = soup.find_all("a", href=True)
        matching = [a for a in product_links if PRODUCT_PATTERN.search(a["href"])]
        print(f"   ✓ Product links found: {len(matching)}")
        
        if matching:
            print(f"     Examples: {[a['href'][:50] for a in matching[:3]]}")
        
        # 2. Check for scripts with SKU data
        scripts = soup.find_all("script")
        sku_found = 0
        for script in scripts:
            content = script.string or ""
            sku_matches = re.findall(r'"sku"\s*:\s*"([^"]+)"', content)
            sku_found += len(sku_matches)
        print(f"   ✓ SKUs in scripts: {sku_found}")
        
        # 3. Check page structure
        product_cards = soup.find_all(class_=re.compile(r"product|item|card", re.I))
        print(f"   ✓ Product containers (.product/.item/.card): {len(product_cards)}")
        
        # 4. Look for pagination
        paginations = soup.find_all(class_=re.compile(r"paginat|page", re.I))
        print(f"   ✓ Pagination elements: {len(paginations)}")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print()

driver.quit()
print("✅ Debug check complete")
