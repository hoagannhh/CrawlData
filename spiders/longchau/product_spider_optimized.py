"""
Long Châu Spider (Optimized v2)
Strategy:
  1. Selenium scroll từng category page → collect product URLs từ <a> tags
  2. Selenium fetch từng product page → parse full drug leaflet
  3. LongChauParser → parse nội dung: indication, dosage, adverse_effect, ...
"""

import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from spiders.base_spider import BaseSpider
from parsers.longchau.medicine_parser import LongChauParser
from config.urls import SOURCES
from utils.logger import get_logger

logger = get_logger("spider.longchau_optimized")

BASE_URL = SOURCES["longchau"]["base_url"]

CATEGORIES = [
    "/thuoc/thuoc-tim-mach-and-mau",
    "/thuoc/thuoc-tieu-hoa-and-gan-mat",
    "/thuoc/thuoc-khang-sinh-khang-nam",
    "/thuoc/thuoc-ho-hap",
    "/thuoc/thuoc-than-kinh",
    "/thuoc/thuoc-giam-dau-ha-sot-khang-viem",
    "/thuoc/thuoc-mat-tai-mui-hong",
    "/thuoc/thuoc-tiet-nieu-sinh-duc",
    "/thuoc/thuoc-bo-and-vitamin",
    "/thuoc/thuoc-ung-thu",
    "/thuoc/thuoc-co-xuong-khop",
    "/thuoc/thuoc-da-lieu",
    "/thuoc/thuoc-tri-tieu-duong",
    "/thuoc/thuoc-tiem-chich-and-dich-truyen",
    "/thuoc/thuoc-di-ung",
    "/thuoc/thuoc-trang-tri-soc",
    "/thuoc/thuoc-ho-sot",
    "/thuoc/thuoc-ung-thu-hoa-tri",
]


def _build_selenium_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=vi-VN")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


PRODUCT_URL_RE = re.compile(r"^/thuoc/[^/]+\.html$")


