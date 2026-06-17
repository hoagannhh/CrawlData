# Pipeline Log — Vietnamese Medical NER Dataset

Tài liệu này ghi lại toàn bộ luồng dữ liệu từ khi cào web cho đến khi ra
dataset NER hoàn chỉnh, bao gồm số liệu thực tế, công cụ sử dụng, và format
dữ liệu ở mỗi bước.

---

## Tổng quan

```
4 Website y tế
      │
      ▼
[Phase 0]  Thu thập (Crawling)
      │        data/raw/{source}/data.json          ~24 M dòng JSON
      ▼
[Phase 0.5] Nạp vào SQLite
      │        data/pharma.db                        26 MB
      ▼
[Phase 0.6] Export clean files
      │        data/processed/by_source/*.json|csv   63 k records
      │        data/processed/merged/all_dedup.json
      ▼
[Step 1]   Làm sạch & tách câu
      │        data/dataset/corpus_clean.jsonl        105,819 câu  45 MB
      ▼
[Step 2]   Thiết kế Entity Schema
      │        dataset/schema.py                     14 types · 15 rules
      ▼
[Step 3]   Silver Labels (Regex)
      │        data/dataset/silver_labels.jsonl       10,297 câu   5.7 MB
      ▼
[Step 4]   LLM Pre-annotation
               data/dataset/llm_annotations.jsonl     5,000 câu    (cần API key)
```

---

## Phase 0 — Thu thập dữ liệu (Crawling)

### Nguồn dữ liệu

| Nguồn            | URL                        | Loại nội dung                      | Records |
|------------------|----------------------------|------------------------------------|---------|
| thuocbietduoc    | thuocbietduoc.vn           | Tờ hướng dẫn sử dụng thuốc        | 1,972   |
| vinmec           | vinmec.com                 | Bài viết y khoa (bệnh, thuốc...)   | 2,000   |
| longchau         | nhathuoclongchau.vn        | Trang thuốc nhà thuốc              | 164     |
| suckhoedoisong   | suckhoedoisong.vn          | Báo y tế, bài sức khoẻ            | 381     |
| **Tổng**         |                            |                                    | **4,517** |

### Kiến trúc crawler

```
main.py
  └── load_spider(source_name)
        ├── BaseSpider (spiders/base_spider.py)
        │     ├── get_list_urls()     ← thu thập danh sách URL
        │     └── parse_item(url)     ← cào nội dung từng trang
        ├── RequestService (services/request_service.py)
        │     ├── requests / aiohttp  ← HTTP thông thường
        │     └── retry với back-off  (services/retry_service.py)
        └── BrowserService (services/browser_service.py)
              └── Selenium + Chrome headless  ← trang cần JS render
```

### Công cụ sử dụng

| Công cụ                    | Mục đích                                  |
|----------------------------|-------------------------------------------|
| `requests` / `aiohttp`     | HTTP requests cho trang tĩnh              |
| `Selenium` + ChromeDriver  | Render trang JS (longchau, thuocbietduoc) |
| `BeautifulSoup 4`          | Parse HTML, trích xuất text fields        |
| `tqdm`                     | Progress bar khi cào                      |
| Checkpoint files           | Lưu trạng thái batch, resume khi bị ngắt |

### Cơ chế checkpoint / resume

- Mỗi batch N URL → lưu ra `data/checkpoint/{source}_batch_XXXX.json`
- URL đã cào → `data/checkpoint/{source}_scraped_urls.json`
- Chạy lại tự bỏ qua URL đã có

### Output

```
data/raw/{source}/data.json     ← toàn bộ records thô, 1 JSON array
data/checkpoint/                ← ~40+ file batch để resume
data/logs/                      ← crawler.log, {source}_run.log
```

**Kích thước raw data:**

| Nguồn          | Dòng trong data.json |
|----------------|----------------------|
| vinmec         | 15,878,796           |
| thuocbietduoc  | 4,386,689            |
| suckhoedoisong | 2,651,939            |
| longchau       | 1,082,063            |

### Format một record thô (thuocbietduoc)

