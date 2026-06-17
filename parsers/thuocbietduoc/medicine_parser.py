from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser
from utils.helpers import clean_text
from utils.logger import get_logger

logger = get_logger("parser.thuocbietduoc")

SECTION_MAP = {
    "thành phần":               "active_ingredient",
    "hoạt chất":                "active_ingredient",
    "dạng bào chế":             "drug_class",
    "nhóm dược lý":             "drug_class",
    "chỉ định":                 "indication",
    "liều dùng":                "dosage",
    "cách dùng":                "dosage",
    "tác dụng không mong muốn": "adverse_effect",
    "tác dụng phụ":             "adverse_effect",
    "chống chỉ định":           "contraindication",
    "mô tả":                    "description",
    "dược động học":            "description",
}


class ThuocBietDuocParser(BaseParser):
    source_name = "thuocbietduoc"

    def parse(self, soup: BeautifulSoup, url: str) -> dict | None:
        try:
            record = self._base_record(url)

            # Tên thuốc — thuocbietduoc dùng h1.drug-name hoặc h1.title
            record["name"] = self._text(soup, "h1.drug-name") or \
                              self._text(soup, "h1.title") or \
                              self._text(soup, "h1")

            if not record["name"]:
                return None

            # Parse nội dung theo tab hoặc section
            content_area = soup.select_one("div.drug-info, div.drug-detail, div#content-drug, article")
            if not content_area:
                content_area = soup

            for tag in content_area.find_all(["h2", "h3", "strong", "b"]):
                title = clean_text(tag.get_text()).lower().rstrip(":")
                content_parts = []
                for sibling in tag.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    text = clean_text(sibling.get_text())
                    if text:
                        content_parts.append(text)
                content = " ".join(content_parts)

                for keyword, field in SECTION_MAP.items():
                    if keyword in title and content and not record[field]:
                        record[field] = content
                        break

            # Tổng hợp description từ các field có nội dung
            # (ThuocBietDuoc không có section "Mô tả" riêng)
            if not record["description"]:
                parts = []
                for field in ("indication", "dosage", "adverse_effect",
                              "contraindication", "active_ingredient"):
                    val = record.get(field, "").strip()
                    if val:
                        parts.append(val)
                record["description"] = " ".join(parts)

            return record if record["name"] else None

        except Exception as e:
            logger.error(f"Parse lỗi [{url}]: {e}")
            return None