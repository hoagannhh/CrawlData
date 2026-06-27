"""
Tool gán nhãn NER — gán nhãn từ đầu, không có pre-annotation.
SQLite backend, hỗ trợ nhiều người cùng lúc.

Chạy:
    python3 dataset/annotate_tool.py [--user TenNguoi] [--port 8767]
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR   = Path(__file__).resolve().parent.parent
CORPUS     = BASE_DIR / "data" / "dataset" / "corpus_clean.jsonl"
DB_PATH    = BASE_DIR / "data" / "dataset" / "annotate_results.db"

_USERNAME = "anonymous"
_PORT     = 8767
for i, arg in enumerate(sys.argv[1:]):
    if arg == "--user" and i + 2 < len(sys.argv):
        _USERNAME = sys.argv[i + 2]
    if arg == "--port" and i + 2 < len(sys.argv):
        _PORT = int(sys.argv[i + 2])

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "annotate_tool" / "templates"),
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

# ── SQLite ─────────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id            TEXT PRIMARY KEY,
            entities      TEXT    NOT NULL DEFAULT '[]',
            status        TEXT    NOT NULL DEFAULT 'done',
            annotated_at  TEXT,
            annotated_by  TEXT
        )
    """)
    conn.commit()
    return conn


def save_annotation(rid: str, entities: list, status: str, user: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO annotations (id, entities, status, annotated_at, annotated_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                entities     = excluded.entities,
                status       = excluded.status,
                annotated_at = excluded.annotated_at,
                annotated_by = excluded.annotated_by
        """, (rid, json.dumps(entities, ensure_ascii=False), status, now, user))


def get_done_ids() -> set[str]:
    with get_db() as conn:
        rows = conn.execute("SELECT id FROM annotations").fetchall()
    return {r["id"] for r in rows}


def get_annotation(rid: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM annotations WHERE id=?", (rid,)).fetchone()
    if not row:
        return None
    return {
        "id":       row["id"],
        "entities": json.loads(row["entities"]),
        "status":   row["status"],
        "annotated_by": row["annotated_by"],
        "annotated_at": row["annotated_at"],
    }


# ── Corpus cache ───────────────────────────────────────────────────────────────

_CACHE: list[dict] | None = None

def load_corpus() -> list[dict]:
    global _CACHE
    if _CACHE is None:
        rows = []
        with open(CORPUS, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        _CACHE = rows
    return _CACHE


def corpus_map() -> dict[str, dict]:
    return {r["id"]: r for r in load_corpus()}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return render_template("annotate_index.html",
                           palette=PALETTE,
                           valid_types=sorted(VALID_TYPES),
                           username=_USERNAME)


@app.get("/api/me")
def api_me():
    return jsonify({"user": _USERNAME})


@app.get("/api/stats")
def api_stats():
    corpus = load_corpus()
    total  = len(corpus)
    done_ids = get_done_ids()
    done   = len(done_ids)
    sources: dict[str, int] = {}
    done_src: dict[str, int] = {}
    for r in corpus:
        src = r.get("source", "")
        sources[src] = sources.get(src, 0) + 1
        if r["id"] in done_ids:
            done_src[src] = done_src.get(src, 0) + 1
    return jsonify({
        "total":    total,
        "done":     done,
        "pending":  total - done,
        "sources":  sources,
        "done_src": done_src,
    })


@app.get("/api/list")
def api_list():
    source   = request.args.get("source", "")
    mode     = request.args.get("filter", "pending")  # pending | done | all
    page     = int(request.args.get("page", 1))
    limit    = int(request.args.get("limit", 60))

    corpus   = load_corpus()
    done_ids = get_done_ids()

    items = []
    for rec in corpus:
        rid = rec["id"]
        src = rec.get("source", "")
        is_done = rid in done_ids

        if source and src != source:
            continue
        if mode == "pending" and is_done:
            continue
        if mode == "done" and not is_done:
            continue

        items.append({
            "id":     rid,
            "source": src,
            "text":   rec["text"],
            "done":   is_done,
        })

    total      = len(items)
    page_items = items[(page - 1) * limit : page * limit]
    return jsonify({"total": total, "page": page, "items": page_items})


@app.get("/api/record/<rid>")
def api_record(rid: str):
    cmap = corpus_map()
    rec  = cmap.get(rid)
    if not rec:
        return jsonify({"error": "not found"}), 404

    ann = get_annotation(rid)
    return jsonify({
        "id":           rid,
        "doc_id":       rec.get("doc_id"),
        "source":       rec.get("source"),
        "text":         rec["text"],
        "is_medical":   rec.get("is_medical", False),
        "entities":     ann["entities"] if ann else [],
        "done":         ann is not None,
        "annotated_by": ann["annotated_by"] if ann else None,
    })


@app.post("/api/save/<rid>")
def api_save(rid: str):
    body   = request.get_json(force=True)
    status = body.get("status", "done")   # done | skipped
    user   = body.get("user", _USERNAME)
    raw    = body.get("entities", [])

    cmap = corpus_map()
    rec  = cmap.get(rid)
    if not rec:
        return jsonify({"error": "not found"}), 404

    text  = rec["text"]
    valid = []
    for e in raw:
        s, en, t = e.get("start"), e.get("end"), e.get("type", "")
        et = e.get("text", "")
        if (isinstance(s, int) and isinstance(en, int)
                and 0 <= s < en <= len(text)
                and text[s:en] == et
                and t in VALID_TYPES):
            valid.append({"start": s, "end": en, "type": t, "text": et})

    save_annotation(rid, valid, status, user)
    return jsonify({"ok": True, "saved": len(valid)})


@app.get("/api/next")
def api_next():
    """Trả về id câu tiếp theo chưa gán nhãn."""
    after  = request.args.get("after", "")
    source = request.args.get("source", "")
    corpus = load_corpus()
    done   = get_done_ids()

    found  = not after  # nếu không có after → lấy câu đầu tiên
    for rec in corpus:
        src = rec.get("source", "")
        if source and src != source:
            continue
        if rec["id"] == after:
            found = True
            continue
        if found and rec["id"] not in done:
            return jsonify({"id": rec["id"]})

    return jsonify({"id": None})


@app.get("/api/export")
def api_export():
    """Export toàn bộ annotations đã gán nhãn dưới dạng JSONL."""
    cmap = corpus_map()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM annotations WHERE status='done' ORDER BY rowid"
        ).fetchall()

    lines = []
    for row in rows:
        rec = cmap.get(row["id"], {})
        lines.append(json.dumps({
            "id":           row["id"],
            "doc_id":       rec.get("doc_id"),
            "source":       rec.get("source"),
            "text":         rec.get("text", ""),
            "entities":     json.loads(row["entities"]),
            "annotated_by": row["annotated_by"],
            "annotated_at": row["annotated_at"],
        }, ensure_ascii=False))

    from flask import Response
    return Response(
        "\n".join(lines),
        mimetype="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=annotations_export.jsonl"},
    )


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    corpus   = load_corpus()
    done_ids = get_done_ids()
    done     = len(done_ids)
    total    = len(corpus)
    print("=" * 55)
    print("  ANNOTATION TOOL")
    print("=" * 55)
    print(f"  Corpus  : {CORPUS.name}  ({total:,} câu)")
    print(f"  DB      : {DB_PATH.name}")
    print(f"  User    : {_USERNAME}")
    print(f"  Tiến độ: {done:,} / {total:,}  ({done/max(total,1)*100:.1f}%)")
    print(f"\n  Mở trình duyệt: http://localhost:{_PORT}\n")
    app.run(host="0.0.0.0", port=_PORT, debug=False, threaded=True)
