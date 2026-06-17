"""
Debug: Count unique products after aggressive scrolling
"""
import sys
sys.path.insert(0, '.')
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://nhathuoclongchau.com.vn"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

PRODUCT_PATTERN = re.compile(r"/thuoc/[a-z0-9\-]+-\d+\.html$")

cat_url = BASE_URL + "/thuoc/thuoc-tim-mach-and-mau?page=1"
print(f"🔍 Testing URL with explicit page parameter: {cat_url}\n")

driver.get(cat_url)
time.sleep(3)

all_urls = set()

# Aggressive scrolling
for scroll_num in range(15):
    soup = BeautifulSoup(driver.page_source, "lxml")
    links = [a["href"] for a in soup.find_all("a", href=True) if PRODUCT_PATTERN.search(a["href"])]
    
    before = len(all_urls)
    all_urls.update(links)
    after = len(all_urls)
    new = after - before
    
    print(f"Scroll {scroll_num+1}: Found {len(links)} links, +{new} new, Total: {after}")
    
    if new == 0 and scroll_num > 3:
        print("✓ No new products after scroll, stopping")
        break
    
    # Aggressive scroll
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1.5)

print(f"\n✅ TOTAL UNIQUE PRODUCTS: {len(all_urls)}")
if all_urls:
    print(f"   Examples: {list(all_urls)[:5]}")

# Try page 2
print(f"\n🔍 Checking page 2...")
driver.get(BASE_URL + "/thuoc/thuoc-tim-mach-and-mau?page=2")
time.sleep(3)

soup = BeautifulSoup(driver.page_source, "lxml")
links_page2 = [a["href"] for a in soup.find_all("a", href=True) if PRODUCT_PATTERN.search(a["href"])]
print(f"   Page 2 found: {len(links_page2)} links")
if len(links_page2) > 0:
    print(f"   Are they the same? {set(links_page2) == set(links)}")

driver.quit()
