import sys, time, re
sys.path.insert(0, '.')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

PRODUCT_PATTERN = re.compile(r"/thuoc/[a-z0-9\-]+-\d+\.html$")
BASE_URL = "https://nhathuoclongchau.com.vn"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

# Test các format URL phân trang khác nhau
test_urls = [
    "/thuoc/thuoc-tieu-hoa-and-gan-mat?page=2",
    "/thuoc/thuoc-tieu-hoa-and-gan-mat?p=2",
    "/thuoc/thuoc-tieu-hoa-and-gan-mat/2",
    "/thuoc/thuoc-tieu-hoa-and-gan-mat?offset=18",
    "/thuoc/thuoc-tieu-hoa-and-gan-mat?pageIndex=2",
]

for path in test_urls:
    url = BASE_URL + path
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "lxml")
    urls = {a["href"] for a in soup.find_all("a", href=True)
            if PRODUCT_PATTERN.search(a["href"])}
    current_url = driver.current_url
    print(f"\nURL test : {path}")
    print(f"URL thực : {current_url}")
    print(f"Sản phẩm: {len(urls)}")
    if urls:
        sample = list(urls)[:2]
        for u in sample:
            print(f"  {u}")

# Tìm pagination trong trang gốc
print("\n\n=== Tìm pagination trong trang danh mục ===")
driver.get(BASE_URL + "/thuoc/thuoc-tieu-hoa-and-gan-mat")
time.sleep(3)
soup = BeautifulSoup(driver.page_source, "lxml")

# Tìm tất cả link có số trang
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if any(k in href for k in ["page", "p=", "offset", "pageIndex"]) or \
       (text.isdigit() and int(text) > 1):
        print(f"  href={href} | text={text}")

# Tìm API endpoint trong script tags
print("\n=== Tìm API endpoint ===")
for script in soup.find_all("script"):
    content = script.string or ""
    if any(k in content for k in ["api", "fetch", "axios", "/v1/", "/api/"]):
        # In 200 ký tự xung quanh keyword
        for keyword in ["pageSize", "pageIndex", "currentPage"]:
            idx = content.find(keyword)
            if idx > 0:
                print(f"  [{keyword}]: ...{content[max(0,idx-50):idx+100]}...")
                break

driver.quit()