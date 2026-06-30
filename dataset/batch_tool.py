"""
Lấy batch câu để gán nhãn thủ công và nhập lại kết quả.

Lấy batch tiếp theo:
    python3 dataset/batch_tool.py get
    python3 dataset/batch_tool.py get --size 50
    python3 dataset/batch_tool.py get --size 100 --source vinmec

Xem tiến độ:
    python3 dataset/batch_tool.py status

Nhập batch đã gán nhãn:
    python3 dataset/batch_tool.py import data/dataset/batches/batch_001.jsonl

Checkpoint lưu tại: data/dataset/manual_annotations.jsonl
Batch files lưu tại: data/dataset/batches/
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent
CORPUS      = BASE_DIR / "data" / "dataset" / "corpus_clean.jsonl"
CHECKPOINT  = BASE_DIR / "data" / "dataset" / "manual_annotations.jsonl"
BATCH_DIR   = BASE_DIR / "data" / "dataset" / "batches"

VALID_TYPES = {
    "DRUG_NAME","DOSE_NUM","FREQ","ROUTE","DISEASE","SYMPTOM",
    "BODY_PART","PATHOGEN","LAB_VALUE",
    "DRUG","DOSAGE","CONDITION","ADVERSE_EFFECT","TREATMENT",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_corpus() -> list[dict]:
    rows = []
    with open(CORPUS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_done_ids() -> set[str]:
    if not CHECKPOINT.exists():
        return set()
    ids = set()
    with open(CHECKPOINT, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                ids.add(r["id"])
    return ids


def append_annotations(records: list[dict]) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def next_batch_num() -> int:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(BATCH_DIR.glob("batch_*.jsonl"))
    # chỉ đếm file chưa _done
    pending = [f for f in existing if not f.stem.endswith("_done")]
    done    = [f for f in existing if f.stem.endswith("_done")]
    num = len(done) + len(pending) + 1
    return num


def validate_entity(e: dict, text: str) -> bool:
    s, en, t = e.get("start"), e.get("end"), e.get("type", "")
    et = e.get("text", "")
    return (
        isinstance(s, int) and isinstance(en, int)
        and 0 <= s < en <= len(text)
        and text[s:en] == et
        and t in VALID_TYPES
    )


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_status() -> None:
    corpus   = load_corpus()
    done_ids = load_done_ids()
    total    = len(corpus)
    done     = len(done_ids)
    pct      = done / max(total, 1) * 100

    src_total: dict[str, int] = {}
    src_done:  dict[str, int] = {}
    for r in corpus:
        src = r.get("source", "")
        src_total[src] = src_total.get(src, 0) + 1
        if r["id"] in done_ids:
            src_done[src] = src_done.get(src, 0) + 1

    print("=" * 52)
    print("  TIẾN ĐỘ GÁN NHÃN THỦ CÔNG")
    print("=" * 52)
    print(f"  Tổng      : {total:,} câu")
    print(f"  Đã xong   : {done:,} câu  ({pct:.1f}%)")
    print(f"  Còn lại   : {total - done:,} câu")
    print()
    print("  Theo nguồn:")
    for src, tot in sorted(src_total.items()):
        d = src_done.get(src, 0)
        print(f"    {src:<22} {d:>6,} / {tot:>6,}  ({d/tot*100:.0f}%)")

    batches = sorted(BATCH_DIR.glob("batch_*.jsonl")) if BATCH_DIR.exists() else []
    if batches:
        print(f"\n  Batch files: {len(batches)} file trong {BATCH_DIR}")


def cmd_get(size: int = 100, source: str = "") -> None:
    corpus   = load_corpus()
    done_ids = load_done_ids()

    pending = []
    for r in corpus:
        if r["id"] in done_ids:
            continue
        if source and r.get("source") != source:
            continue
        pending.append(r)
        if len(pending) >= size:
            break

    if not pending:
        print("[OK] Khong con cau nao chua gan nhan" +
              (f" (nguon: {source})" if source else "") + ".")
        return

    num      = next_batch_num()
    out_path = BATCH_DIR / f"batch_{num:03d}.jsonl"
    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in pending:
        rows.append({
            "id":         r["id"],
            "doc_id":     r.get("doc_id"),
            "source":     r.get("source", ""),
            "sent_idx":   r.get("sent_idx"),
            "text":       r["text"],
            "is_medical": r.get("is_medical", False),
            "doc_fields": r.get("doc_fields"),
            "entities":   [],
        })

    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[OK] Da xuat {len(rows):,} cau -> {out_path}")
    print()
    print("  Dien entities theo dang:")
    print('  {"start":0,"end":11,"type":"DRUG_NAME","text":"Amoxicillin"}')
    print()
    print("  Khi xong, chay:")
    print(f"  python3 dataset/batch_tool.py import {out_path}")


def cmd_import(path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        print(f"[ERROR] Khong tim thay file: {path}")
        sys.exit(1)

    corpus   = load_corpus()
    cmap     = {r["id"]: r for r in corpus}
    done_ids = load_done_ids()

    records  = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  [ERROR] Dong {lineno}: JSON loi - {exc}")
                continue

            rid = r.get("id", "")
            if rid in done_ids:
                print(f"  [SKIP] {rid}: da co trong checkpoint, bo qua")
                continue

            orig = cmap.get(rid)
            if not orig:
                print(f"  [ERROR] {rid}: khong tim thay trong corpus, bo qua")
                continue

            text      = orig["text"]
            raw_ents  = r.get("entities", [])
            valid     = [e for e in raw_ents if validate_entity(e, text)]
            bad       = len(raw_ents) - len(valid)
            if bad:
                print(f"  [WARN] {rid}: {bad} entity loi offset bi loai")

            records.append({
                "id":            rid,
                "doc_id":        orig.get("doc_id"),
                "source":        orig.get("source"),
                "text":          text,
                "entities":      valid,
                "annotated_at":  datetime.now(timezone.utc).isoformat(),
            })

    if not records:
        print("[ERROR] Khong co dong hop le nao de import.")
        sys.exit(1)

    append_annotations(records)

    done_path = path.with_stem(path.stem + "_done")
    path.rename(done_path)
    print(f"[OK] Da import {len(records):,} cau -> {CHECKPOINT}")
    print(f"[OK] Doi ten batch -> {done_path.name}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("status", "s"):
        cmd_status()
        return

    if args[0] == "get":
        size   = 100
        source = ""
        i = 1
        while i < len(args):
            if args[i] == "--size" and i + 1 < len(args):
                size = int(args[i + 1]); i += 2
            elif args[i] == "--source" and i + 1 < len(args):
                source = args[i + 1]; i += 2
            else:
                i += 1
        cmd_get(size, source)
        return

    if args[0] == "import" and len(args) >= 2:
        cmd_import(args[1])
        return

    print(__doc__)


if __name__ == "__main__":
    main()
