"""
Bước 4: Pre-annotate bằng LLM qua Ollama (local, hoàn toàn miễn phí)

Không cần API key, không giới hạn số lượng, chạy offline.
Dùng Qwen2.5 7B — hỗ trợ tiếng Việt tốt, chạy được trên 8GB RAM.

Cài đặt:
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull qwen2.5:7b

Chạy:
    # Bước 1: Khởi động Ollama server (terminal riêng, để chạy nền)
    ollama serve

    # Bước 2: Chạy script
    python dataset/step4_preannotate.py

Input : data/dataset/corpus_clean.jsonl
Output: data/dataset/llm_annotations.jsonl
        data/dataset/llm_checkpoint.jsonl   ← tự resume khi chạy lại
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_HOST   = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL         = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
MAX_SENTENCES = 5_000
MAX_TOKENS    = 1_024

BASE_DIR        = Path(__file__).resolve().parent.parent
CORPUS_PATH     = BASE_DIR / "data" / "dataset" / "corpus_clean.jsonl"
OUT_PATH        = BASE_DIR / "data" / "dataset" / "llm_annotations.jsonl"
CHECKPOINT_PATH = BASE_DIR / "data" / "dataset" / "llm_checkpoint.jsonl"

# ── Entity schema ─────────────────────────────────────────────────────────────
SCHEMA_DESC = """\
FLAT ENTITIES:
  DRUG_NAME  : tên thuốc/hoạt chất  (e.g. "Paracetamol", "Amoxicillin", "Lidocaine")
  DOSE_NUM   : liều + đơn vị        (e.g. "500mg", "250ml", "400 mg", "2 IU")
  FREQ       : tần suất dùng        (e.g. "3 lần/ngày", "mỗi 8 giờ", "ngày 2 lần")
  ROUTE      : đường dùng           (e.g. "uống", "tiêm tĩnh mạch", "bôi", "nhỏ mắt")
  DISEASE    : tên bệnh/hội chứng   (e.g. "viêm phổi", "đái tháo đường", "ung thư")
  SYMPTOM    : triệu chứng          (e.g. "sốt", "ho khan", "khó thở", "đau đầu")
  BODY_PART  : bộ phận cơ thể       (e.g. "gan", "phổi", "niệu đạo", "bao quy đầu")
  PATHOGEN   : vi sinh vật          (e.g. "Helicobacter pylori", "vi khuẩn gram âm")
  LAB_VALUE  : chỉ số xét nghiệm   (e.g. "huyết áp 130/80 mmHg", "glucose 7.2 mmol/L")

NESTED ENTITIES (bao chứa flat):
  DRUG          : DRUG_NAME + DOSE_NUM          e.g. "Amoxicillin 500mg"
  DOSAGE        : DOSE_NUM + FREQ + ROUTE       e.g. "500mg uống 3 lần/ngày"
  CONDITION     : DISEASE + PATHOGEN + BODY_PART
  ADVERSE_EFFECT: SYMPTOM + BODY_PART + DISEASE
  TREATMENT     : DRUG + DOSAGE + CONDITION + DISEASE\
"""

VALID_TYPES = {
    "DRUG_NAME", "DOSE_NUM", "FREQ", "ROUTE",
    "DISEASE", "SYMPTOM", "BODY_PART", "PATHOGEN", "LAB_VALUE",
    "DRUG", "DOSAGE", "CONDITION", "ADVERSE_EFFECT", "TREATMENT",
}

SYSTEM_PROMPT = """\
Bạn là chuyên gia gán nhãn thực thể y tế (NER) tiếng Việt.
Chỉ trả về một JSON object hợp lệ, không thêm bất kỳ text nào khác.\
"""


def build_prompt(text: str) -> str:
    return f"""\
Gán nhãn tất cả thực thể y tế trong câu sau.

SCHEMA:
{SCHEMA_DESC}

Câu: "{text}"

