import sys, json, time
sys.path.insert(0, '.')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from parsers.longchau.medicine_parser import LongChauParser

# Lấy URL thực tế từ DB
import sqlite3
conn = sqlite3.connect('data/pharma.db')
urls = [r[0] for r in conn.execute("SELECT url FROM medicines LIMIT 3").fetchall()]
conn.close()

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)

parser = LongChauParser()

for url in urls:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
        )
    except:
        pass
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "lxml")

    # In tất cả heading tìm được
    print("\n--- Headings trong trang ---")
    for tag in soup.find_all(["h1","h2","h3"])[:15]:
        print(f"  <{tag.name}> {tag.get_text(strip=True)[:80]}")

    # Thử parse
    result = parser.parse(soup, url)
    print("\n--- Kết quả parse ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))

driver.quit()