```json
{
  "id": "c446735120c3",
  "url": "https://thuocbietduoc.vn/...",
  "name": "Paracetamol 500mg",
  "source": "thuocbietduoc",
  "active_ingredient": "Paracetamol",
  "indication": "Giảm đau, hạ sốt...",
  "dosage": "Người lớn: 500mg-1g mỗi 4-6 giờ...",
  "adverse_effect": "Buồn nôn, dị ứng da...",
  "contraindication": "Suy gan nặng...",
  "description": "Paracetamol là thuốc giảm đau..."
}
```

---

## Phase 0.5 — Nạp vào SQLite

### Script

`database/db_connect.py` + `database/medicine_repository.py`

### Công cụ

| Công cụ     | Mục đích                                    |
|-------------|---------------------------------------------|
| `sqlite3`   | Database nhẹ, không cần server              |
| Schema SQL  | `database/schema.sql` — định nghĩa bảng     |

### Bảng chính: `medicines`

```sql
CREATE TABLE medicines (
    id               TEXT PRIMARY KEY,
    source           TEXT,
    name             TEXT,
    url              TEXT,
    description      TEXT,
    active_ingredient TEXT,
    indication       TEXT,
    dosage           TEXT,
    adverse_effect   TEXT,
    contraindication TEXT,
    created_at       TEXT
);
```

### Output

```
data/pharma.db   26 MB
```

**Records theo nguồn:**

| source         | Records |
|----------------|---------|
| vinmec         | 2,000   |
| thuocbietduoc  | 1,972   |
| suckhoedoisong | 381     |
| longchau       | 164     |

---

## Phase 0.6 — Export clean files

### Script

`main.py --export`

### Công cụ

| Công cụ      | Mục đích                                  |
|--------------|-------------------------------------------|
| `sqlite3`    | Đọc từ pharma.db                          |
| `pandas`     | Xuất CSV                                  |
| `json`       | Xuất JSON                                 |
| `dedup_records()` | Loại bỏ trùng theo URL hoặc MD5 description |

### Output

```
data/processed/by_source/
    thuocbietduoc_clean.json     27,609 dòng
    vinmec_clean.json            28,001 dòng
    suckhoedoisong_clean.json     5,335 dòng
    longchau_clean.json           2,297 dòng
    *.csv                        (cùng data, format CSV)

data/processed/merged/
    all_dedup.json               63,239 records (sau dedup toàn bộ)
```

---

## Step 1 — Làm sạch & Tách câu

**Script:** `dataset/step1_clean.py`
**Input:** `data/pharma.db` (bảng `medicines`, cột `description`)
**Output:**
- `data/dataset/corpus_clean.jsonl` — 105,819 câu, 45 MB
- `data/dataset/corpus_stats.json` — thống kê

### Công cụ

| Công cụ / Module      | Mục đích                                               |
|-----------------------|--------------------------------------------------------|
| `sqlite3`             | Đọc bảng medicines                                     |
| `unicodedata.normalize("NFC")` | Chuẩn hóa Unicode tiếng Việt (tổ hợp dấu)    |
| `re` (regex)          | Strip HTML tag, URL, email, noise lines                |
| `re.split()`          | Tách câu theo dấu câu + bullet list                    |
| `json`                | Ghi JSONL output                                       |

### Các bước xử lý trên mỗi document

```
description text
    │
    ├─ 1. unicodedata.normalize("NFC")       ← chuẩn hóa dấu tiếng Việt
    ├─ 2. HTML_TAG_RE.sub()                  ← xóa <tag>
    ├─ 3. URL_RE / EMAIL_RE.sub()            ← xóa link, email
    ├─ 4. xóa ký tự điều khiển (Cc)         ← ký tự không in được
    ├─ 5. MULTI_SPACE_RE.sub()               ← gộp khoảng trắng
    │
    ▼  clean text
    │
    ├─ 6. chuẩn hóa bullet list → "\n"      ← "- item" → newline
    ├─ 7. re.split() tách câu               ← theo [.!?;] + khoảng trắng + hoa
    ├─ 8. đoạn >300 ký tự → split("\n")     ← fallback tách thêm
    │
    ▼  danh sách câu thô
    │
    ├─ 9. is_valid_sentence()               ← 20≤len≤600, ≥10 chữ cái, không noise
    └─ 10. is_medical_sentence()            ← chứa từ khóa y tế (MEDICAL_RE)
```

