# PharmaVi-NER: Vietnamese Biomedical Named Entity Recognition Dataset

## Dataset Summary

**PharmaVi-NER** is a Vietnamese biomedical NER dataset containing **94,500 deduplicated sentences** manually annotated with medical entities. The dataset covers drug information, clinical descriptions, disease conditions, symptoms, and treatment guidelines sourced from four major Vietnamese pharmaceutical and healthcare websites.

| Metric | Value |
|---|---|
| Total sentences | 94,500 |
| Sentences with entities | 44,997 (47.6%) |
| Total entity annotations | 92,282 |
| Entity types | 13 |
| Source documents | 4,387 |
| Language | Vietnamese |
| Annotation type | Manual human annotation |

---

## Supported Tasks

- **Named Entity Recognition (NER)**: identify and classify medical entities in Vietnamese clinical text
- **Relation Extraction**: linking drugs to dosages, diseases to pathogens, etc.
- **Information Extraction**: extracting structured drug information from free text

---

## Languages

Vietnamese (`vi`)

---

## Dataset Structure

### Data Fields

Each record in the JSONL file contains:

```json
{
  "id": "abc123_0005",
  "doc_id": "abc123",
  "source": "thuocbietduoc",
  "text": "Amoxicillin 500mg uống 3 lần/ngày điều trị viêm phổi.",
  "entities": [
    {"start": 0,  "end": 11, "type": "DRUG_NAME", "text": "Amoxicillin"},
    {"start": 12, "end": 17, "type": "DOSE_NUM",  "text": "500mg"},
    {"start": 18, "end": 22, "type": "ROUTE",     "text": "uống"},
    {"start": 23, "end": 33, "type": "FREQ",      "text": "3 lần/ngày"},
    {"start": 40, "end": 49, "type": "DISEASE",   "text": "viêm phổi"},
    {"start": 0,  "end": 17, "type": "DRUG",      "text": "Amoxicillin 500mg"},
    {"start": 12, "end": 33, "type": "DOSAGE",    "text": "500mg uống 3 lần/ngày"}
  ],
  "doc_fields": {
    "has_active_ingredient": true,
    "has_indication": true,
    "has_dosage": true,
    "has_adverse_effect": false,
    "has_contraindication": false
  }
}
```

- `start` / `end`: character offsets (0-based), `text == sentence[start:end]`
- `doc_fields`: boolean flags indicating which structured fields existed in the source document

### Entity Schema

#### Flat Entities

| Type | Description | Example |
|---|---|---|
| `DRUG_NAME` | Drug name or active ingredient | `"Paracetamol"`, `"Amoxicillin"` |
| `DOSE_NUM` | Dose amount with unit | `"500mg"`, `"2 IU"`, `"10 ml"` |
| `FREQ` | Administration frequency | `"3 lần/ngày"`, `"mỗi 8 giờ"` |
| `ROUTE` | Route of administration | `"uống"`, `"tiêm tĩnh mạch"`, `"bôi"` |
| `DISEASE` | Disease or syndrome name | `"viêm phổi"`, `"đái tháo đường"` |
| `SYMPTOM` | Clinical symptom | `"sốt"`, `"ho khan"`, `"khó thở"` |
| `BODY_PART` | Body part or organ | `"gan"`, `"thận"`, `"phổi"` |
| `PATHOGEN` | Disease-causing agent | `"Helicobacter pylori"`, `"vi khuẩn gram âm"` |
| `LAB_VALUE` | Laboratory or clinical measurement | `"glucose 7.2 mmol/L"`, `"38.5°C"` |

#### Nested Entities

| Type | Contains | Example |
|---|---|---|
| `DRUG` | `DRUG_NAME` + `DOSE_NUM` | `"Amoxicillin 500mg"` |
| `DOSAGE` | `DOSE_NUM` + `FREQ` + `ROUTE` | `"500mg uống 3 lần/ngày"` |
| `CONDITION` | `DISEASE` + `PATHOGEN` + `BODY_PART` | `"viêm phổi do vi khuẩn"` |
| `ADVERSE_EFFECT` | `SYMPTOM` + `BODY_PART` + `DISEASE` | `"phản ứng dị ứng ngoài da"` |
| `TREATMENT` | `DRUG` + `DOSAGE` + `CONDITION` | `"Amoxicillin 500mg điều trị viêm phổi"` |

### Entity Statistics

| Type | Count | % of total |
|---|---|---|
| BODY_PART | 30,619 | 33.2% |
| SYMPTOM | 24,977 | 27.1% |
| DISEASE | 18,038 | 19.5% |
| ROUTE | 6,091 | 6.6% |
| DOSE_NUM | 3,939 | 4.3% |
| CONDITION | 2,810 | 3.0% |
| PATHOGEN | 2,435 | 2.6% |
| DRUG_NAME | 1,594 | 1.7% |
| FREQ | 1,181 | 1.3% |
| DOSAGE | 554 | 0.6% |
| DRUG | 42 | 0.05% |
| LAB_VALUE | 2 | ~0% |
| **Total** | **92,282** | |

---

## Data Sources

| Source | Domain | Documents | Sentences |
|---|---|---|---|
| [Vinmec](https://www.vinmec.com) | Hospital / Clinical articles | 1,988 | 74,281 |
| [Sức Khỏe & Đời Sống](https://suckhoedoisong.vn) | Health news & articles | 371 | 13,734 |
| [Thuốc Biệt Dược](https://thuocbietduoc.com.vn) | Drug reference database | 1,864 | 6,108 |
| [Long Châu Pharmacy](https://nhathuoclongchau.com.vn) | Pharmacy / Drug information | 164 | 377 |
| **Total** | | **4,387** | **94,500** |

---

## Data Collection & Processing

1. **Crawling**: web scraped from 4 sources using custom spiders
2. **Storage**: structured into SQLite database with fields: `name`, `active_ingredient`, `indication`, `dosage`, `adverse_effect`, `contraindication`, `description`
3. **Cleaning** (`step1_clean.py`):
   - HTML tag removal, URL/email stripping
   - Vietnamese sentence segmentation
   - Filtering sentences < 20 chars or > 600 chars
   - **Deduplication**: exact-match dedup at sentence level (removed 11,319 duplicate sentences from 105,819 raw)
4. **Annotation**: manual human annotation using character-level span labeling

---

## Annotation Guidelines

- Offsets are **0-based character indices**: `sentence[start:end] == entity_text`
- **Flat and nested entities coexist**: a `DRUG_NAME` span inside a `DRUG` span is valid
- Nested entity spans must satisfy containment constraints (see schema above)
- Entities are annotated only when **explicitly stated** in the sentence — no inference beyond sentence content
- Sentences with no medical entities are retained with `"entities": []`

---

## Considerations for Using the Data

- **Domain**: pharmaceutical and clinical Vietnamese text — may not generalize to informal medical language
- **Entity imbalance**: `BODY_PART` and `SYMPTOM` are overrepresented; `LAB_VALUE` and `DRUG` are rare
- **Nested entities**: models must support span overlap to use nested annotations
- **Vinmec dominance**: 78.6% of sentences come from Vinmec clinical articles — diversity is limited

---

## Citation

If you use this dataset, please cite:

```bibtex
@dataset{pharmavi_ner_2025,
  title     = {PharmaVi-NER: Vietnamese Biomedical Named Entity Recognition Dataset},
  author    = {hoagannhh, huynhatminh20},
  year      = {2025},
  publisher = {Hugging Face},
  url       = {https://huggingface.co/datasets/your-username/pharmavi-ner}
}
```

---

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — free to use with attribution.
