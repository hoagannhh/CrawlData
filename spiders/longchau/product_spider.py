import re
import time
from bs4 import BeautifulSoup
from spiders.base_spider import BaseSpider
from parsers.longchau.medicine_parser import LongChauParser
from services.browser_service import BrowserService
from config.urls import SOURCES

BASE_URL = SOURCES["longchau"]["base_url"]
PRODUCT_PATTERN = re.compile(r"/thuoc/[a-z0-9\-]+-\d+\.html$")

# Danh mục thuốc với URL thực tế - Thêm nhiều danh mục hơn
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


class LongChauSpider(BaseSpider):
    source_name = "longchau"

    def __init__(self):
        super().__init__()
        self.parser  = LongChauParser()
        self.browser = BrowserService(headless=True)

    def get_list_urls(self, max_pages: int) -> list[str]:
        """Cào URL sản phẩm từ từng danh mục, scroll để load thêm."""
        all_urls = []
        self.browser.start()

        try:
            for cat_idx, cat_path in enumerate(CATEGORIES, 1):
                cat_name = cat_path.split('/')[-1][:25]
                cat_url = BASE_URL + cat_path
                self.logger.info(f"[{cat_idx}/{len(CATEGORIES)}] Category: {cat_name}")
                try:
                    cat_urls = self._scrape_category(cat_url, max_products=max_pages * 15)
                    self.logger.info(f"  ✓ Extracted: {len(cat_urls)} product URLs")
                    all_urls.extend(cat_urls)
                except Exception as e:
                    self.logger.error(f"  ✗ Error in {cat_name}: {e}")
        finally:
            self.browser.quit()

        final_urls = list(dict.fromkeys(all_urls))  # dedup giữ thứ tự
        self.logger.info(f"✅ Total unique URLs extracted: {len(final_urls)} products")
        return final_urls

    def _scrape_category(self, cat_url: str, max_products: int = 300) -> list[str]:
        """Scroll trang danh mục để load toàn bộ sản phẩm."""
        self.browser.driver.get(cat_url)
        time.sleep(3)

        urls = set()
        no_new_count = 0
        max_scrolls = max_products // 5  # More aggressive scrolling

        for scroll_num in range(max_scrolls):
            # Lấy URL hiện tại
            soup = BeautifulSoup(self.browser.driver.page_source, "lxml")
            new_urls = {
                BASE_URL + a["href"]
                for a in soup.find_all("a", href=True)
                if PRODUCT_PATTERN.search(a["href"])
            }

            before = len(urls)
            urls.update(new_urls)
            after = len(urls)
            new_count = after - before

            if new_count > 0:
                self.logger.debug(f"  Scroll {scroll_num+1}: +{new_count} URLs → Total: {after}")
                no_new_count = 0
            else:
                no_new_count += 1
                self.logger.debug(f"  Scroll {scroll_num+1}: No new URLs ({no_new_count}/3)")

            # Dừng nếu không load thêm được sau 3 lần scroll liên tiếp
            if no_new_count >= 3:
                self.logger.debug(f"  → Stopping: No new URLs for 3 consecutive scrolls")
                break

            # Scroll xuống cuối
            self.browser.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(2)

            # Kiểm tra nút "Xem thêm" / "Load more" nếu có
            try:
                # Thử các selector khác nhau cho nút load more
                selectors = [
                    "button.load-more",
                    "button[class*='load']",
                    "button[class*='xem-them']",
                    "a[class*='load-more']",
                    "button[data-action*='load']"
                ]
                
                btn_found = False
                for selector in selectors:
                    try:
                        btn = self.browser.driver.find_element("css selector", selector)
                        if btn.is_displayed():
                            self.logger.debug(f"  → Found load button: {selector}")
                            self.browser.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(2)
                            btn_found = True
                            break
                    except Exception:
                        pass
            except Exception as e:
                self.logger.debug(f"  No load button found: {e}")

        return list(urls)

    def parse_item(self, url: str) -> dict | None:
        """Cào nội dung 1 trang thuốc."""
        self.browser.start()
        soup = self.browser.get_soup(url, wait_selector="h1", wait_timeout=10)
        return self.parser.parse(soup, url)