### Bộ lọc y tế

MEDICAL_RE khớp các từ khóa:
`thuốc`, `bệnh`, `viêm`, `ung thư`, `hội chứng`, `điều trị`, `liều`,
`mg`, `mcg`, `ml`, `kháng sinh`, `tiêm`, `uống`, `đau`, `sốt`, `ho`,
`gan`, `thận`, `tim`, `phổi`, `máu`, `vi khuẩn`, v.v.

### Kết quả

| Nguồn          | Docs  | Câu tổng | Câu y tế | Tỉ lệ |
|----------------|-------|----------|----------|-------|
| vinmec         | 1,988 | 81,124   | 66,561   | 82%   |
| thuocbietduoc  | 1,864 | 10,297   | 9,254    | 90%   |
| suckhoedoisong | 371   | 14,015   | 10,704   | 76%   |
| longchau       | 164   | 383      | 348      | 91%   |
| **Tổng**       | 4,387 | **105,819** | **86,867** | **82%** |

### Format output (mỗi dòng JSONL)

```json
{
  "id":         "c446735120c3_0012",
  "doc_id":     "c446735120c3",
  "source":     "thuocbietduoc",
  "sent_idx":   12,
  "text":       "Paracetamol 500mg dùng để giảm đau, hạ sốt.",
  "is_medical": true,
  "doc_fields": {
    "has_active_ingredient": true,
    "has_indication":        true,
    "has_dosage":            true,
    "has_adverse_effect":    false,
    "has_contraindication":  false
  }
}
```

---

## Step 2 — Thiết kế Entity Schema

**Script:** `dataset/schema.py`
**Input:** không cần file (module định nghĩa thuần Python)
**Output:** module Python, import được trong các bước sau

### Công cụ

| Công cụ         | Mục đích                                    |
|-----------------|---------------------------------------------|
| `dataclasses`   | Định nghĩa `EntityType` với type hints      |

### Cấu trúc schema

**9 FLAT entities** (span nguyên tử):

| Type       | Mô tả                           | Ví dụ                            |
|------------|---------------------------------|----------------------------------|
| DRUG_NAME  | Tên thuốc / hoạt chất           | "Paracetamol", "Amoxicillin"     |
| DOSE_NUM   | Con số + đơn vị liều            | "500mg", "250ml", "2 IU"         |
| FREQ       | Tần suất dùng                   | "3 lần/ngày", "mỗi 8 giờ"       |
| ROUTE      | Đường dùng thuốc                | "uống", "tiêm tĩnh mạch", "bôi" |
| DISEASE    | Tên bệnh / hội chứng            | "viêm phổi", "đái tháo đường"   |
| SYMPTOM    | Triệu chứng lâm sàng            | "sốt", "ho khan", "khó thở"     |
| BODY_PART  | Bộ phận / cơ quan cơ thể        | "gan", "phổi", "niệu đạo"       |
| PATHOGEN   | Vi sinh vật gây bệnh            | "Helicobacter pylori", "virus"   |
| LAB_VALUE  | Chỉ số xét nghiệm               | "huyết áp 130/80 mmHg"           |

**5 NESTED entities** (bao chứa flat):

| Type          | Chứa                              | Ví dụ                                  |
|---------------|-----------------------------------|----------------------------------------|
| DRUG          | DRUG_NAME + DOSE_NUM              | "Amoxicillin 500mg"                    |
| DOSAGE        | DOSE_NUM + FREQ + ROUTE           | "500mg uống 3 lần/ngày"               |
| CONDITION     | DISEASE + PATHOGEN + BODY_PART    | "viêm phổi do vi khuẩn"               |
| ADVERSE_EFFECT| SYMPTOM + BODY_PART + DISEASE     | "phản ứng dị ứng ngoài da"             |
| TREATMENT     | DRUG + DOSAGE + CONDITION + DISEASE | "dùng Amoxicillin 500mg điều trị viêm phổi" |

