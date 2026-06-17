"""Data access for the manual label tool."""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LLM_PATH = BASE_DIR / "data" / "dataset" / "llm_annotations.jsonl"
CHECKPOINT_PATH = BASE_DIR / "data" / "dataset" / "llm_checkpoint.jsonl"
CORPUS_PATH = BASE_DIR / "data" / "dataset" / "corpus_clean.jsonl"
HUMAN_PATH = BASE_DIR / "data" / "dataset" / "human_annotations.jsonl"

PRIORITY_SOURCES = ["thuocbietduoc", "vinmec", "longchau", "suckhoedoisong"]
MAX_SENTENCES = 5_000


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_corpus_sentences(max_count: int = MAX_SENTENCES) -> list[dict]:
    """Chọn câu y tế — cùng logic với step4_preannotate."""
    buckets: dict[str, list[dict]] = {src: [] for src in PRIORITY_SOURCES}

    with open(CORPUS_PATH, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if not rec.get("is_medical"):
                continue
            src = rec.get("source")
            if src in buckets:
                buckets[src].append(rec)

    selected: list[dict] = []
    for src in PRIORITY_SOURCES:
        remaining = max_count - len(selected)
        if remaining <= 0:
            break
        selected.extend(buckets[src][:remaining])
    return selected


def load_llm_map() -> dict[str, dict]:
    """Gộp checkpoint + file output; ưu tiên bản không lỗi mới nhất."""
    merged: dict[str, dict] = {}
    for path in (CHECKPOINT_PATH, LLM_PATH):
        for rec in _read_jsonl(path):
            rid = rec.get("id")
            if not rid:
                continue
            existing = merged.get(rid)
            if existing is None or ("error" in existing and "error" not in rec):
                merged[rid] = rec
    return merged


def save_llm_record(record: dict) -> None:
    """Lưu gợi ý LLM cho 1 câu (checkpoint + cập nhật output)."""
    rid = record["id"]
    with open(CHECKPOINT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    llm_map = load_llm_map()
    llm_map[rid] = record
    order = {r["id"]: i for i, r in enumerate(load_corpus_sentences())}
    ordered = sorted(llm_map.values(), key=lambda r: order.get(r["id"], 999_999))
    good = [r for r in ordered if "error" not in r]
    _write_jsonl(LLM_PATH, good)


def load_source_records() -> list[dict]:
    """Corpus làm nguồn chính; gợi ý LLM merge theo id."""
    llm_map = load_llm_map()
    records: list[dict] = []

    for rec in load_corpus_sentences():
        llm = llm_map.get(rec["id"], {})
        records.append({
            "id": rec["id"],
            "doc_id": rec.get("doc_id"),
            "source": rec.get("source"),
            "text": rec["text"],
            "doc_fields": rec.get("doc_fields"),
            "entities": llm.get("entities", []),
            "llm_model": llm.get("model"),
            "llm_error": llm.get("error"),
        })
    return records


def load_human_map() -> dict[str, dict]:
    return {r["id"]: r for r in _read_jsonl(HUMAN_PATH)}


def save_human_record(record: dict) -> None:
    human = load_human_map()
    human[record["id"]] = record
    source_order = {r["id"]: i for i, r in enumerate(load_source_records())}
    ordered = sorted(
        human.values(),
        key=lambda r: source_order.get(r["id"], 999_999),
    )
    _write_jsonl(HUMAN_PATH, ordered)


def merge_record(source: dict, human: dict | None) -> dict:
    llm_entities = source.get("entities") or []
    if human:
        return {
            "id": source["id"],
            "doc_id": source.get("doc_id"),
            "source": source.get("source"),
            "text": source["text"],
            "llm_entities": human.get("llm_entities", llm_entities),
            "llm_model": human.get("llm_model", source.get("llm_model")),
            "entities": human.get("entities", []),
            "reviewed": human.get("reviewed", False),
            "notes": human.get("notes", ""),
        }
    return {
        "id": source["id"],
        "doc_id": source.get("doc_id"),
        "source": source.get("source"),
        "text": source["text"],
        "llm_entities": llm_entities,
        "llm_model": source.get("llm_model"),
        "entities": [],
        "reviewed": False,
        "notes": "",
    }


def list_ids(filter_mode: str = "all") -> list[str]:
    sources = load_source_records()
    human = load_human_map()
    ids: list[str] = []
    for rec in sources:
        h = human.get(rec["id"])
        reviewed = bool(h and h.get("reviewed"))
        has_llm = bool(rec.get("entities"))

        if filter_mode == "pending" and reviewed:
            continue
        if filter_mode == "reviewed" and not reviewed:
            continue
        if filter_mode == "no_llm" and has_llm:
            continue
        ids.append(rec["id"])
    return ids


def get_stats() -> dict:
    sources = load_source_records()
    human = load_human_map()
    reviewed = sum(1 for s in sources if human.get(s["id"], {}).get("reviewed"))
    with_llm = sum(1 for s in sources if s.get("entities"))
    return {
        "total": len(sources),
        "reviewed": reviewed,
        "pending": len(sources) - reviewed,
        "with_llm": with_llm,
        "no_llm": len(sources) - with_llm,
    }
