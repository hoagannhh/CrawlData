from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser
from utils.helpers import clean_text
from utils.logger import get_logger

logger = get_logger("parser.longchau")

# Mở rộng keyword để bắt nhiều biến thể tiêu đề hơn
SECTION_MAP = {
    # Active ingredient
    "thành phần":                   "active_ingredient",
    "hoạt chất":                    "active_ingredient",
    "thành phần hoạt chất":         "active_ingredient",
    "thành phần thuốc":             "active_ingredient",
    # Indication
    "chỉ định":                     "indication",
    "công dụng":                    "indication",
    "tác dụng":                     "indication",
    "điều trị":                     "indication",
    # Dosage
    "liều dùng":                    "dosage",
    "cách dùng":                    "dosage",
    "liều lượng":                   "dosage",
    "hướng dẫn sử dụng":            "dosage",
    "cách sử dụng":                 "dosage",
    # Adverse effect
    "tác dụng phụ":                 "adverse_effect",
    "tác dụng không mong muốn":     "adverse_effect",
    "tác dụng không mong muốn (adr)": "adverse_effect",
    "tác dụng bất lợi":             "adverse_effect",
    # Contraindication
    "chống chỉ định":               "contraindication",
    "không dùng thuốc khi":         "contraindication",
    "lưu ý, thận trọng":            "contraindication",
    # Drug class / description
    "dược lực học":                 "drug_class",
    "nhóm thuốc":                   "drug_class",
    "phân loại":                    "drug_class",
    # Description
    "mô tả sản phẩm":               "description",
    "thông tin sản phẩm":           "description",
    "giới thiệu":                   "description",
}


class LongChauParser(BaseParser):
    source_name = "longchau"

    def parse(self, soup: BeautifulSoup, url: str) -> dict | None:
        try:
            record = self._base_record(url)

            # Tên thuốc
            record["name"] = self._text(soup, "h1")
            if not record["name"]:
                return None

            # Parse tất cả h2, h3 (LongChau dùng h2/h3 cho các section thuốc)
            for heading in soup.find_all(["h2", "h3"]):
                title = clean_text(heading.get_text()).lower().rstrip(":")

                matched_field = None
                for keyword, field in SECTION_MAP.items():
                    if keyword in title:
                        matched_field = field
                        break

                if not matched_field:
                    continue

                # Lấy nội dung từ sibling sau heading
                content_parts = []
                for sibling in heading.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    text = clean_text(sibling.get_text(separator=" "))
                    if text and text not in ("Chưa có dữ liệu.", "Đang cập nhật..."):
                        content_parts.append(text)

                content = " ".join(content_parts).strip()

                if content and (
                    not record[matched_field]
                    or len(content) > len(record[matched_field])
                ):
                    record[matched_field] = content

            # Fallback description: meta description
            if not record["description"]:
                meta = soup.select_one("meta[name='description']")
                if meta:
                    record["description"] = clean_text(meta.get("content", ""))

            # Nếu description trống nhưng có indication → dùng indication làm description
            if not record["description"] and record["indication"]:
                record["description"] = record["indication"]

            return record

        except Exception as e:
            logger.error(f"Parse lỗi [{url}]: {e}")
            return None
