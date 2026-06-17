"""Load / save editable entity schema for the label tool."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dataset.schema import ENTITY_TYPES, EntityType

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = BASE_DIR / "data" / "dataset" / "entity_schema.json"

# Distinct colors for entity highlights in the UI
PALETTE = [
    "#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12",
    "#1abc9c", "#e67e22", "#34495e", "#16a085", "#c0392b",
    "#2980b9", "#8e44ad", "#27ae60", "#d35400",
]


@dataclass
class SchemaType:
    name: str
    level: str
    description: str
    examples: list[str] = field(default_factory=list)
    can_contain: list[str] = field(default_factory=list)
    color: str = "#3498db"


def _default_schema() -> list[SchemaType]:
    types: list[SchemaType] = []
    for i, et in enumerate(ENTITY_TYPES):
        types.append(SchemaType(
            name=et.name,
            level=et.level,
            description=et.description,
            examples=list(et.examples),
            can_contain=list(et.can_contain),
            color=PALETTE[i % len(PALETTE)],
        ))
    return types


def _to_schema_type(data: dict) -> SchemaType:
    return SchemaType(
        name=data["name"].strip().upper().replace(" ", "_"),
        level=data.get("level", "flat"),
        description=data.get("description", ""),
        examples=data.get("examples", []),
        can_contain=data.get("can_contain", []),
        color=data.get("color", PALETTE[0]),
    )


def load_schema() -> list[SchemaType]:
    if not SCHEMA_PATH.exists():
        types = _default_schema()
        save_schema(types)
        return types

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    types = [_to_schema_type(t) for t in raw.get("types", [])]
    if not types:
        types = _default_schema()
        save_schema(types)
    return types


def save_schema(types: list[SchemaType]) -> None:
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "types": [asdict(t) for t in types],
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def valid_type_names(types: list[SchemaType] | None = None) -> set[str]:
    if types is None:
        types = load_schema()
    return {t.name for t in types}


def schema_to_api(types: list[SchemaType] | None = None) -> dict:
    if types is None:
        types = load_schema()
    return {
        "types": [asdict(t) for t in types],
        "flat": [t.name for t in types if t.level == "flat"],
        "nested": [t.name for t in types if t.level == "nested"],
    }
