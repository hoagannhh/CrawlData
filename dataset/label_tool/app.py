"""Flask backend cho annotation tool.

Chạy:
    python dataset/label_tool/app.py

Mở trình duyệt: http://localhost:5000
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from dataset.label_tool.data_store import (
    get_stats,
    list_ids,
    load_human_map,
    load_source_records,
    merge_record,
    save_human_record,
    save_llm_record,
)
from dataset.label_tool.schema_store import (
    load_schema,
    save_schema,
    schema_to_api,
    valid_type_names,
)
from dataset.label_tool.schema_store import SchemaType

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
MAX_TOKENS = 1_024

app = Flask(__name__, template_folder="templates")

# Cache corpus in memory sau lần load đầu
_source_cache: list[dict] | None = None


def _get_sources() -> list[dict]:
    global _source_cache
    if _source_cache is None:
        _source_cache = load_source_records()
    return _source_cache


def _invalidate_cache() -> None:
    global _source_cache
    _source_cache = None


# ── Ollama helpers ────────────────────────────────────────────────────────────

def _ollama_ping() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def _ollama_has_model() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            data = json.loads(r.read())
        return any(OLLAMA_MODEL in m["name"] for m in data.get("models", []))
    except Exception:
        return False


def _build_schema_desc(schema_types: list) -> str:
    flat   = [t for t in schema_types if t.level == "flat"]
    nested = [t for t in schema_types if t.level == "nested"]
    lines  = ["FLAT ENTITIES:"]
    for t in flat:
        ex = f'  (e.g. {", ".join(repr(e) for e in t.examples[:2])})' if t.examples else ""
        lines.append(f'  {t.name:<15}: {t.description}{ex}')
    lines.append("\nNESTED ENTITIES (bao chứa flat):")
    for t in nested:
        contains = f'  [{", ".join(t.can_contain)}]' if t.can_contain else ""
        ex = f'  (e.g. {t.examples[0]})' if t.examples else ""
        lines.append(f'  {t.name:<15}: {t.description}{contains}{ex}')
    return "\n".join(lines)


def _ollama_suggest(text: str, schema_types: list) -> list[dict]:
    """Gọi Ollama, trả về danh sách entity đã validate."""
    schema_desc = _build_schema_desc(schema_types)
    valid_types = {t.name for t in schema_types}

    system_prompt = (
        "Bạn là chuyên gia gán nhãn thực thể y tế (NER) tiếng Việt. "
        "Chỉ trả về một JSON object hợp lệ, không thêm text nào khác."
    )
    user_prompt = f"""\
Gán nhãn tất cả thực thể y tế trong câu sau.

SCHEMA:
{schema_desc}

Câu: "{text}"

