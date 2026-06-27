"""
Tool kiểm tra + chỉnh sửa nhãn dataset.
SQLite backend → nhiều người dùng cùng lúc không xung đột.

Chạy:
    python3 dataset/review_tool.py [--user TenNguoi] [--port 8766]
Mở trình duyệt: http://localhost:8766
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR    = Path(__file__).resolve().parent.parent
ANN_PATH    = BASE_DIR / "data" / "dataset" / "corpus_annotations.jsonl"
DB_PATH     = BASE_DIR / "data" / "dataset" / "review_results.db"

# Đọc --user và --port từ CLI
_USERNAME = "anonymous"
_PORT     = 8766
for i, arg in enumerate(sys.argv[1:]):
    if arg == "--user" and i + 2 < len(sys.argv):
        _USERNAME = sys.argv[i + 2]
    if arg == "--port" and i + 2 < len(sys.argv):
        _PORT = int(sys.argv[i + 2])

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "review_tool" / "templates"),
)

PALETTE: dict[str, str] = {
    "DRUG_NAME":      "#4e9af1",
    "DOSE_NUM":       "#f4a261",
    "FREQ":           "#a8d8ea",
    "ROUTE":          "#b5ead7",
    "DISEASE":        "#ff6b6b",
    "SYMPTOM":        "#ffd166",
    "BODY_PART":      "#c9b1ff",
    "PATHOGEN":       "#f08080",
    "LAB_VALUE":      "#98d8c8",
    "DRUG":           "#1e6bb8",
    "DOSAGE":         "#e07b39",
    "CONDITION":      "#dd4444",
    "ADVERSE_EFFECT": "#c44569",
    "TREATMENT":      "#26de81",
}

VALID_TYPES = set(PALETTE.keys())

# ── SQLite ────────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # concurrent reads
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          TEXT PRIMARY KEY,
            status      TEXT    NOT NULL DEFAULT 'pending',
            note        TEXT    NOT NULL DEFAULT '',
            corrections TEXT    NOT NULL DEFAULT '[]',
            updated_at  TEXT,
            updated_by  TEXT
        )
    """)
    conn.commit()
    return conn


def _load_review(rid: str) -> dict:
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE id=?", (rid,)).fetchone()
    if not row:
        return {"id": rid, "status": "pending", "note": "", "corrections": None}
    corr = json.loads(row["corrections"]) if row["corrections"] else None
    return {
        "id":          row["id"],
        "status":      row["status"],
        "note":        row["note"],
        "corrections": corr,
        "updated_at":  row["updated_at"],
        "updated_by":  row["updated_by"],
    }


def _save_review(rid: str, status: str, note: str,
                 corrections: list | None, user: str) -> None:
    corr_json = json.dumps(corrections, ensure_ascii=False) if corrections is not None else "[]"
    now = datetime.now(timezone.utc).isoformat()
    with _get_db() as conn:
        conn.execute("""
            INSERT INTO reviews (id, status, note, corrections, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status      = excluded.status,
                note        = excluded.note,
                corrections = excluded.corrections,
                updated_at  = excluded.updated_at,
                updated_by  = excluded.updated_by
        """, (rid, status, note, corr_json, now, user))


def _get_stats_db() -> dict:
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM reviews GROUP BY status"
        ).fetchall()
    counts = {r["status"]: r["cnt"] for r in rows}
    return counts


# ── Corpus ────────────────────────────────────────────────────────────────────

_ANN_CACHE: list[dict] | None = None