Trả về JSON: {{"entities": [{{"start": int, "end": int, "type": str, "text": str}}, ...]}}
start/end là chỉ số ký tự 0-based (Python: text[start:end] == text của entity).
Gán nhãn cả nested entities. Nếu không có entity: {{"entities": []}}

Ví dụ câu "Uống Amoxicillin 500mg 3 lần/ngày":
{{"entities": [{{"start":5,"end":16,"type":"DRUG_NAME","text":"Amoxicillin"}},{{"start":17,"end":22,"type":"DOSE_NUM","text":"500mg"}},{{"start":23,"end":33,"type":"FREQ","text":"3 lần/ngày"}},{{"start":5,"end":22,"type":"DRUG","text":"Amoxicillin 500mg"}}]}}\
"""


# ── Ollama API (dùng stdlib, không cần cài thêm package) ─────────────────────

def ollama_chat(prompt: str, timeout: int = 120) -> str:
    """Gọi Ollama API, trả về text response."""
    payload = json.dumps({
        "model":  MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": MAX_TOKENS,
        },
        "format": "json",   # Ollama force JSON output
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["message"]["content"]


def ollama_ping() -> bool:
    """Kiểm tra Ollama server đang chạy không."""
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def ollama_has_model() -> bool:
    """Kiểm tra model đã được pull chưa."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            data = json.loads(r.read())
        names = [m["name"] for m in data.get("models", [])]
        return any(MODEL in n for n in names)
    except Exception:
        return False


# ── Entity validation ─────────────────────────────────────────────────────────

def parse_entities(raw: str | dict, sent_text: str) -> list[dict]:
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(l for l in lines if not l.startswith("```")).strip()
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, AttributeError):
            return []
    else:
        parsed = raw

    entities_raw = parsed.get("entities", []) if isinstance(parsed, dict) else []
    text_len = len(sent_text)
    seen: set[tuple] = set()
    result: list[dict] = []

    for ent in entities_raw:
        if not isinstance(ent, dict):
            continue
        etype    = ent.get("type")
        ent_text = ent.get("text", "")
        start    = ent.get("start")
        end      = ent.get("end")

        if etype not in VALID_TYPES:
            continue
        if not isinstance(ent_text, str) or not ent_text.strip():
            continue

        # Ưu tiên dùng text để tìm vị trí thực trong câu gốc.
        # Model hay đếm sai offset với tiếng Việt, nhưng text thường đúng.
        actual_start: int | None = None
        actual_end:   int | None = None

        ent_text = ent_text.strip()
        idx = sent_text.find(ent_text)
        if idx != -1:
            # Tìm được bằng text → dùng vị trí thực
            actual_start = idx
            actual_end   = idx + len(ent_text)
        elif (isinstance(start, int) and isinstance(end, int)
              and 0 <= start < end <= text_len
              and sent_text[start:end] == ent_text):
            # Offset model cho đúng → dùng luôn
            actual_start = start
            actual_end   = end
        else:
            # Cả hai đều sai → bỏ qua entity này
            continue

        key = (actual_start, actual_end, etype)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "start": actual_start,
            "end":   actual_end,
            "type":  etype,
            "text":  sent_text[actual_start:actual_end],
        })

    return sorted(result, key=lambda e: (e["start"], e["end"]))


# ── Checkpoint ────────────────────────────────────────────────────────────────

