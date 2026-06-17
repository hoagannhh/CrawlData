import sys, time, re
sys.path.insert(0, '.')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

options = Options()
# Bật headless=False để xem thực tế
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

BASE_URL = 'https://nhathuoclongchau.com.vn/thuoc'
driver.get(BASE_URL)
time.sleep(4)

soup = BeautifulSoup(driver.page_source, 'lxml')

# Tìm tất cả element liên quan đến pagination
print("=== Tìm pagination elements ===")
for tag in soup.find_all(["a", "button", "div", "nav"],
                          class_=lambda c: c and any(
                              k in str(c).lower()
                              for k in ["page", "paging", "pagination", "next", "load"]
                          )):
    print(f"  <{tag.name}> class={tag.get('class')} href={tag.get('href','')[:60]} text={tag.get_text(strip=True)[:30]}")

# Tìm nút "xem thêm" / "load more"
print("\n=== Tìm nút Load More / Xem thêm ===")
for tag in soup.find_all(["button", "a", "div", "span"]):
    text = tag.get_text(strip=True).lower()
    if any(k in text for k in ["xem thêm", "load more", "tải thêm", "next", "tiếp"]):
        print(f"  <{tag.name}> class={tag.get('class')} text='{tag.get_text(strip=True)}'")

# In URL hiện tại
print(f"\n=== URL hiện tại ===")
print(driver.current_url)

# Scroll xuống cuối xem có load thêm không
print("\n=== Scroll xuống cuối trang ===")
PRODUCT_PATTERN = re.compile(r'/thuoc/[a-z0-9\-]+-\d+\.html$')

before_scroll = len([
    a for a in soup.find_all('a', href=True)
    if PRODUCT_PATTERN.search(a['href'])
])
print(f"Sản phẩm trước scroll: {before_scroll}")

# Scroll từ từ
for i in range(5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

soup2 = BeautifulSoup(driver.page_source, 'lxml')
after_scroll = len([
    a for a in soup2.find_all('a', href=True)
    if PRODUCT_PATTERN.search(a['href'])
])
print(f"Sản phẩm sau scroll: {after_scroll}")

# Lưu HTML để xem
with open("debug_pagination.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("\nĐã lưu → debug_pagination.html")

input("Nhấn Enter để đóng browser...")
driver.quit()