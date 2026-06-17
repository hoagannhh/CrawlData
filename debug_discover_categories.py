"""
Debug: Discover all available categories on Long Châu
"""
import sys
sys.path.insert(0, '.')
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://nhathuoclongchau.com.vn"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

print("🔍 Discovering all medicine categories on Long Châu...\n")

# Navigate to main medicine page
driver.get(BASE_URL + "/thuoc")
time.sleep(3)

soup = BeautifulSoup(driver.page_source, "lxml")

# Look for category links
category_links = []

# Try different selectors
selectors = [
    "a[href*='/thuoc/'][href$!='']",  # Links containing /thuoc/
    ".category-link",
    ".cat-item a",
    "[class*='category'] a",
    "nav a",
    "aside a"
]

# Find all links that might be categories
all_links = soup.find_all("a", href=True)
for link in all_links:
    href = link.get("href", "")
    text = link.get_text(strip=True)
    
    # Filter for /thuoc/ links that look like categories (not products)
    if "/thuoc/" in href and href.endswith("/"):
        if text and len(text) > 2:  # Not too short
            category_links.append((text, href))
    elif "/thuoc/" in href and not ".html" in href and href.count("/") == 3:
        if text and len(text) > 2:
            category_links.append((text, href))

# Deduplicate
category_links = list(dict.fromkeys(category_links))

print(f"✓ Found {len(category_links)} categories:\n")
for i, (text, href) in enumerate(category_links, 1):
    print(f"{i:2}. {text[:40]:40} → {href}")

# Also try to find navigation menu with categories
nav = soup.find("nav")
if nav:
    print(f"\n📍 Found navigation element")
    nav_cats = nav.find_all("a")
    print(f"   Contains {len(nav_cats)} links")

driver.quit()