**15 nesting rules** dưới dạng `(outer, inner)` tuple — dùng để validate
khi human annotation.

### Ví dụ nested NER

```
Câu: "Uống Amoxicillin 500mg, 3 lần/ngày để điều trị viêm phổi do vi khuẩn."

FLAT spans:
  [5..16]   DRUG_NAME  "Amoxicillin"
  [17..22]  DOSE_NUM   "500mg"
  [24..34]  FREQ       "3 lần/ngày"
  [47..56]  DISEASE    "viêm phổi"
  [60..69]  PATHOGEN   "vi khuẩn"

NESTED spans:
  [5..22]   DRUG       "Amoxicillin 500mg"
  [17..34]  DOSAGE     "500mg, 3 lần/ngày"
  [47..69]  CONDITION  "viêm phổi do vi khuẩn"
```

---

## Step 3 — Silver Labels (Regex-based Annotation)

**Script:** `dataset/step3_silver_labels.py`
**Input:**
- `data/pharma.db` — lấy `active_ingredient` theo `doc_id`
- `data/dataset/corpus_clean.jsonl` — chỉ xử lý câu `source=thuocbietduoc`

**Output:** `data/dataset/silver_labels.jsonl` — 10,297 câu, 5.7 MB

### Công cụ

| Công cụ / Kỹ thuật       | Mục đích                                           |
|--------------------------|----------------------------------------------------|
| `sqlite3`                | Tra cứu active_ingredient của từng thuốc           |
| `re.compile()` patterns  | Match DOSE_NUM, FREQ, ROUTE, DISEASE, SYMPTOM, PATHOGEN |
| `re.finditer()`          | Tìm tất cả span trong câu                          |
| `re.escape(name)`        | Tìm tên thuốc exact match (case-insensitive)       |

### Logic annotation từng loại entity

```
Từ pharma.db
  active_ingredient: "Amoxicillin; Clavulanic acid"
      │
      ├─ parse_drug_names() → ["Amoxicillin", "Clavulanic acid"]
      │
      ▼
  Với mỗi câu (source=thuocbietduoc):
      │
      ├─ find_drug_name_spans()   ← exact match tên hoạt chất trong câu
      ├─ DOSE_NUM_RE.finditer()   ← r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ml|IU|%...)"
      ├─ FREQ_RE.finditer()       ← r"\d+ lần/ngày | mỗi \d+ giờ | sáng trưa tối..."
      ├─ ROUTE_RE.finditer()      ← r"uống | tiêm tĩnh mạch | bôi | nhỏ mắt..."
      ├─ DISEASE_KEYWORDS.finditer() ← r"viêm \w+ | ung thư | hội chứng | bệnh..."
      ├─ SYMPTOM_KEYWORDS.finditer() ← r"đau | sốt | ho | khó thở | buồn nôn..."
      ├─ PATHOGEN_RE.finditer()   ← Latin tên vi sinh + "vi khuẩn|virus|nấm..."
      │
      ├─ build_nested_drug_spans()
      │     DRUG_NAME + DOSE_NUM liền kề (gap ≤ 5 ký tự) → DRUG span
      │
      ├─ build_dosage_spans()
      │     DOSE_NUM + (ROUTE|FREQ gần nhất trong 10 ký tự) → DOSAGE span
      │
      └─ dedup (start, end, type) → sort theo start
```

### Kết quả

| Metric                     | Giá trị           |
|----------------------------|-------------------|
| Câu đầu vào (thuocbietduoc) | 10,297           |
| Câu có ≥1 entity           | 6,840 (66.4%)    |

**Phân bố entity types:**

| Entity Type | Count  |
|-------------|--------|
| DOSE_NUM    | 6,927  |
| DISEASE     | 5,962  |
| SYMPTOM     | 2,695  |
| ROUTE       | 2,182  |
| FREQ        | 1,837  |
| DOSAGE      | 1,015  |
| PATHOGEN    | 496    |
| DRUG_NAME   | 6      |

