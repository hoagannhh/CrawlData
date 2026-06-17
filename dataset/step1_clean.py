"""
Bước 1: Làm sạch text và tách câu → xuất clean corpus

Input : data/pharma.db (bảng medicines)
Output: data/dataset/corpus_clean.jsonl
        data/dataset/corpus_stats.json

Mỗi dòng trong corpus_clean.jsonl:
{
  "id": "c446735120c3_12",
  "doc_id": "c446735120c3",
  "source": "thuocbietduoc",
  "sent_idx": 12,
  "text": "Paracetamol 500mg dùng để giảm đau, hạ sốt.",
  "doc_fields": {            # field nào non-empty trong record gốc
    "has_indication": true,
    "has_dosage": false,
    ...
  }
}
"""

import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DB_PATH    = BASE_DIR / "data" / "pharma.db"
OUT_DIR    = BASE_DIR / "data" / "dataset"
OUT_CORPUS = OUT_DIR / "corpus_clean.jsonl"
OUT_STATS  = OUT_DIR / "corpus_stats.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Từ khóa y tế để lọc câu có giá trị NER ──────────────────────────────────
MEDICAL_RE = re.compile(
    r"(?:thuốc|bệnh|viêm|ung thư|hội chứng|triệu chứng|chẩn đoán|điều trị|"
    r"liều|mg|mcg|ml|hoạt chất|chỉ định|tác dụng|chống chỉ định|dược|lâm sàng|"
    r"bệnh nhân|phẫu thuật|phác đồ|kháng sinh|vaccine|tiêm|uống|bôi|"
    r"đau|sốt|ho|khó thở|buồn nôn|tiêu chảy|dị ứng|nhiễm|virus|vi khuẩn|"
    r"gan|thận|tim|phổi|não|máu|xương|cơ|thần kinh|nội tiết)",
    re.IGNORECASE,
)

# Noise patterns cần xóa
HTML_TAG_RE    = re.compile(r"<[^>]+>")
MULTI_SPACE_RE = re.compile(r"[ \t]+")
MULTI_NL_RE    = re.compile(r"\n{3,}")
URL_RE         = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE       = re.compile(r"\S+@\S+\.\S+")
# Dòng chỉ chứa số, ký tự đặc biệt, không có chữ
NOISE_LINE_RE  = re.compile(r"^[\d\s\-–—•·*#/\\|(){}\[\]<>+=@%^&~`\"\']+$")

# Nguồn không cần thiết (tin tức hành chính, không phải nội dung y tế thuần)
SKIP_TITLE_RE = re.compile(
    r"(?:bắt |khởi tố|thứ trưởng|bộ y tế .(?:nhắc|yêu cầu)|"
    r"từ ngày \d|đề xuất cấm|chính thức nâng|giảm trừ mới|"
    r"vinmec phú quốc\]|ứng dụng công nghệ thông tin trong ngành y tế)",
    re.IGNORECASE,
)


