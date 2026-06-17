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

# Test 1 danh mục
cat_url = BASE_URL + "/thuoc/thuoc-tieu-hoa-and-gan-mat"
print(f"Mở: {cat_url}")
driver.get(cat_url)
time.sleep(3)

# Scroll 3 lần
urls = set()
for i in range(5):
    soup = BeautifulSoup(driver.page_source, "lxml")
    new = {BASE_URL + a["href"] for a in soup.find_all("a", href=True)
           if PRODUCT_PATTERN.search(a["href"])}
    before = len(urls)
    urls.update(new)
    print(f"Scroll {i+1}: +{len(urls)-before} → tổng {len(urls)}")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2.5)

driver.quit()
print(f"\nTổng URL thu được: {len(urls)}")
for u in list(urls)[:5]:
    print(f"  {u}")