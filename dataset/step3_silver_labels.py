"""
Bước 3: Tạo silver labels từ structured fields của thuocbietduoc

Logic:
  - active_ingredient → tìm span DRUG_NAME trong description/indication
  - indication        → câu thuộc context DISEASE/CONDITION
  - dosage            → câu thuộc context DOSAGE, extract DOSE_NUM + FREQ + ROUTE
  - adverse_effect    → câu thuộc context ADVERSE_EFFECT + SYMPTOM
  - contraindication  → câu thuộc context CONDITION/DISEASE (dạng chống chỉ định)

Input : data/pharma.db  +  data/dataset/corpus_clean.jsonl
Output: data/dataset/silver_labels.jsonl

Mỗi dòng:
{
  "id": "abc123_0005",
  "text": "Amoxicillin 500mg uống 3 lần/ngày điều trị viêm phổi.",
  "source": "thuocbietduoc",
  "silver": true,
  "entities": [
    {"start": 0,  "end": 10, "type": "DRUG_NAME", "text": "Amoxicillin"},
    {"start": 11, "end": 16, "type": "DOSE_NUM",  "text": "500mg"},
    {"start": 0,  "end": 16, "type": "DRUG",      "text": "Amoxicillin 500mg"},
    ...
  ]
}
"""

import json
import re
import sqlite3
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = BASE_DIR / "data" / "pharma.db"
CORPUS_PATH = BASE_DIR / "data" / "dataset" / "corpus_clean.jsonl"
OUT_PATH    = BASE_DIR / "data" / "dataset" / "silver_labels.jsonl"

# ── Regex patterns cho từng entity type ─────────────────────────────────────

DOSE_NUM_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ml|mL|L|IU|UI|UI/ml|%|mmol|μmol|nmol|mEq|mOsm)"
    r"(?:/\s*(?:kg|ngày|lần|liều))?",
    re.IGNORECASE,
)

FREQ_RE = re.compile(
    r"\b(?:\d+\s*lần\s*/\s*(?:ngày|tuần|tháng|giờ)|"
    r"mỗi\s+\d+\s*giờ|"
    r"(?:ngày|tuần|tháng)\s+\d+\s*lần|"
    r"(?:sáng|trưa|tối|chiều)(?:\s+và\s+(?:sáng|trưa|tối|chiều))*|"
    r"\d+\s*lần\s*mỗi\s+(?:ngày|tuần)|"
    r"mỗi\s+(?:ngày|tuần|tháng))",
    re.IGNORECASE,
)

ROUTE_RE = re.compile(
    r"\b(?:uống|tiêm\s+(?:tĩnh\s+mạch|bắp|dưới\s+da|nội\s+tủy)|"
    r"bôi(?:\s+ngoài\s+da)?|nhỏ\s+(?:mắt|tai|mũi)|"
    r"đặt\s+(?:hậu\s+môn|âm\s+đạo)|xịt|hít|ngậm|đường\s+miệng|"
    r"truyền\s+(?:tĩnh\s+mạch)?|tiêm\s+trực\s+tiếp)",
    re.IGNORECASE,
)

DISEASE_KEYWORDS = re.compile(
    r"(?:viêm\s+\w+(?:\s+\w+)?|ung\s+thư\s+\w+|"
    r"hội\s+chứng\s+\w+(?:\s+\w+)?|"
    r"bệnh\s+\w+(?:\s+\w+)?|"
    r"nhiễm\s+(?:khuẩn|trùng|virus|nấm)(?:\s+\w+)?|"
    r"suy\s+(?:gan|thận|tim|hô\s+hấp)|"
    r"đái\s+tháo\s+đường|tăng\s+huyết\s+áp|nhồi\s+máu\s+cơ\s+tim|"
    r"loét\s+(?:dạ\s+dày|tá\s+tràng)|xuất\s+huyết\s+\w*)",
    re.IGNORECASE,
)