> **Lưu ý:** DRUG_NAME thấp (6) vì tên thuốc trong `active_ingredient`
> thường không xuất hiện trong câu `description` một cách trực tiếp.
> Step 4 (LLM) sẽ bổ sung entity này.

### Format output (mỗi dòng JSONL)

```json
{
  "id":       "c446735120c3_0012",
  "doc_id":   "c446735120c3",
  "source":   "thuocbietduoc",
  "text":     "Amoxicillin 500mg uống 3 lần/ngày điều trị viêm phổi.",
  "silver":   true,
  "entities": [
    {"start": 0,  "end": 11, "type": "DRUG_NAME", "text": "Amoxicillin"},
    {"start": 12, "end": 17, "type": "DOSE_NUM",  "text": "500mg"},
    {"start": 18, "end": 23, "type": "ROUTE",     "text": "uống"},
    {"start": 24, "end": 34, "type": "FREQ",      "text": "3 lần/ngày"},
    {"start": 0,  "end": 17, "type": "DRUG",      "text": "Amoxicillin 500mg"},
    {"start": 12, "end": 34, "type": "DOSAGE",    "text": "500mg uống 3 lần/ngày"},
    {"start": 44, "end": 53, "type": "DISEASE",   "text": "viêm phổi"}
  ],
  "doc_fields": {"has_indication": true, "has_dosage": true, ...}
}
```

---

## Step 4 — LLM Pre-annotation

**Script:** `dataset/step4_preannotate.py`
**Input:** `data/dataset/corpus_clean.jsonl` (5,000 câu, chọn theo ưu tiên)
**Output:**
- `data/dataset/llm_annotations.jsonl` — 5,000 câu với entity do LLM gán
- `data/dataset/llm_batch_id.txt` — batch ID để resume nếu bị ngắt

**Yêu cầu:** `ANTHROPIC_API_KEY` phải được set trong môi trường.

### Công cụ

| Công cụ                          | Mục đích                                        |
|----------------------------------|-------------------------------------------------|
| `anthropic` SDK (≥0.40.0)        | Giao tiếp với Anthropic API                     |
| Batches API (`/v1/messages/batches`) | Xử lý async, **50% cost** so với standard API |
| `claude-haiku-4-5`               | Model nhanh + rẻ nhất, đủ cho extraction task  |
| `json`                           | Parse JSON response từ Claude                   |

### Chọn câu

```
corpus_clean.jsonl (105,819 câu)
    │
    ├─ Lọc is_medical=True
    ├─ Ưu tiên nguồn: thuocbietduoc → vinmec → longchau → suckhoedoisong
    └─ Lấy tối đa 5,000 câu
```

### Luồng xử lý Batches API

```
5,000 câu
    │
    ├─ 1. build_user_message(text)       ← prompt NER với SCHEMA_DESC
    ├─ 2. create_batch()                 ← gửi 1 batch = 5,000 requests
    │       └─ lưu batch_id → llm_batch_id.txt
    │
    ├─ 3. wait_for_batch()               ← poll mỗi 30s, hiển thị % tiến độ
    │       └─ chờ đến khi status = "ended" (tối đa 24 giờ)
    │
    └─ 4. collect_results()              ← đọc kết quả từng request
            ├─ parse_entities()
            │     ├─ strip markdown code block (``` ... ```)
            │     ├─ json.loads()
            │     ├─ validate: isinstance int, type in VALID_TYPES
            │     ├─ validate: 0 ≤ start < end ≤ len(text)
            │     └─ dedup (start, end, type)
            └─ ghi JSONL → llm_annotations.jsonl
```

### Prompt gửi cho LLM

```
SYSTEM: "Bạn là chuyên gia gán nhãn thực thể y tế (NER) tiếng Việt.
         Hãy trả về chỉ một JSON object hợp lệ, không có text thêm vào."

USER:   Gán nhãn tất cả thực thể trong câu sau theo schema...
        [SCHEMA_DESC: 14 entity types với mô tả + ví dụ]
        Câu: "..."
        Yêu cầu: {"entities": [{"start":..., "end":..., "type":..., "text":...}]}
```

### Cách resume nếu bị ngắt