def _load_annotations() -> list[dict]:
    global _ANN_CACHE
    if _ANN_CACHE is None:
        rows = []
        with open(ANN_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        _ANN_CACHE = rows
    return _ANN_CACHE


def _ann_map() -> dict[str, dict]:
    return {r["id"]: r for r in _load_annotations()}


# ── Rendering ─────────────────────────────────────────────────────────────────

def _render_highlighted(text: str, entities: list[dict]) -> str:
    flat_types = {"DRUG_NAME","DOSE_NUM","FREQ","ROUTE","DISEASE",
                  "SYMPTOM","BODY_PART","PATHOGEN","LAB_VALUE"}
    spans = sorted(
        [e for e in entities if e["type"] in flat_types],
        key=lambda e: (e["start"], -(e["end"] - e["start"])),
    )
    merged, last_end = [], 0
    for sp in spans:
        if sp["start"] >= last_end:
            merged.append(sp)
            last_end = sp["end"]

    result, cursor = [], 0
    for sp in merged:
        s, e, etype = sp["start"], sp["end"], sp["type"]
        color = PALETTE.get(etype, "#ccc")
        result.append(text[cursor:s].replace("<","&lt;").replace(">","&gt;"))
        snippet = text[s:e].replace("<","&lt;").replace(">","&gt;")
        result.append(
            f'<mark style="background:{color}33;border:1px solid {color};'
            f'border-radius:3px;padding:1px 3px;cursor:pointer" '
            f'title="{etype}" data-start="{s}" data-end="{e}" data-type="{etype}">'
            f'{snippet}'
            f'<sup style="font-size:9px;opacity:.8;margin-left:2px">{etype}</sup></mark>'
        )
        cursor = e
    result.append(text[cursor:].replace("<","&lt;").replace(">","&gt;"))
    return "".join(result)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return render_template("review_index.html", palette=PALETTE,
                           valid_types=sorted(VALID_TYPES), username=_USERNAME)


@app.get("/api/me")
def api_me():
    return jsonify({"user": _USERNAME})


@app.get("/api/stats")
def api_stats():
    ann    = _load_annotations()
    counts = _get_stats_db()
    total  = len(ann)
    sources: dict[str, int] = {}
    for r in ann:
        src = r.get("source", "")
        sources[src] = sources.get(src, 0) + 1
    verified = counts.get("verified", 0)
    flagged  = counts.get("flagged",  0)
    pending  = total - verified - flagged
    return jsonify({"total": total, "verified": verified,
                    "flagged": flagged, "pending": pending, "sources": sources})


@app.get("/api/list")
def api_list():
    mode   = request.args.get("filter", "all")
    source = request.args.get("source", "")
    page   = int(request.args.get("page", 1))
    limit  = int(request.args.get("limit", 60))

    ann = _load_annotations()

    # Build review status map in one DB call
    with _get_db() as conn:
        rows = conn.execute("SELECT id, status, updated_by FROM reviews").fetchall()
    rv_map = {r["id"]: dict(r) for r in rows}

    items = []
    for rec in ann:
        rid    = rec["id"]
        rv     = rv_map.get(rid, {})
        status = rv.get("status", "pending")
        src    = rec.get("source", "")

        if source and src != source:
            continue
        if mode == "pending"  and status != "pending":
            continue
        if mode == "verified" and status != "verified":
            continue
        if mode == "flagged"  and status != "flagged":
            continue

        items.append({
            "id":           rid,
            "source":       src,
            "text":         rec["text"],
            "status":       status,
            "entity_count": len(rec.get("entities", [])),
            "updated_by":   rv.get("updated_by", ""),
        })

    total    = len(items)
    start    = (page - 1) * limit
    page_items = items[start : start + limit]
    return jsonify({"total": total, "page": page, "items": page_items})


@app.get("/api/record/<rid>")
def api_record(rid: str):
    amap = _ann_map()
    rec  = amap.get(rid)
    if not rec:
        return jsonify({"error": "not found"}), 404

    rv       = _load_review(rid)
    # corrections override original entities when present
    entities = rv["corrections"] if rv["corrections"] is not None else rec.get("entities", [])

    return jsonify({
        "id":           rid,
        "doc_id":       rec.get("doc_id"),
        "source":       rec.get("source"),
        "text":         rec["text"],
        "highlighted":  _render_highlighted(rec["text"], entities),
        "entities":     sorted(entities, key=lambda e: e["start"]),
        "orig_entities":rec.get("entities", []),
        "status":       rv["status"],
        "note":         rv["note"],
        "updated_by":   rv.get("updated_by", ""),
        "updated_at":   rv.get("updated_at", ""),
        "palette":      PALETTE,
    })


@app.post("/api/review/<rid>")
def api_review(rid: str):
    body        = request.get_json(force=True)
    status      = body.get("status", "pending")
    note        = body.get("note", "")
    corrections = body.get("corrections")   # None = no edit, list = edited
    user        = body.get("user", _USERNAME)

    # Validate corrections if provided
    if corrections is not None:
        amap = _ann_map()
        rec  = amap.get(rid)
        if rec:
            text = rec["text"]
            valid = []
            for e in corrections:
                s, en, t = e.get("start"), e.get("end"), e.get("type","")
                if (isinstance(s, int) and isinstance(en, int)
                        and 0 <= s < en <= len(text)
                        and text[s:en] == e.get("text","")
                        and t in VALID_TYPES):
                    valid.append(e)
            corrections = valid

    _save_review(rid, status, note, corrections, user)
    return jsonify({"ok": True})


@app.get("/api/nav")
def api_nav():
    mode   = request.args.get("filter", "all")
    source = request.args.get("source", "")
    cur_id = request.args.get("id", "")

    ann = _load_annotations()
    with _get_db() as conn:
        rows = conn.execute("SELECT id, status FROM reviews").fetchall()
    rv_map = {r["id"]: r["status"] for r in rows}

    ids = []
    for rec in ann:
        rid    = rec["id"]
        status = rv_map.get(rid, "pending")
        src    = rec.get("source", "")
        if source and src != source:
            continue
        if mode == "pending"  and status != "pending":
            continue
        if mode == "verified" and status != "verified":
            continue
        if mode == "flagged"  and status != "flagged":
            continue
        ids.append(rid)

    try:
        idx = ids.index(cur_id)
    except ValueError:
        idx = 0

    return jsonify({
        "prev":  ids[idx - 1] if idx > 0            else None,
        "next":  ids[idx + 1] if idx < len(ids) - 1 else None,
        "pos":   idx + 1,
        "total": len(ids),
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ann  = _load_annotations()
    stat = _get_stats_db()
    done = stat.get("verified", 0) + stat.get("flagged", 0)
    print("=" * 55)
    print("  REVIEW TOOL")
    print("=" * 55)
    print(f"  Dataset : {ANN_PATH.name}  ({len(ann):,} câu)")
    print(f"  DB      : {DB_PATH.name}")
    print(f"  User    : {_USERNAME}")
    print(f"  Đã xử lý: {done:,} / {len(ann):,}  ({done/max(len(ann),1)*100:.1f}%)")
    print(f"\n  Mở trình duyệt: http://localhost:{_PORT}\n")
    app.run(host="0.0.0.0", port=_PORT, debug=False, threaded=True)
