import sys, time, re
sys.path.insert(0, '.')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

PRODUCT_PATTERN = re.compile(r'/thuoc/[a-z0-9\-]+-\d+\.html$')
BASE_URL = 'https://nhathuoclongchau.com.vn'

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

total_urls = []
for page in range(1, 6):
    url = f'{BASE_URL}/thuoc?page={page}'
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*=".html"]'))
        )
    except:
        pass
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'lxml')
    links = [
        a['href'] for a in soup.find_all('a', href=True)
        if PRODUCT_PATTERN.search(a['href'])
    ]
    deduped = list(dict.fromkeys(links))
    total_urls.extend(deduped)
    print(f'Trang {page}: {len(deduped)} san pham')
    for u in deduped[:3]:
        print(f'  {u}')

driver.quit()
print(f'\nTong 5 trang: {len(total_urls)} URL')