from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from utils.helpers import clean_text


class BaseParser(ABC):
    source_name: str = "base"

    @abstractmethod
    def parse(self, soup: BeautifulSoup, url: str) -> dict | None:
        """Parse BeautifulSoup thành dict chuẩn."""
        pass

    def _text(self, soup: BeautifulSoup, selector: str, default: str = "") -> str:
        """Helper: lấy text từ selector, trả về default nếu không tìm thấy."""
        tag = soup.select_one(selector)
        return clean_text(tag.get_text()) if tag else default

    def _texts(self, soup: BeautifulSoup, selector: str) -> list[str]:
        """Helper: lấy list text từ selector."""
        return [clean_text(t.get_text()) for t in soup.select(selector) if t.get_text(strip=True)]

    def _base_record(self, url: str) -> dict:
        """Template record chuẩn dùng chung."""
        return {
            "source":             self.source_name,
            "url":                url,
            "name":               "",
            "active_ingredient":  "",   # hoạt chất
            "drug_class":         "",   # nhóm thuốc
            "indication":         "",   # chỉ định
            "dosage":             "",   # liều dùng
            "adverse_effect":     "",   # tác dụng phụ
            "contraindication":   "",   # chống chỉ định
            "description":        "",   # mô tả chung / nội dung bài viết
        }