class LongChauOptimizedSpider(BaseSpider):
    """
    Step 1: Selenium scroll each category page → collect product URLs from <a> tags.
    Step 2: Selenium fetch each product page → parse full drug leaflet.
    """
    source_name = "longchau"

    def __init__(self):
        super().__init__()
        self.parser = LongChauParser()

    def _extract_product_urls_from_page(self, driver) -> set:
        """Trích xuất product URLs từ <a href="/thuoc/...html"> trong DOM hiện tại."""
        soup = BeautifulSoup(driver.page_source, "lxml")
        urls = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if PRODUCT_URL_RE.match(href):
                urls.add(f"{BASE_URL}{href}")
        return urls

    def _collect_urls_via_selenium(self, max_pages: int) -> set:
        """
        Scroll từng category page, thu thập product URLs từ anchor tags.
        max_pages = số lần scroll tối đa mỗi category.
        """
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=options)

        all_urls = set()

        try:
            for cat_idx, cat_path in enumerate(CATEGORIES, 1):
                cat_name = cat_path.split("/")[-1][:25]
                self.logger.info(f"[{cat_idx}/{len(CATEGORIES)}] {cat_name}")

                driver.get(f"{BASE_URL}{cat_path}")
                time.sleep(3)

                consecutive_no_new = 0

                for scroll_num in range(max_pages):
                    page_urls = self._extract_product_urls_from_page(driver)

                    before = len(all_urls)
                    all_urls.update(page_urls)
                    new_count = len(all_urls) - before

                    self.logger.info(
                        f"  Scroll {scroll_num+1}: {len(page_urls)} URLs trên trang | "
                        f"+{new_count} new | Total: {len(all_urls)}"
                    )

                    if new_count == 0:
                        consecutive_no_new += 1
                        if consecutive_no_new >= 3:
                            self.logger.info("  → Không có URL mới, sang category tiếp.")
                            break
                    else:
                        consecutive_no_new = 0

                    # Scroll xuống để trigger lazy load
                    prev_height = driver.execute_script("return document.body.scrollHeight")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2.5)

                    # Chờ thêm nếu trang đang load (chiều cao thay đổi)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height > prev_height:
                        time.sleep(1.5)

                    # Bấm nút "Xem thêm" nếu có
                    for selector in [
                        "button.btn-load-more",
                        "button[class*='load-more']",
                        "button[class*='loadmore']",
                        "a[class*='load-more']",
                    ]:
                        try:
                            btn = driver.find_element("css selector", selector)
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(2)
                                break
                        except Exception:
                            pass

        finally:
            driver.quit()

        return all_urls

    def get_list_urls(self, max_pages: int) -> list:
        """
        max_pages: số lần scroll tối đa mỗi category.
        """
        self.logger.info("Bước 1: Thu thập product URLs từ category pages...")
        all_urls = self._collect_urls_via_selenium(max_pages)
        self.logger.info(f"Total product URLs: {len(all_urls)}")
        return list(all_urls)

    def parse_item(self, url: str) -> dict | None:
        """Dùng driver dùng chung (self._shared_driver) nếu có, fallback tạo mới."""
        driver = getattr(self, "_shared_driver", None)
        own_driver = False
        try:
            if driver is None:
                driver = _build_selenium_driver()
                own_driver = True

            driver.get(url)
            try:
                WebDriverWait(driver, 12).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                )
            except Exception:
                self.logger.warning(f"Timeout chờ h1 tại {url}")
            time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "lxml")
            return self.parser.parse(soup, url)

        except Exception as e:
            self.logger.error(f"Lỗi fetch [{url}]: {e}")
            return None
        finally:
            if own_driver and driver:
                driver.quit()

    def run(self, max_pages: int = 5) -> list:
        """
        max_pages: số trang Selenium scroll cho mỗi category.
        Với 18 categories × 5 pages = 90 lần scroll → ~300-500 sản phẩm.
        Dùng 1 Selenium driver dùng chung cho toàn bộ → nhanh hơn nhiều.
        """
        from utils.file_handler import load_scraped_urls, save_scraped_urls, save_checkpoint
        from tqdm import tqdm

        self.logger.info(f"LongChau Optimized Spider (max_pages={max_pages})")

        scraped_urls = load_scraped_urls(self.source_name)
        all_urls = self.get_list_urls(max_pages)
        new_urls = [u for u in all_urls if u not in scraped_urls]

        self.logger.info(
            f"Tổng {len(all_urls)} URL | Mới: {len(new_urls)} | Đã cào: {len(scraped_urls)}"
        )

        results, batch = [], []

        # Một driver dùng chung cho tất cả parse_item — khởi động 1 lần duy nhất
        self._shared_driver = _build_selenium_driver()
        self.logger.info("Khởi động Selenium driver dùng chung...")

        try:
            for url in tqdm(new_urls, desc="longchau"):
                try:
                    item = self.parse_item(url)
                    if item:
                        results.append(item)
                        batch.append(item)
                        scraped_urls.add(url)
                except Exception as e:
                    self.logger.error(f"Lỗi [{url}]: {e}")

                if len(batch) >= 20:
                    batch_num = len(results) // 20
                    save_checkpoint(batch, self.source_name, batch_num)
                    save_scraped_urls(self.source_name, scraped_urls)
                    self.logger.info(f"Checkpoint {batch_num}: {len(results)} records")
                    batch = []
        finally:
            self._shared_driver.quit()
            self._shared_driver = None
            self.logger.info("Đã đóng Selenium driver.")

        if batch:
            batch_num = (len(results) // 20) + 1
            save_checkpoint(batch, self.source_name, batch_num)
            save_scraped_urls(self.source_name, scraped_urls)

        self.logger.info(f"Hoàn thành LongChau: {len(results)} records")
        return results
