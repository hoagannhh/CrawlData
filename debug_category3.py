import sys, time, re
sys.path.insert(0, '.')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

PRODUCT_PATTERN = re.compile(r"/thuoc/[a-z0-9\-]+-\d+\.html$")
BASE_URL = "https://nhathuoclongchau.com.vn"
CAT = "/thuoc/thuoc-tieu-hoa-and-gan-mat"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

all_urls = set()

for page in range(1, 8):
    # Trang 1 không có số, trang 2+ có /{page}
    url = BASE_URL + CAT if page == 1 else BASE_URL + CAT + f"/{page}"
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "lxml")
    page_urls = {
        a["href"] for a in soup.find_all("a", href=True)
        if PRODUCT_PATTERN.search(a["href"])
        and "/thuoc/" in a["href"]
        and a["href"] not in ["/thuoc/thuoc-tieu-hoa-and-gan-mat"]
    }

    # Loại bỏ URL danh mục, chỉ giữ sản phẩm thực
    product_urls = {u for u in page_urls if re.search(r"-\d+\.html$", u)}

    before = len(all_urls)
    all_urls.update(product_urls)
    new_count = len(all_urls) - before

    print(f"Trang {page}: {len(product_urls)} sp | +{new_count} mới | tổng {len(all_urls)}")

    if new_count == 0:
        print("  → Không có sản phẩm mới, dừng.")
        break

    # In mẫu trang đầu
    if page == 1:
        for u in list(product_urls)[:3]:
            print(f"  {u}")

driver.quit()
print(f"\nTổng sản phẩm unique: {len(all_urls)}")