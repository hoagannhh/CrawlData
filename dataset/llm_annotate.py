"""
LLM pre-annotation qua Ollama — dùng chung cho step4 và label tool.

Schema lấy từ data/dataset/entity_schema.json (chỉnh trong label tool).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from dataset.label_tool.schema_store import SchemaType, load_schema

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
MAX_TOKENS = 1_024

SYSTEM_PROMPT = """\
Bạn là chuyên gia gán nhãn thực thể y tế (NER) tiếng Việt.
Chỉ trả về một JSON object hợp lệ, không thêm bất kỳ text nào khác.\
"""


def schema_to_desc(types: list[SchemaType] | None = None) -> str:
    if types is None:
        types = load_schema()

    lines = ["FLAT ENTITIES:"]
    for t in types:
        if t.level != "flat":
            continue
        ex = ", ".join(f'"{e}"' for e in t.examples[:3])
        suffix = f"  (e.g. {ex})" if ex else ""
        lines.append(f"  {t.name:<15}: {t.description}{suffix}")

    lines.append("\nNESTED ENTITIES (bao chứa flat):")
    for t in types:
        if t.level != "nested":
            continue
        contains = " + ".join(t.can_contain) if t.can_contain else t.description
        ex = ", ".join(f'"{e}"' for e in t.examples[:2])
        lines.append(f"  {t.name:<15}: {contains}  e.g. {ex}")

    return "\n".join(lines)


def valid_type_names(types: list[SchemaType] | None = None) -> set[str]:
    if types is None:
        types = load_schema()
    return {t.name for t in types}


def build_prompt(text: str, types: list[SchemaType] | None = None) -> str:
    schema_desc = schema_to_desc(types)
    return f"""\
Gán nhãn tất cả thực thể y tế trong câu sau.

SCHEMA:
{schema_desc}

Câu: "{text}"

Trả về JSON: {{"entities": [{{"start": int, "end": int, "type": str, "text": str}}, ...]}}
start/end là chỉ số ký tự 0-based (Python: text[start:end] == text của entity).
Gán nhãn cả nested entities. Nếu không có entity: {{"entities": []}}

Ví dụ câu "Uống Amoxicillin 500mg 3 lần/ngày":
{{"entities": [{{"start":5,"end":16,"type":"DRUG_NAME","text":"Amoxicillin"}},{{"start":17,"end":22,"type":"DOSE_NUM","text":"500mg"}},{{"start":23,"end":33,"type":"FREQ","text":"3 lần/ngày"}},{{"start":5,"end":22,"type":"DRUG","text":"Amoxicillin 500mg"}}]}}\
"""


def ollama_chat(prompt: str, timeout: int = 120) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": MAX_TOKENS},
        "format": "json",
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
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def ollama_has_model() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            data = json.loads(r.read())
        names = [m["name"] for m in data.get("models", [])]
        return any(MODEL in n for n in names)
    except Exception:
        return False


def ollama_status() -> dict:
    if not ollama_ping():
        return {"online": False, "model_ready": False, "host": OLLAMA_HOST, "model": MODEL}
    return {
        "online": True,
        "model_ready": ollama_has_model(),
        "host": OLLAMA_HOST,
        "model": MODEL,
    }


def parse_entities(
    raw: str | dict,
    sent_text: str,
    types: list[SchemaType] | None = None,
) -> list[dict]:
    valid = valid_type_names(types)

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
        etype = ent.get("type")
        ent_text = ent.get("text", "")
        start = ent.get("start")
        end = ent.get("end")

        if etype not in valid:
            continue
        if not isinstance(ent_text, str) or not ent_text.strip():
            continue

        ent_text = ent_text.strip()
        actual_start: int | None = None
        actual_end: int | None = None

        idx = sent_text.find(ent_text)
        if idx != -1:
            actual_start = idx
            actual_end = idx + len(ent_text)
        elif (isinstance(start, int) and isinstance(end, int)
              and 0 <= start < end <= text_len
              and sent_text[start:end] == ent_text):
            actual_start = start
            actual_end = end
        else:
            continue

        key = (actual_start, actual_end, etype)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "start": actual_start,
            "end": actual_end,
            "type": etype,
            "text": sent_text[actual_start:actual_end],
        })

    return sorted(result, key=lambda e: (e["start"], e["end"]))


def annotate_text(
    text: str,
    types: list[SchemaType] | None = None,
    retries: int = 3,
) -> tuple[list[dict], str | None]:
    """Gọi Ollama, trả về (entities, error)."""
    last_err: str | None = None
    for attempt in range(retries):
        try:
            raw = ollama_chat(build_prompt(text, types))
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            return parse_entities(parsed, text, types), None
        except urllib.error.URLError as e:
            return [], f"Ollama không phản hồi ({OLLAMA_HOST}). Chạy: ollama serve"
        except Exception as e:
            last_err = str(e)[:200]
            if attempt < retries - 1:
                time.sleep(3)
    return [], last_err or "unknown error"
