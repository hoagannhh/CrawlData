"""
Entity schema cho Vietnamese Medical Nested NER

Thiết kế theo 2 tầng:
  - FLAT entities: span nguyên tử, không chứa span khác
  - NESTED entities: span bao phủ 1+ flat entity

Ví dụ minh họa:
  Câu: "Uống Amoxicillin 500mg, 3 lần/ngày để điều trị viêm phổi do vi khuẩn."

  Flat:
    DRUG_NAME  → "Amoxicillin"
    DOSE_NUM   → "500mg"
    FREQ       → "3 lần/ngày"
    DISEASE    → "viêm phổi"
    PATHOGEN   → "vi khuẩn"

  Nested:
    DRUG       → "Amoxicillin 500mg"      (= DRUG_NAME + DOSE_NUM)
    DOSAGE     → "500mg, 3 lần/ngày"      (= DOSE_NUM + FREQ)
    CONDITION  → "viêm phổi do vi khuẩn"  (= DISEASE + PATHOGEN)
"""

from dataclasses import dataclass, field

# ── Định nghĩa từng entity type ───────────────────────────────────────────────

@dataclass
class EntityType:
    name: str          # tên dùng trong annotation
    level: str         # "flat" hoặc "nested"
    description: str
    examples: list[str]
    can_contain: list[str] = field(default_factory=list)  # chỉ dùng cho nested


ENTITY_TYPES: list[EntityType] = [

    # ── FLAT entities ──────────────────────────────────────────────────────
    EntityType(
        name="DRUG_NAME",
        level="flat",
        description="Tên thuốc / hoạt chất không bao gồm liều",
        examples=["Paracetamol", "Amoxicillin", "Mebendazole", "Ibuprofen", "Lidocaine"],
    ),
    EntityType(
        name="DOSE_NUM",
        level="flat",
        description="Con số và đơn vị liều dùng (mg, ml, IU, %...)",
        examples=["500mg", "250ml", "2%", "10 IU", "1g"],
    ),
    EntityType(
        name="FREQ",
        level="flat",
        description="Tần suất / cách dùng (số lần, khoảng cách giữa các lần)",
        examples=["3 lần/ngày", "mỗi 8 giờ", "2 lần mỗi tuần", "ngày 1 lần"],
    ),
    EntityType(
        name="ROUTE",
        level="flat",
        description="Đường dùng thuốc",
        examples=["uống", "tiêm tĩnh mạch", "bôi ngoài da", "nhỏ mắt", "đặt hậu môn"],
    ),
    EntityType(
        name="DISEASE",
        level="flat",
        description="Tên bệnh lý, hội chứng, chẩn đoán",
        examples=["viêm phổi", "đái tháo đường", "ung thư dạ dày", "hội chứng Down"],
    ),
    EntityType(
        name="SYMPTOM",
        level="flat",
        description="Triệu chứng lâm sàng",
        examples=["sốt", "ho khan", "khó thở", "đau đầu", "buồn nôn", "phát ban"],
    ),
    EntityType(
        name="BODY_PART",
        level="flat",
        description="Bộ phận / cơ quan cơ thể",
        examples=["gan", "thận", "phổi", "tim", "niệu đạo", "đường ruột"],
    ),
    EntityType(
        name="PATHOGEN",
        level="flat",
        description="Vi sinh vật gây bệnh (vi khuẩn, virus, ký sinh trùng, nấm)",
        examples=["Helicobacter pylori", "virus SARS-CoV-2", "Candida albicans", "giun đũa"],
    ),
    EntityType(
        name="LAB_VALUE",
        level="flat",
        description="Chỉ số xét nghiệm / đo lường lâm sàng",
        examples=["huyết áp 130/80 mmHg", "glucose 7.2 mmol/L", "nhiệt độ 38.5°C"],
    ),

    # ── NESTED entities ────────────────────────────────────────────────────
    EntityType(
        name="DRUG",
        level="nested",
        description="Thuốc đầy đủ = tên thuốc + liều (nếu có)",
        examples=["Amoxicillin 500mg", "Paracetamol 1g", "Lidocaine 2%"],
        can_contain=["DRUG_NAME", "DOSE_NUM"],
    ),
    EntityType(
        name="DOSAGE",
        level="nested",
        description="Chỉ dẫn liều dùng đầy đủ = liều + tần suất + đường dùng",
        examples=["500mg uống 3 lần/ngày", "tiêm tĩnh mạch 10mg mỗi 8 giờ"],
        can_contain=["DOSE_NUM", "FREQ", "ROUTE"],
    ),
    EntityType(
        name="CONDITION",
        level="nested",
        description="Tình trạng bệnh lý đầy đủ = bệnh + nguyên nhân/vị trí",
        examples=["viêm phổi do vi khuẩn", "loét dạ dày tá tràng", "nhiễm khuẩn đường tiết niệu"],
        can_contain=["DISEASE", "PATHOGEN", "BODY_PART"],
    ),
    EntityType(
        name="ADVERSE_EFFECT",
        level="nested",
        description="Tác dụng không mong muốn = triệu chứng + mức độ/vị trí",
        examples=["phản ứng dị ứng ngoài da", "suy gan nặng", "buồn nôn và nôn"],
        can_contain=["SYMPTOM", "BODY_PART", "DISEASE"],
    ),
    EntityType(
        name="TREATMENT",
        level="nested",
        description="Phác đồ điều trị = thuốc + chỉ định",
        examples=["dùng Amoxicillin 500mg điều trị viêm phổi"],
        can_contain=["DRUG", "DOSAGE", "CONDITION", "DISEASE"],
    ),
]

