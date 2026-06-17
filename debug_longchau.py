import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

options = Options()
# options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--window-size=1920,1080")

# Không dùng webdriver-manager, dùng Chrome có sẵn
driver = webdriver.Chrome(options=options)

try:
    url = "https://nhathuoclongchau.com.vn/thuoc?page=1"
    print(f"Đang mở: {url}")
    driver.get(url)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "lxml")
    print(f"Title: {soup.title.text if soup.title else 'Không có'}")

    links = soup.find_all("a", href=True)
    print(f"Tổng link: {len(links)}")

    drug_links = [
        a["href"] for a in links
        if any(k in a["href"] for k in ["/thuoc/", "/san-pham/", "-p."])
    ]
    print(f"Link sản phẩm: {len(drug_links)}")
    for l in drug_links[:10]:
        print(f"  {l}")

    with open("debug_page_selenium.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Đã lưu → debug_page_selenium.html")

finally:
    driver.quit()