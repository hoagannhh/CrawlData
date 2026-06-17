"""
Vinmec Spider (Sitemap-based)
Strategy:
  - Vinmec dùng React nhưng các trang bai-viet có SSR → plain requests hoạt động
  - Dùng sitemap XML (posts-vi-*.xml) để lấy URL bài viết y tế
  - Lọc các bài liên quan đến bệnh lý, thuốc, triệu chứng, điều trị
  - Parse #main-article div (đã xác nhận hoạt động)
"""

import time
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

from spiders.base_spider import BaseSpider
from parsers.vinmec.article_parser import VinmecParser
from config.urls import SOURCES
from utils.logger import get_logger

logger = get_logger("spider.vinmec")

BASE_URL = SOURCES["vinmec"]["base_url"]
SITEMAP_BASE = "https://www.vinmec.com/sitemap/posts-vi-{n}.xml"
SITEMAP_TOTAL = 86

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Từ khoá lọc bài y tế (chỉ lấy bài có nội dung liên quan)
MEDICAL_KEYWORDS = [
    "benh", "thuoc", "trieu-chung", "dieu-tri", "phac-do", "chan-doan",
    "ung-thu", "viem", "nhiem", "suc-khoe", "y-te", "bai-viet",
    "phau-thuat", "noi-soi", "siet-mau", "mien-dich", "duoc",
]


def _is_medical_url(url: str) -> bool:
    url_lower = url.lower()
    return any(kw in url_lower for kw in MEDICAL_KEYWORDS)


class VinmecSpider(BaseSpider):
    source_name = "vinmec"

    def __init__(self):
        super().__init__()
        self.parser = VinmecParser()
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get_urls_from_sitemap(self, sitemap_n: int) -> list:
        """Lấy tất cả URL từ một file sitemap."""
        url = SITEMAP_BASE.format(n=sitemap_n)
        try:
            r = self.session.get(url, timeout=20)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = [loc.text for loc in root.findall(".//sm:loc", ns) if loc.text]
            return urls
        except Exception as e:
            self.logger.error(f"Sitemap {url}: {e}")
            return []

    def get_list_urls(self, max_pages: int) -> list:
        """
        max_pages = số sitemap file cần đọc (1 file = 1000 URLs).
        Mỗi sitemap có 1000 URLs → max_pages=2 cho 2000 URLs, lọc còn ~1000 URLs y tế.
        """
        all_urls = []
        seen = set()

        # Đọc max_pages sitemap files
        sitemaps_to_read = min(max_pages, SITEMAP_TOTAL)
        self.logger.info(f"Đọc {sitemaps_to_read} sitemap files...")

        for n in range(1, sitemaps_to_read + 1):
            urls = self._get_urls_from_sitemap(n)
            self.logger.info(f"  Sitemap {n}: {len(urls)} URLs")

            for url in urls:
                if url not in seen and _is_medical_url(url):
                    seen.add(url)
                    all_urls.append(url)

            time.sleep(0.3)

        self.logger.info(f"Tổng URLs y tế từ sitemap: {len(all_urls)}")
        return all_urls

    def parse_item(self, url: str) -> dict | None:
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            time.sleep(0.5)
            soup = BeautifulSoup(r.text, "lxml")
            return self.parser.parse(soup, url)
        except Exception as e:
            self.logger.error(f"Lỗi fetch [{url}]: {e}")
            return None
