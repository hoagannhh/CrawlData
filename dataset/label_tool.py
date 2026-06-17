"""
Công cụ gán nhãn thủ công — gợi ý LLM (Ollama), quyết định cuối cùng do bạn.

Tích hợp logic từ step4_preannotate.py:
  - Load toàn bộ corpus y tế (không chỉ file đã annotate)
  - Nút "Gợi ý LLM" gọi Ollama theo schema hiện tại
  - Schema chỉnh trong UI → prompt LLM cập nhật theo

Chạy:
    ollama serve                    # terminal riêng (nếu dùng gợi ý LLM)
    python dataset/label_tool.py

Mở trình duyệt: http://localhost:8765
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    PALETTE,
    SchemaType,
    load_schema,
    save_schema,
    schema_to_api,
    valid_type_names,
)
from dataset.llm_annotate import MODEL, annotate_text, ollama_status

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "label_tool" / "templates"),
)


def _source_by_id() -> dict[str, dict]:
    return {r["id"]: r for r in load_source_records()}


def _normalize_entities(entities: list[dict], text: str, types: set[str]) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple] = set()
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        etype = ent.get("type", "")
        if etype not in types:
            continue
        start = ent.get("start")
        end = ent.get("end")
        ent_text = ent.get("text", "")
        if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
            snippet = text[start:end]
        elif isinstance(ent_text, str) and ent_text:
            idx = text.find(ent_text)
            if idx == -1:
                continue
            start, end, snippet = idx, idx + len(ent_text), ent_text
        else:
            continue
        key = (start, end, etype)
        if key in seen:
            continue
        seen.add(key)
        result.append({"start": start, "end": end, "type": etype, "text": snippet})
    return sorted(result, key=lambda e: (e["start"], e["end"]))


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/ollama/status")
def api_ollama_status():
    return jsonify(ollama_status())


@app.get("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.get("/api/schema")
def api_schema_get():
    return jsonify(schema_to_api())


@app.put("/api/schema")
def api_schema_put():
    body = request.get_json(force=True)
    raw_types = body.get("types", [])
    types: list[SchemaType] = []
    names: set[str] = set()
    for i, t in enumerate(raw_types):
        name = t.get("name", "").strip().upper().replace(" ", "_")
        if not name or name in names:
            continue
        names.add(name)
        types.append(SchemaType(
            name=name,
            level=t.get("level", "flat"),
            description=t.get("description", ""),
            examples=t.get("examples", []),
            can_contain=t.get("can_contain", []),
            color=t.get("color", PALETTE[i % len(PALETTE)]),
        ))
    if not types:
        return jsonify({"error": "Schema phải có ít nhất 1 nhãn"}), 400
    save_schema(types)
    return jsonify(schema_to_api(types))


@app.get("/api/sentences")
def api_sentences():
    filter_mode = request.args.get("filter", "all")
    ids = list_ids(filter_mode)
    human = load_human_map()
    llm_map = _source_by_id()
    items = []
    for sid in ids[:500]:
        h = human.get(sid)
        src = llm_map.get(sid, {})
        items.append({
            "id": sid,
            "reviewed": bool(h and h.get("reviewed")),
            "has_llm": bool(src.get("entities")),
            "entity_count": len((h or {}).get("entities", [])),
        })
    return jsonify({"ids": ids, "preview": items, "total": len(ids)})


@app.get("/api/sentence/<sid>")
def api_sentence_get(sid: str):
    source = _source_by_id().get(sid)
    if not source:
        return jsonify({"error": "Không tìm thấy câu"}), 404
    human = load_human_map().get(sid)
    return jsonify(merge_record(source, human))


@app.post("/api/sentence/<sid>/suggest")
def api_sentence_suggest(sid: str):
    """Gọi Ollama gợi ý nhãn cho 1 câu (logic step4, schema động)."""
    source = _source_by_id().get(sid)
    if not source:
        return jsonify({"error": "Không tìm thấy câu"}), 404

    status = ollama_status()
    if not status["online"]:
        return jsonify({"error": "Ollama chưa chạy. Mở terminal: ollama serve"}), 503
    if not status["model_ready"]:
        return jsonify({"error": f"Model {MODEL} chưa có. Chạy: ollama pull {MODEL}"}), 503

    schema_types = load_schema()
    entities, error_msg = annotate_text(source["text"], schema_types)

    llm_record = {
        "id": sid,
        "doc_id": source.get("doc_id"),
        "source": source.get("source"),
        "text": source["text"],
        "llm": True,
        "model": MODEL,
        "entities": entities,
        "doc_fields": source.get("doc_fields"),
    }
    if error_msg:
        llm_record["error"] = error_msg
        return jsonify({"error": error_msg}), 502

    save_llm_record(llm_record)

    human = load_human_map().get(sid)
    merged = merge_record({**source, "entities": entities}, human)
    merged["llm_entities"] = entities
    merged["llm_model"] = MODEL
    return jsonify(merged)


@app.put("/api/sentence/<sid>")
def api_sentence_put(sid: str):
    source = _source_by_id().get(sid)
    if not source:
        return jsonify({"error": "Không tìm thấy câu"}), 404

    body = request.get_json(force=True)
    types = valid_type_names()
    text = source["text"]
    entities = _normalize_entities(body.get("entities", []), text, types)
    llm_entities = _normalize_entities(
        body.get("llm_entities", source.get("entities", [])),
        text,
        types,
    )

    record = {
        "id": sid,
        "doc_id": source.get("doc_id"),
        "source": source.get("source"),
        "text": text,
        "llm_entities": llm_entities,
        "llm_model": body.get("llm_model", source.get("llm_model")),
        "entities": entities,
        "reviewed": bool(body.get("reviewed", True)),
        "notes": body.get("notes", ""),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_human_record(record)
    return jsonify(record)


def main():
    import webbrowser
    from threading import Timer

    port = 8765
    url = f"http://127.0.0.1:{port}"
    stats = get_stats()
    oll = ollama_status()

    print("=" * 55)
    print("  CÔNG CỤ GÁN NHÃN (LLM gợi ý + duyệt tay)")
    print("=" * 55)
    print(f"  Mở trình duyệt: {url}")
    print(f"  Corpus         : {stats['total']:,} câu")
    print(f"  Đã có gợi ý LLM: {stats['with_llm']:,} · Chưa: {stats['no_llm']:,}")
    if oll["online"] and oll["model_ready"]:
        print(f"  Ollama         : OK ({MODEL})")
    elif oll["online"]:
        print(f"  Ollama         : chạy nhưng thiếu model → ollama pull {MODEL}")
    else:
        print("  Ollama         : chưa chạy (gợi ý LLM cần: ollama serve)")
    print("  Ctrl+C để dừng")
    print()
    Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
