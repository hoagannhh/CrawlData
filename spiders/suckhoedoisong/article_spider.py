"""
Sức Khỏe Đời Sống Spider (Multi-category)
Strategy:
  - Dùng nhiều trang category y tế (mỗi trang ~50 bài viết mới nhất)
  - URL bài viết có dạng: /{slug}-{15+digits}.htm
  - Thu thập URL từ 13+ category → dedup → fetch từng bài
  - Không có pagination thực: mỗi category chỉ có 1 trang với bài mới nhất
    → Dùng nhiều category để đa dạng nội dung
"""

import re
import time
import requests
from bs4 import BeautifulSoup

from spiders.base_spider import BaseSpider
from parsers.suckhoedoisong.article_parser import SucKhoeDoiSongParser
from config.urls import SOURCES
from utils.logger import get_logger

logger = get_logger("spider.suckhoedoisong")

BASE_URL = SOURCES["suckhoedoisong"]["base_url"]

# Tất cả category y tế/dược học trên suckhoedoisong.vn
MEDICAL_CATEGORIES = [
    "/thuoc-va-suc-khoe.htm",
    "/duoc.htm",
    "/duoc/an-toan-dung-thuoc.htm",
    "/duoc/thuoc-moi.htm",
    "/y-hoc-360.htm",
    "/y-hoc-360/benh-thuong-gap.htm",
    "/y-hoc-360/benh-nguoi-cao-tuoi.htm",
    "/y-hoc-360/benh-phu-nu.htm",
    "/y-hoc-360/benh-nam-gioi.htm",
    "/y-hoc-360/benh-tre-em.htm",
    "/y-hoc-360/suc-khoe-tam-hon.htm",
    "/y-hoc-co-truyen.htm",
    "/y-hoc-co-truyen/cay-thuoc-quanh-ta.htm",
    "/y-hoc-co-truyen/thay-gioi-thuoc-hay.htm",
    "/y-te/blog-thay-thuoc.htm",          # chỉ lấy blog bác sĩ, bỏ /y-te.htm (tin tức rộng)
    "/dinh-duong.htm",
    "/dinh-duong/che-do-an-nguoi-benh.htm",
    "/gioi-tinh/suc-khoe-sinh-san.htm",
    "/gioi-tinh/benh-lay-truyen.htm",
]

# Từ khoá y tế tối thiểu — bài không có từ nào trong này sẽ bị loại
MEDICAL_KEYWORDS = [
    "thuốc", "bệnh", "triệu chứng", "điều trị", "bác sĩ", "y tế",
    "viêm", "đau", "sốt", "vaccine", "kháng sinh", "liều", "dược",
    "phòng bệnh", "ung thư", "tiêm", "phẫu thuật", "chẩn đoán",
    "sức khỏe", "bệnh nhân", "dị ứng", "nhiễm", "huyết áp",
]


def _is_medical_content(name: str, description: str) -> bool:
    text = (name + " " + description[:600]).lower()
    return any(kw in text for kw in MEDICAL_KEYWORDS)

# Bài viết có 15+ chữ số ở cuối trước .htm
ARTICLE_PATTERN = re.compile(r"/[^/]+-(\d{15,})\.htm$")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}


class SucKhoeDoiSongSpider(BaseSpider):
    source_name = "suckhoedoisong"

    def __init__(self):
        super().__init__()
        self.parser = SucKhoeDoiSongParser()
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get_soup(self, url: str) -> BeautifulSoup | None:
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            time.sleep(0.4)
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            self.logger.error(f"GET {url}: {e}")
            return None

    def _extract_article_urls(self, soup: BeautifulSoup) -> list:
        """Lấy URL bài viết: có 15+ chữ số ở cuối."""
        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Chuẩn hóa URL
            if href.startswith("/"):
                full_url = BASE_URL + href
            elif href.startswith(BASE_URL):
                full_url = href
            else:
                continue

            # Chỉ lấy URL có pattern bài viết
            if ARTICLE_PATTERN.search(full_url):
                urls.append(full_url)

        return list(dict.fromkeys(urls))  # dedup giữ thứ tự

    def get_list_urls(self, max_pages: int) -> list:
        """
        max_pages không dùng trực tiếp (không có pagination thực).
        Thay vào đó, crawl nhiều category = max_pages categories.
        """
        # Giới hạn số category theo max_pages (tối đa toàn bộ list)
        categories = MEDICAL_CATEGORIES[:max_pages] if max_pages < len(MEDICAL_CATEGORIES) \
            else MEDICAL_CATEGORIES

        all_urls = []
        seen = set()

        for idx, cat_path in enumerate(categories, 1):
            cat_url = BASE_URL + cat_path
            cat_name = cat_path.split("/")[-1][:40]
            self.logger.info(f"[{idx}/{len(categories)}] {cat_name}")

            soup = self._get_soup(cat_url)
            if not soup:
                continue

            article_urls = self._extract_article_urls(soup)
            new_count = 0
            for url in article_urls:
                if url not in seen:
                    seen.add(url)
                    all_urls.append(url)
                    new_count += 1

            self.logger.info(f"  +{new_count} bài mới | Tổng: {len(all_urls)}")

        self.logger.info(f"Tổng URL bài viết: {len(all_urls)}")
        return all_urls

    def parse_item(self, url: str) -> dict | None:
        soup = self._get_soup(url)
        if not soup:
            return None
        result = self.parser.parse(soup, url)
        if result and not _is_medical_content(result.get("name", ""), result.get("description", "")):
            self.logger.debug(f"Bỏ qua (không liên quan y tế): {result.get('name','')[:50]}")
            return None
        return result
