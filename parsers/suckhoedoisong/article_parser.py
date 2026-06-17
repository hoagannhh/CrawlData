from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser
from utils.helpers import clean_text
from utils.logger import get_logger

logger = get_logger("parser.suckhoedoisong")


class SucKhoeDoiSongParser(BaseParser):
    source_name = "suckhoedoisong"

    # Thứ tự ưu tiên CSS selector cho content
    CONTENT_SELECTORS = [
        "div.detail-content",
        "div.article__body",
        "div.content-detail",
        "div#article-body",
        "div.post-content",
        "article",
    ]

    def parse(self, soup: BeautifulSoup, url: str) -> dict | None:
        try:
            record = self._base_record(url)

            # Tiêu đề
            record["name"] = (
                self._text(soup, "h1.article__title")
                or self._text(soup, "h1.detail-title")
                or self._text(soup, "h1.post-title")
                or self._text(soup, "h1")
            )

            if not record["name"]:
                return None

            # Nội dung chính
            body = None
            for selector in self.CONTENT_SELECTORS:
                body = soup.select_one(selector)
                if body:
                    break

            if body:
                for tag in body.select("script, style, .ads, .banner, figure, .related"):
                    tag.decompose()
                record["description"] = clean_text(body.get_text(separator=" "))
            else:
                # Fallback: ghép tất cả <p> đủ dài
                paragraphs = soup.select("p")
                record["description"] = " ".join(
                    clean_text(p.get_text())
                    for p in paragraphs
                    if len(p.get_text(strip=True)) > 40
                )

            if not record["description"] or len(record["description"]) < 100:
                return None

            # Parse structured sections nếu có
            for tag in soup.select("h2, h3, strong"):
                title = clean_text(tag.get_text()).lower().rstrip(":")
                content_parts = []
                for sib in tag.find_next_siblings():
                    if sib.name in ["h2", "h3"]:
                        break
                    t = clean_text(sib.get_text())
                    if t and len(t) > 20:
                        content_parts.append(t)
                content = " ".join(content_parts)

                if any(k in title for k in ["chỉ định", "công dụng", "tác dụng"]) \
                        and not record["indication"] and content:
                    record["indication"] = content
                elif any(k in title for k in ["liều dùng", "cách dùng", "liều lượng"]) \
                        and not record["dosage"] and content:
                    record["dosage"] = content
                elif any(k in title for k in ["thành phần", "hoạt chất"]) \
                        and not record["active_ingredient"] and content:
                    record["active_ingredient"] = content

            return record

        except Exception as e:
            logger.error(f"Parse lỗi [{url}]: {e}")
            return None