# ── Text cleaning ────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Làm sạch một đoạn text."""
    text = unicodedata.normalize("NFC", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = URL_RE.sub("", text)
    text = EMAIL_RE.sub("", text)
    # Xóa ký tự điều khiển (trừ newline)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch == "\n")
    text = MULTI_SPACE_RE.sub(" ", text)
    text = MULTI_NL_RE.sub("\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """
    Tách câu tiếng Việt từ đoạn văn.
    Ưu tiên tách theo:
      1. Dấu câu kết thúc (.!?) + khoảng trắng
      2. Bullet/list markers (-, •, *, số thứ tự)
      3. Dòng trống
    """
    # Chuẩn hóa bullet lists thành dấu xuống dòng
    text = re.sub(r"\n\s*[-–•·*]\s+", "\n", text)
    text = re.sub(r"\n\s*\d+[.)]\s+", "\n", text)

    # Tách theo dấu câu kết thúc
    parts = re.split(
        r"(?<=[.!?;])\s+(?=[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ\d\"\'(])"
        r"|(?<=\n)",
        text,
    )

    sentences = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Nếu đoạn còn dài (>300 ký tự) thì cố tách thêm theo dòng
        if len(part) > 300:
            sub = [s.strip() for s in part.split("\n") if s.strip()]
            sentences.extend(sub)
        else:
            sentences.append(part)

    return sentences


def is_valid_sentence(sent: str) -> bool:
    """Kiểm tra câu có đáng giữ lại không."""
    if len(sent) < 20:
        return False
    if len(sent) > 600:          # quá dài, thường là đoạn chưa tách được
        return False
    if NOISE_LINE_RE.match(sent):
        return False
    # Phải có ít nhất 3 chữ cái
    if len(re.findall(r"[a-zA-ZÀ-ỹ]", sent)) < 10:
        return False
    return True


def is_medical_sentence(sent: str) -> bool:
    return bool(MEDICAL_RE.search(sent))


def is_useful_doc(name: str, source: str) -> bool:
    """Lọc bỏ tài liệu không phải nội dung y tế (tin tức hành chính...)."""
    if SKIP_TITLE_RE.search(name or ""):
        return False
    return True


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, source, name, description, "
        "active_ingredient, indication, dosage, adverse_effect, contraindication "
        "FROM medicines WHERE description IS NOT NULL AND description != ''"
    )
    rows = cur.fetchall()
    conn.close()

    stats = {
        "total_docs": len(rows),
        "skipped_docs": 0,
        "total_sentences": 0,
        "medical_sentences": 0,
        "by_source": {},
    }

    written = 0
    with open(OUT_CORPUS, "w", encoding="utf-8") as fout:
        for row in rows:
            doc_id  = row["id"]
            source  = row["source"]
            name    = row["name"] or ""

            # Lọc tài liệu rác
            if not is_useful_doc(name, source):
                stats["skipped_docs"] += 1
                continue

            if source not in stats["by_source"]:
                stats["by_source"][source] = {
                    "docs": 0, "sentences": 0, "medical_sentences": 0
                }

            text     = clean_text(row["description"])
            sentences = split_sentences(text)

            doc_fields = {
                "has_active_ingredient": bool(row["active_ingredient"]),
                "has_indication":        bool(row["indication"]),
                "has_dosage":            bool(row["dosage"]),
                "has_adverse_effect":    bool(row["adverse_effect"]),
                "has_contraindication":  bool(row["contraindication"]),
            }

            stats["by_source"][source]["docs"] += 1
            kept = 0

            for idx, sent in enumerate(sentences):
                if not is_valid_sentence(sent):
                    continue

                stats["total_sentences"] += 1
                stats["by_source"][source]["sentences"] += 1

                is_med = is_medical_sentence(sent)
                if is_med:
                    stats["medical_sentences"] += 1
                    stats["by_source"][source]["medical_sentences"] += 1

                record = {
                    "id":         f"{doc_id}_{idx:04d}",
                    "doc_id":     doc_id,
                    "source":     source,
                    "sent_idx":   idx,
                    "text":       sent,
                    "is_medical": is_med,
                    "doc_fields": doc_fields,
                }
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
                kept += 1

    # Lưu stats
    with open(OUT_STATS, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # In báo cáo
    print("=" * 55)
    print("  KẾT QUẢ BƯỚC 1 — LÀM SẠCH CORPUS")
    print("=" * 55)
    print(f"  Tài liệu đầu vào   : {stats['total_docs']:,}")
    print(f"  Tài liệu bỏ qua    : {stats['skipped_docs']:,}")
    print(f"  Câu tổng           : {stats['total_sentences']:,}")
    print(f"  Câu y tế           : {stats['medical_sentences']:,}")
    print(f"  Tỉ lệ câu y tế     : {stats['medical_sentences']/max(stats['total_sentences'],1)*100:.1f}%")
    print()
    print(f"  {'Nguồn':<20} {'Docs':>6} {'Câu':>8} {'Câu y tế':>10} {'Tỉ lệ':>7}")
    print("  " + "-" * 55)
    for src, s in stats["by_source"].items():
        pct = s["medical_sentences"] / max(s["sentences"], 1) * 100
        print(f"  {src:<20} {s['docs']:>6,} {s['sentences']:>8,} {s['medical_sentences']:>10,} {pct:>6.0f}%")
    print()
    print(f"  Output: {OUT_CORPUS}")
    print(f"  Stats : {OUT_STATS}")


if __name__ == "__main__":
    main()
