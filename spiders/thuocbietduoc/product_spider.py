"""
Thuoc Biet Duoc Spider
Strategy:
  1. Lấy danh sách nhóm thuốc từ drgsearch.aspx (35 nhóm, mỗi nhóm hàng trăm thuốc)
  2. Với mỗi nhóm: paginate qua tất cả trang, thu thập URL thuốc chi tiết
  3. Fetch từng trang thuốc, parse nội dung

URL pattern thuốc chi tiết: https://thuocbietduoc.com.vn/thuoc-{ID}/{slug}.aspx
"""

import time
import re
import requests
from bs4 import BeautifulSoup

from spiders.base_spider import BaseSpider
from parsers.thuocbietduoc.medicine_parser import ThuocBietDuocParser
from config.urls import SOURCES
from utils.logger import get_logger

logger = get_logger("spider.thuocbietduoc")

BASE_URL = SOURCES["thuocbietduoc"]["base_url"]

DRUG_DETAIL_PATTERN = re.compile(r"/thuoc-\d+/[^/]+\.aspx$")


class ThuocBietDuocSpider(BaseSpider):
    source_name = "thuocbietduoc"

    def __init__(self):
        super().__init__()
        self.parser = ThuocBietDuocParser()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            "Referer": BASE_URL,
        })

    def _get_soup(self, url: str) -> BeautifulSoup | None:
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            time.sleep(0.5)
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            self.logger.error(f"GET {url}: {e}")
            return None

    def _get_group_urls(self) -> list:
        """Lấy danh sách URL của 35 nhóm thuốc từ drgsearch.aspx."""
        soup = self._get_soup(f"{BASE_URL}/thuoc/drgsearch.aspx")
        if not soup:
            return []

        group_urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/nhom-thuoc-" in href:
                full_url = href if href.startswith("http") else BASE_URL + href
                if full_url not in group_urls:
                    group_urls.append(full_url)

        self.logger.info(f"Nhóm thuốc tìm được: {len(group_urls)}")
        return group_urls

    def _get_drug_urls_from_group(self, group_url: str, max_pages: int) -> list:
        """Lấy tất cả URL thuốc chi tiết từ một nhóm thuốc (có pagination)."""
        drug_urls = []

        for page in range(1, max_pages + 1):
            url = group_url if page == 1 else f"{group_url}?page={page}"
            soup = self._get_soup(url)
            if not soup:
                break

            page_drug_urls = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if DRUG_DETAIL_PATTERN.search(href):
                    full_url = href if href.startswith("http") else BASE_URL + href
                    if full_url not in drug_urls and full_url not in page_drug_urls:
                        page_drug_urls.append(full_url)

            if not page_drug_urls:
                break

            drug_urls.extend(page_drug_urls)
            self.logger.debug(f"  {group_url} page {page}: +{len(page_drug_urls)} drugs")

            # Kiểm tra có trang tiếp không
            next_page_link = soup.find("a", href=re.compile(rf"\?page={page + 1}"))
            if not next_page_link:
                break

        return drug_urls

    def get_list_urls(self, max_pages: int) -> list:
        """
        max_pages: số trang tối đa cho mỗi nhóm thuốc.
        Mỗi trang có ~20 thuốc. max_pages=10 → 200 thuốc/nhóm.
        """
        group_urls = self._get_group_urls()
        if not group_urls:
            self.logger.error("Không lấy được nhóm thuốc!")
            return []

        all_drug_urls = []
        seen = set()

        for idx, group_url in enumerate(group_urls, 1):
            group_name = group_url.split("/")[-1][:40]
            self.logger.info(f"[{idx}/{len(group_urls)}] {group_name}")

            drug_urls = self._get_drug_urls_from_group(group_url, max_pages)
            for u in drug_urls:
                if u not in seen:
                    seen.add(u)
                    all_drug_urls.append(u)

            self.logger.info(f"  → {len(drug_urls)} URLs | Tổng: {len(all_drug_urls)}")

        self.logger.info(f"Tổng URL thuốc: {len(all_drug_urls)}")
        return all_drug_urls

    def parse_item(self, url: str) -> dict | None:
        soup = self._get_soup(url)
        if not soup:
            return None
        return self.parser.parse(soup, url)