Trả về JSON: {{"entities": [{{"start": int, "end": int, "type": str, "text": str}}, ...]}}
start/end là chỉ số ký tự 0-based (Python: text[start:end] == text của entity).
Gán nhãn cả nested entities. Nếu không có entity: {{"entities": []}}"""

    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "stream":  False,
        "format":  "json",
        "options": {"temperature": 0.0, "num_predict": MAX_TOKENS},
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())

    raw = data["message"]["content"]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return _validate_entities(parsed.get("entities", []), text, valid_types)


def _validate_entities(entities_raw: list, text: str, valid_types: set[str]) -> list[dict]:
    """Validate + tìm lại vị trí thực từ text field nếu offset sai."""
    text_len = len(text)
    seen: set[tuple] = set()
    result: list[dict] = []

    for ent in entities_raw:
        if not isinstance(ent, dict):
            continue
        etype    = ent.get("type", "")
        ent_text = str(ent.get("text", "")).strip()
        start    = ent.get("start")
        end      = ent.get("end")

        if etype not in valid_types or not ent_text:
            continue

        # Ưu tiên dùng text để tìm vị trí thực (model hay sai offset với tiếng Việt)
        actual_start: int | None = None
        actual_end:   int | None = None

        idx = text.find(ent_text)
        if idx != -1:
            actual_start, actual_end = idx, idx + len(ent_text)
        elif (isinstance(start, int) and isinstance(end, int)
              and 0 <= start < end <= text_len
              and text[start:end] == ent_text):
            actual_start, actual_end = start, end
        else:
            continue

        key = (actual_start, actual_end, etype)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "start": actual_start,
            "end":   actual_end,
            "type":  etype,
            "text":  text[actual_start:actual_end],
        })

    return sorted(result, key=lambda e: (e["start"], e["end"]))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return render_template("index.html")


# Schema
@app.get("/api/schema")
def api_schema_get():
    return jsonify(schema_to_api())


@app.put("/api/schema")
def api_schema_put():
    data  = request.get_json()
    types = [SchemaType(**t) for t in data.get("types", [])]
    save_schema(types)
    return jsonify(schema_to_api(types))


# Stats
@app.get("/api/stats")
def api_stats():
    return jsonify(get_stats())


# Ollama status
@app.get("/api/ollama/status")
def api_ollama_status():
    online      = _ollama_ping()
    model_ready = _ollama_has_model() if online else False
    return jsonify({
        "online":      online,
        "model_ready": model_ready,
        "model":       OLLAMA_MODEL,
        "host":        OLLAMA_HOST,
    })


# Sentence list
@app.get("/api/sentences")
def api_sentences():
    filter_mode = request.args.get("filter", "all")
    ids = list_ids(filter_mode)
    return jsonify({"ids": ids, "total": len(ids)})


# Single sentence GET
@app.get("/api/sentence/<sid>")
def api_sentence_get(sid: str):
    sources  = {r["id"]: r for r in _get_sources()}
    human    = load_human_map()
    source   = sources.get(sid)
    if source is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(merge_record(source, human.get(sid)))


# Single sentence PUT (save human annotation)
@app.put("/api/sentence/<sid>")
def api_sentence_put(sid: str):
    sources = {r["id"]: r for r in _get_sources()}
    if sid not in sources:
        return jsonify({"error": "not found"}), 404

    body = request.get_json()
    src  = sources[sid]
    save_human_record({
        "id":          sid,
        "doc_id":      src.get("doc_id"),
        "source":      src.get("source"),
        "text":        src["text"],
        "llm_entities": body.get("llm_entities", src.get("entities", [])),
        "llm_model":   body.get("llm_model", src.get("llm_model")),
        "entities":    body.get("entities", []),
        "reviewed":    body.get("reviewed", False),
        "notes":       body.get("notes", ""),
    })
    return jsonify({"ok": True})


# On-demand LLM suggestion for one sentence
@app.post("/api/sentence/<sid>/suggest")
def api_suggest(sid: str):
    sources = {r["id"]: r for r in _get_sources()}
    source  = sources.get(sid)
    if source is None:
        return jsonify({"error": "not found"}), 404

    if not _ollama_ping():
        return jsonify({"error": "Ollama server không chạy. Chạy: ollama serve"}), 503
    if not _ollama_has_model():
        return jsonify({"error": f"Model '{OLLAMA_MODEL}' chưa được pull. Chạy: ollama pull {OLLAMA_MODEL}"}), 503

    schema_types = load_schema()
    try:
        entities = _ollama_suggest(source["text"], schema_types)
    except urllib.error.URLError as e:
        return jsonify({"error": f"Không kết nối được Ollama: {e}"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Lưu vào checkpoint/llm_annotations để dùng lại sau
    llm_record = {
        "id":         sid,
        "doc_id":     source.get("doc_id"),
        "source":     source.get("source"),
        "text":       source["text"],
        "llm":        True,
        "model":      OLLAMA_MODEL,
        "entities":   entities,
        "doc_fields": source.get("doc_fields"),
    }
    save_llm_record(llm_record)
    _invalidate_cache()   # buộc load lại source records

    return jsonify({
        "llm_entities": entities,
        "llm_model":    OLLAMA_MODEL,
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    port = int(os.environ.get("PORT", 5000))
    print(f"  Annotation tool: http://localhost:{port}")
    print(f"  Ollama: {OLLAMA_HOST}  Model: {OLLAMA_MODEL}")
    print(f"  Ctrl+C để dừng\n")

    # Preload corpus một lần khi khởi động
    print("  Đang load corpus...", end=" ", flush=True)
    try:
        sources = _get_sources()
        print(f"{len(sources):,} câu")
    except FileNotFoundError as e:
        print(f"\n  Lỗi: {e}")
        print("  Chạy step1_clean.py trước để tạo corpus_clean.jsonl")
        sys.exit(1)

    app.run(host="0.0.0.0", port=port, debug=False)