```bash
# Batch đã tạo, chờ/collect chưa xong:
python dataset/step4_preannotate.py --resume
# → đọc batch_id từ llm_batch_id.txt, bỏ qua bước tạo batch mới
```

### Format output (mỗi dòng JSONL)

```json
{
  "id":       "a1b2c3d4e5f6_0042",
  "doc_id":   "a1b2c3d4e5f6",
  "source":   "vinmec",
  "text":     "Bệnh nhân sốt cao 39°C, ho khan kéo dài 5 ngày.",
  "llm":      true,
  "model":    "claude-haiku-4-5",
  "entities": [
    {"start": 11, "end": 19, "type": "SYMPTOM",   "text": "sốt cao"},
    {"start": 11, "end": 27, "type": "LAB_VALUE",  "text": "sốt cao 39°C"},
    {"start": 29, "end": 36, "type": "SYMPTOM",   "text": "ho khan"}
  ],
  "doc_fields": {"has_indication": true, ...}
}
```

---

## Tổng kết dataset sau 4 bước

| File                          | Câu     | Nguồn annotation | Dùng cho                     |
|-------------------------------|---------|------------------|------------------------------|
| `corpus_clean.jsonl`          | 105,819 | —                | Pool câu gốc                 |
| `silver_labels.jsonl`         | 10,297  | Regex            | Seed data thuocbietduoc      |
| `llm_annotations.jsonl`       | 5,000   | Claude Haiku     | Pre-label đa nguồn           |

**Coverage entity types sau step 3+4 kết hợp:**

- Step 3 mạnh ở: `DOSE_NUM`, `DISEASE`, `SYMPTOM`, `ROUTE`, `FREQ`, `DOSAGE`
- Step 4 bổ sung: `DRUG_NAME` (LLM tìm được), `BODY_PART`, `LAB_VALUE`,
  `PATHOGEN`, `CONDITION`, `ADVERSE_EFFECT`, `TREATMENT`

---

## Các bước tiếp theo (chưa triển khai)

### Step 5 — Human Annotation

**Công cụ:** Label Studio hoặc Doccano

```bash
# Export sang Label Studio format
python dataset/step5_export_labelstudio.py

# Sau khi human annotate xong, import lại:
python dataset/step5_import_annotations.py
```

Ưu tiên annotate:
1. Câu có silver labels (regex) → review + sửa
2. Câu có LLM labels → review + sửa
3. Câu chưa annotate → annotate mới

### Step 6 — Inter-Annotator Agreement

**Công cụ:** `sklearn.metrics`, tính Cohen's Kappa

- Target: κ ≥ 0.8 trên test set
- Mỗi câu test → ít nhất 2 annotator độc lập

### Step 7 — Model Training

**Công cụ:** `transformers` (HuggingFace), `seqeval`

Các model phù hợp:
- `vinai/phobert-base-v2` — PhoBERT, pretrained tiếng Việt
- `uitnlp/visobert` — ViSoBERT
- `google/rembert` — multilingual, hỗ trợ tốt tiếng Việt

**Architecture cho Nested NER:**
- Span-based (SpanBERT, BERT-MRC) — tốt hơn sequence labeling cho nested
- Hoặc dùng BIO + post-processing để tái tạo nested spans

---

## Lệnh chạy toàn pipeline

```bash
# Phase 0: Crawl (mỗi nguồn chạy riêng, ~vài tiếng)
python main.py --source thuocbietduoc
python main.py --source vinmec
python main.py --source longchau
python main.py --source suckhoedoisong

# Phase 0.6: Export
python main.py --export

# Step 1: Clean corpus
python dataset/step1_clean.py

# Step 2: Schema (không cần chạy, chỉ import)
python dataset/schema.py   # in ra schema để kiểm tra

# Step 3: Silver labels
python dataset/step3_silver_labels.py

# Step 4: LLM pre-annotation (cần API key)
export ANTHROPIC_API_KEY="sk-ant-..."
python dataset/step4_preannotate.py

# Resume nếu bị ngắt giữa chừng
python dataset/step4_preannotate.py --resume
```