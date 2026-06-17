import hashlib
import re
import unicodedata


def clean_text(text: str) -> str:
    """Chuẩn hóa text tiếng Việt cơ bản."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def make_id(text: str) -> str:
    """Tạo hash ID ngắn từ text."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def dedup_records(records: list[dict], key: str = "url") -> list[dict]:
    """Loại bỏ record trùng lặp theo URL (primary) hoặc field khác."""
    seen, result = set(), []
    for r in records:
        # Dedup theo URL trước (chính xác nhất)
        url_key = r.get("url", "")
        if url_key and url_key not in seen:
            seen.add(url_key)
            result.append(r)
        elif not url_key:
            # Fallback: dedup theo description nếu không có URL
            val = r.get(key, "") or r.get("description", "")
            h = hashlib.md5(val[:300].encode("utf-8")).hexdigest()
            if h not in seen:
                seen.add(h)
                result.append(r)
    return result


def split_sentences(text: str) -> list[str]:
    """Tách câu đơn giản cho tiếng Việt."""
    # Tách theo dấu câu kết thúc + khoảng trắng + chữ hoa hoặc số
    sentences = re.split(r"(?<=[.!?;])\s+(?=[A-ZÁÀẢÃẠĂẮẰẨẪẬÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ0-9])", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return sentences