SYMPTOM_KEYWORDS = re.compile(
    r"\b(?:đau\s+\w+|sốt\b|ho\s+khan|ho\s+có\s+đờm|khó\s+thở|buồn\s+nôn|"
    r"nôn\s+mửa|tiêu\s+chảy|táo\s+bón|chóng\s+mặt|mệt\s+mỏi|phát\s+ban|"
    r"ngứa\s+\w+|phù\s+nề|tê\s+liệt|co\s+giật|dị\s+ứng|sốc\s+phản\s+vệ|"
    r"nhức\s+đầu|hoa\s+mắt|mất\s+ngủ|run\s+tay|đỏ\s+da|nổi\s+mề\s+đay)",
    re.IGNORECASE,
)

PATHOGEN_RE = re.compile(
    # Tên latin khoa học (>=6 ký tự, kết thúc hậu tố vi sinh vật)
    r"\b[A-Z][a-z]{4,}(?:coccus|bacillus|ella|monas|bacter|avirus|phage|fungus)\b"
    # Cụm từ tiếng Việt mô tả mầm bệnh
    r"|(?:vi\s+khuẩn|vi\s+rút|virus|nấm|ký\s+sinh\s+trùng|giun|sán)"
    r"\s+[A-Za-zÀ-ỹ]+(?:\s+[A-Za-zÀ-ỹ]+)?",
    re.IGNORECASE,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_spans(pattern: re.Pattern, text: str, entity_type: str) -> list[dict]:
    spans = []
    for m in pattern.finditer(text):
        spans.append({
            "start": m.start(),
            "end":   m.end(),
            "type":  entity_type,
            "text":  m.group(),
        })
    return spans


def find_drug_name_spans(drug_names: list[str], text: str) -> list[dict]:
    """Tìm tên thuốc/hoạt chất trong câu (exact match, case-insensitive)."""
    spans = []
    for name in drug_names:
        name_clean = name.strip()
        if not name_clean or len(name_clean) < 3:
            continue
        pattern = re.compile(re.escape(name_clean), re.IGNORECASE)
        for m in pattern.finditer(text):
            spans.append({
                "start": m.start(),
                "end":   m.end(),
                "type":  "DRUG_NAME",
                "text":  m.group(),
            })
    return spans


def build_nested_drug_spans(flat_spans: list[dict], text: str) -> list[dict]:
    """
    Từ DRUG_NAME + DOSE_NUM liền kề → tạo DRUG span bao phủ cả hai.
    "Amoxicillin 500mg" = DRUG(DRUG_NAME + DOSE_NUM)
    """
    drug_names = [s for s in flat_spans if s["type"] == "DRUG_NAME"]
    dose_nums  = [s for s in flat_spans if s["type"] == "DOSE_NUM"]
    nested = []
    for dn in drug_names:
        # Tìm DOSE_NUM ngay sau DRUG_NAME (trong vòng 5 ký tự)
        for dose in dose_nums:
            gap = dose["start"] - dn["end"]
            if 0 <= gap <= 5:
                nested.append({
                    "start": dn["start"],
                    "end":   dose["end"],
                    "type":  "DRUG",
                    "text":  text[dn["start"]:dose["end"]],
                })
                break
    return nested


def build_dosage_spans(flat_spans: list[dict], text: str) -> list[dict]:
    """
    DOSE_NUM + ROUTE/FREQ liền kề → DOSAGE span
    """
    dose_nums = [s for s in flat_spans if s["type"] == "DOSE_NUM"]
    routes    = [s for s in flat_spans if s["type"] == "ROUTE"]
    freqs     = [s for s in flat_spans if s["type"] == "FREQ"]
    nested = []
    for dose in dose_nums:
        candidates = [s for s in (routes + freqs) if s["start"] >= dose["end"]]
        if not candidates:
            continue
        closest = min(candidates, key=lambda s: s["start"])
        if closest["start"] - dose["end"] <= 10:
            nested.append({
                "start": dose["start"],
                "end":   closest["end"],
                "type":  "DOSAGE",
                "text":  text[dose["start"]:closest["end"]],
            })
    return nested


def annotate_sentence(text: str, drug_names: list[str]) -> list[dict]:
    """Trả về list entity spans (flat + nested) cho một câu."""
    flat = []
    flat += find_drug_name_spans(drug_names, text)
    flat += find_spans(DOSE_NUM_RE,      text, "DOSE_NUM")
    flat += find_spans(FREQ_RE,          text, "FREQ")
    flat += find_spans(ROUTE_RE,         text, "ROUTE")
    flat += find_spans(DISEASE_KEYWORDS, text, "DISEASE")
    flat += find_spans(SYMPTOM_KEYWORDS, text, "SYMPTOM")
    flat += find_spans(PATHOGEN_RE,      text, "PATHOGEN")

    nested = []
    nested += build_nested_drug_spans(flat, text)
    nested += build_dosage_spans(flat, text)

    # Loại bỏ span trùng lặp (cùng start+end+type)
    all_spans = flat + nested
    seen = set()
    deduped = []
    for s in all_spans:
        key = (s["start"], s["end"], s["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return sorted(deduped, key=lambda s: (s["start"], s["end"]))


def parse_drug_names(active_ingredient_text: str) -> list[str]:
    """
    Từ field active_ingredient, trích xuất tên hoạt chất.
    Bỏ các giá trị như "1 hoạt chất", "2 hoạt chất" vì không có tên thực.
    """
    if not active_ingredient_text:
        return []
    text = active_ingredient_text.strip()
    # Lọc giá trị không có tên thực
    if re.match(r"^\d+\s+hoạt\s+chất$", text, re.IGNORECASE):
        return []
    # Tách theo dấu phẩy, dấu chấm phẩy, xuống dòng
    parts = re.split(r"[,;\n/]", text)
    names = []
    for p in parts:
        p = p.strip()
        # Lấy chữ đầu mỗi phần (trước dấu ngoặc hoặc số)
        m = re.match(r"^([A-Za-zÀ-ỹ\s\-]+)", p)
        if m:
            name = m.group(1).strip()
            if len(name) >= 3:
                names.append(name)
    return names


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load DB để lấy active_ingredient per doc
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, active_ingredient FROM medicines WHERE source='thuocbietduoc'"
    )
    drug_map: dict[str, list[str]] = {}
    for row in cur.fetchall():
        names = parse_drug_names(row["active_ingredient"] or "")
        if names:
            drug_map[row["id"]] = names
    conn.close()

    stats = {"total": 0, "annotated": 0, "has_entities": 0, "skipped": 0}
    entity_type_counts: dict[str, int] = {}

    with (
        open(CORPUS_PATH, encoding="utf-8") as fin,
        open(OUT_PATH, "w", encoding="utf-8") as fout,
    ):
        for line in fin:
            rec = json.loads(line)
            stats["total"] += 1

            # Chỉ xử lý thuocbietduoc
            if rec["source"] != "thuocbietduoc":
                stats["skipped"] += 1
                continue

            drug_names = drug_map.get(rec["doc_id"], [])
            entities   = annotate_sentence(rec["text"], drug_names)

            if entities:
                stats["has_entities"] += 1
                for e in entities:
                    entity_type_counts[e["type"]] = entity_type_counts.get(e["type"], 0) + 1

            out = {
                "id":       rec["id"],
                "doc_id":   rec["doc_id"],
                "source":   rec["source"],
                "text":     rec["text"],
                "silver":   True,
                "entities": entities,
                "doc_fields": rec["doc_fields"],
            }
            fout.write(json.dumps(out, ensure_ascii=False) + "\n")
            stats["annotated"] += 1

    print("=" * 55)
    print("  KẾT QUẢ BƯỚC 3 — SILVER LABELS")
    print("=" * 55)
    print(f"  Câu đầu vào (toàn corpus) : {stats['total']:,}")
    print(f"  Câu thuocbietduoc         : {stats['annotated']:,}")
    print(f"  Câu có ít nhất 1 entity   : {stats['has_entities']:,} "
          f"({stats['has_entities']/max(stats['annotated'],1)*100:.1f}%)")
    print()
    print(f"  {'Entity type':<20} {'Count':>8}")
    print("  " + "-" * 30)
    for etype, cnt in sorted(entity_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {etype:<20} {cnt:>8,}")
    print()
    print(f"  Output: {OUT_PATH}")


if __name__ == "__main__":
    main()