def load_checkpoint(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if "error" not in rec:
                    done.add(rec["id"])
            except Exception:
                pass
    return done


def save_checkpoint(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── Sentence selection ─────────────────────────────────────────────────────────

def load_sentences(path: Path, max_count: int) -> list[dict]:
    priority_order = ["thuocbietduoc", "vinmec", "longchau", "suckhoedoisong"]
    buckets: dict[str, list[dict]] = {src: [] for src in priority_order}

    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if not rec.get("is_medical"):
                continue
            src = rec["source"]
            if src in buckets:
                buckets[src].append(rec)

    selected: list[dict] = []
    for src in priority_order:
        remaining = max_count - len(selected)
        if remaining <= 0:
            break
        selected.extend(buckets[src][:remaining])

    return selected


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(sentences: list[dict]) -> None:
    done_ids = load_checkpoint(CHECKPOINT_PATH)
    pending  = [s for s in sentences if s["id"] not in done_ids]
    total    = len(sentences)
    already  = len(done_ids)

    if not pending:
        finalize(sentences)
        return

    t_run_start = time.monotonic()

    try:
        for i, rec in enumerate(pending, 1):
            idx = already + i
            elapsed_total = time.monotonic() - t_run_start
            speed = i / max(elapsed_total, 1)
            eta   = (len(pending) - i) / max(speed, 0.001)
            print(f"  [{idx:>5}/{total}]  ETA {int(eta//60)}m  ", end="", flush=True)

            entities: list[dict] = []
            success   = False
            error_msg = None

            for attempt in range(3):
                try:
                    raw = ollama_chat(build_prompt(rec["text"]))
                    try:
                        entities = parse_entities(json.loads(raw), rec["text"])
                    except json.JSONDecodeError:
                        entities = parse_entities(raw, rec["text"])
                    print(f"OK  {len(entities)} entity")
                    success = True
                    break

                except urllib.error.URLError:
                    print("\n  Ollama server ngắt kết nối. Kiểm tra `ollama serve`")
                    finalize(sentences)
                    sys.exit(1)

                except Exception as e:
                    if attempt < 2:
                        print(f"retry...", end=" ", flush=True)
                        time.sleep(5)
                    else:
                        error_msg = str(e)[:150]
                        print(f"LỖI: {error_msg}")

            out = {
                "id": rec["id"], "doc_id": rec["doc_id"], "source": rec["source"],
                "text": rec["text"], "llm": True, "model": MODEL,
                "entities": entities, "doc_fields": rec.get("doc_fields"),
            }
            if not success:
                out["error"] = error_msg or "unknown"

            save_checkpoint(CHECKPOINT_PATH, out)

    except KeyboardInterrupt:
        pass

    finalize(sentences)


def finalize(sentences: list[dict]) -> None:
    id_order = {r["id"]: i for i, r in enumerate(sentences)}
    results: dict[str, dict] = {}

    with open(CHECKPOINT_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                existing = results.get(rec["id"])
                if existing is None or ("error" in existing and "error" not in rec):
                    results[rec["id"]] = rec
            except Exception:
                pass

    ordered = sorted(
        (r for r in results.values() if "error" not in r),
        key=lambda r: id_order.get(r["id"], 99999),
    )

    with open(OUT_PATH, "w", encoding="utf-8") as fout:
        for rec in ordered:
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  BƯỚC 4 — LLM PRE-ANNOTATION (Ollama / local)")
    print("=" * 55)
    print(f"  Host  : {OLLAMA_HOST}")
    print(f"  Model : {MODEL}")

    # Kiểm tra Ollama server
    print("\n  Kiểm tra Ollama server...", end=" ", flush=True)
    if not ollama_ping():
        print("KHÔNG CHẠY")
        print("\n  Khởi động Ollama trước:")
        print("    ollama serve")
        print("  Hoặc để chạy nền:")
        print("    nohup ollama serve &")
        sys.exit(1)
    print("OK")

    # Kiểm tra model
    print(f"  Kiểm tra model {MODEL}...", end=" ", flush=True)
    if not ollama_has_model():
        print("CHƯA CÓ")
        print(f"\n  Tải model:")
        print(f"    ollama pull {MODEL}")
        sys.exit(1)
    print("OK")

    # Test inference
    print("  Test inference...", end=" ", flush=True)
    try:
        ollama_chat('Reply with only: {"test": true}', timeout=180)
        print("OK")
    except Exception as e:
        print(f"LỖI: {e}")
        sys.exit(1)

    print()
    sentences = load_sentences(CORPUS_PATH, MAX_SENTENCES)
    run(sentences)


if __name__ == "__main__":
    main()