# ── Lookup helpers ─────────────────────────────────────────────────────────

FLAT_TYPES   = [e.name for e in ENTITY_TYPES if e.level == "flat"]
NESTED_TYPES = [e.name for e in ENTITY_TYPES if e.level == "nested"]
ALL_TYPES    = FLAT_TYPES + NESTED_TYPES

TYPE_MAP: dict[str, EntityType] = {e.name: e for e in ENTITY_TYPES}


# ── Nesting rules (dùng khi validate annotation) ──────────────────────────

NESTING_RULES: list[tuple[str, str]] = [
    # (outer, inner) — outer bao phủ inner là hợp lệ
    ("DRUG",           "DRUG_NAME"),
    ("DRUG",           "DOSE_NUM"),
    ("DOSAGE",         "DOSE_NUM"),
    ("DOSAGE",         "FREQ"),
    ("DOSAGE",         "ROUTE"),
    ("CONDITION",      "DISEASE"),
    ("CONDITION",      "PATHOGEN"),
    ("CONDITION",      "BODY_PART"),
    ("ADVERSE_EFFECT", "SYMPTOM"),
    ("ADVERSE_EFFECT", "BODY_PART"),
    ("ADVERSE_EFFECT", "DISEASE"),
    ("TREATMENT",      "DRUG"),
    ("TREATMENT",      "DOSAGE"),
    ("TREATMENT",      "CONDITION"),
    ("TREATMENT",      "DISEASE"),
]


def print_schema():
    print("=" * 60)
    print("  ENTITY SCHEMA — VIETNAMESE MEDICAL NESTED NER")
    print("=" * 60)
    print(f"\n  FLAT ENTITIES ({len(FLAT_TYPES)}):")
    for e in ENTITY_TYPES:
        if e.level == "flat":
            print(f"    [{e.name:<15}] {e.description}")
            print(f"      VD: {', '.join(e.examples[:3])}")
    print(f"\n  NESTED ENTITIES ({len(NESTED_TYPES)}):")
    for e in ENTITY_TYPES:
        if e.level == "nested":
            print(f"    [{e.name:<15}] {e.description}")
            print(f"      Chứa  : {', '.join(e.can_contain)}")
            print(f"      VD    : {', '.join(e.examples[:2])}")
    print(f"\n  Tổng: {len(ALL_TYPES)} entity types  |  {len(NESTING_RULES)} nesting rules")


if __name__ == "__main__":
    print_schema()
