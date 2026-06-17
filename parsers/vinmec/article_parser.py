import json
import re
from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser
from utils.helpers import clean_text
from utils.logger import get_logger

logger = get_logger("parser.vinmec")


class VinmecParser(BaseParser):
    source_name = "vinmec"

    def parse(self, soup: BeautifulSoup, url: str) -> dict | None:
        try:
            record = self._base_record(url)

            # Tiêu đề từ h1 hoặc JSON-LD
            record["name"] = self._text(soup, "h1") or self._get_jsonld_headline(soup)

            if not record["name"]:
                return None

            # Nội dung chính từ #main-article (đã xác nhận hoạt động với requests)
            main_article = soup.find(id="main-article")
            if main_article:
                for tag in main_article.select("script, style, .ads, nav, .toc-container"):
                    tag.decompose()
                raw = clean_text(main_article.get_text(separator=" "))
                # Loại bỏ noise đầu text: "☰ Mục lục ... <tên bài>"
                raw = re.sub(r"^[☰\s]*Mục lục\s*", "", raw)
                # Loại bỏ câu giới thiệu tác giả thường ở đầu
                raw = re.sub(r"^Bài viết được tư vấn chuyên môn bởi[^.]+\.\s*", "", raw)
                record["description"] = raw.strip()
            else:
                # Fallback: các div nội dung khác
                body = soup.select_one(
                    "div.body-content, div.article-content, "
                    "div.post-content, article.detail-content"
                )
                if body:
                    for tag in body.select("script, style, .ads, .related, nav"):
                        tag.decompose()
                    record["description"] = clean_text(body.get_text(separator=" "))
                else:
                    # Fallback cuối: JSON-LD description
                    record["description"] = self._get_jsonld_description(soup)

            if not record["description"] or len(record["description"]) < 100:
                return None

            # Parse structured sections từ headings
            for tag in soup.select("h2, h3"):
                title = clean_text(tag.get_text()).lower()
                content_parts = []
                for sib in tag.find_next_siblings():
                    if sib.name in ["h2", "h3"]:
                        break
                    t = clean_text(sib.get_text())
                    if t:
                        content_parts.append(t)
                content = " ".join(content_parts)

                if any(k in title for k in ["triệu chứng", "biểu hiện", "chỉ định"]) \
                        and not record["indication"]:
                    record["indication"] = content
                elif any(k in title for k in ["điều trị", "phác đồ", "cách dùng", "liều dùng"]) \
                        and not record["dosage"]:
                    record["dosage"] = content
                elif any(k in title for k in ["thành phần", "hoạt chất"]) \
                        and not record["active_ingredient"]:
                    record["active_ingredient"] = content
                elif any(k in title for k in ["chống chỉ định"]) \
                        and not record["contraindication"]:
                    record["contraindication"] = content

            return record

        except Exception as e:
            logger.error(f"Parse lỗi [{url}]: {e}")
            return None

    @staticmethod
    def _get_jsonld_headline(soup: BeautifulSoup) -> str:
        for sc in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(sc.string or "{}")
                graph = data.get("@graph", [data])
                for item in graph:
                    if item.get("headline"):
                        return clean_text(item["headline"])
            except Exception:
                pass
        return ""

    @staticmethod
    def _get_jsonld_description(soup: BeautifulSoup) -> str:
        for sc in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(sc.string or "{}")
                graph = data.get("@graph", [data])
                for item in graph:
                    desc = item.get("description", "")
                    if desc and len(desc) > 100:
                        return clean_text(desc)
            except Exception:
                pass
        return ""
