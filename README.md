# Pharma Scraper 🏥

Công cụ cào dữ liệu y tế / dược phẩm tiếng Việt từ nhiều nguồn,  
phục vụ xây dựng dataset **Nested NER** tiếng Việt.

## Nguồn dữ liệu

| Nguồn                   | Loại nội dung      | Entity chính                    |
| ----------------------- | ------------------ | ------------------------------- |
| nhathuoclongchau.com.vn | Tờ hướng dẫn thuốc | DRUG, ACTIVE_INGREDIENT, DOSAGE |
| thuocbietduoc.com.vn    | Thông tin dược học | DRUG_CLASS, CONTRAINDICATION    |
| vinmec.com              | Bài viết bệnh lý   | DISEASE, SYMPTOM, BODY_PART     |
| suckhoedoisong.vn       | Báo chí y tế       | SYMPTOM, DISEASE, TREATMENT     |

## Cài đặt

```bash
pip install -r requirements.txt
cp .env.example .env   # chỉnh sửa nếu cần
```

## Cách dùng

```bash
# Chạy tất cả nguồn
python main.py

# Chỉ chạy 1 nguồn
python main.py --source longchau

# Chạy nhiều nguồn
python main.py --source longchau vinmec

# Xem thống kê DB
python main.py --stats

# Xuất CSV + JSON
python main.py --export
```

## Cấu trúc output

```
data/
├── raw/               # JSON thô theo từng nguồn
├── processed/
│   ├── by_source/     # CSV + JSON đã clean theo nguồn
│   └── merged/        # Tổng hợp tất cả, đã dedup
├── checkpoint/        # Lưu tiến độ, resume nếu bị dừng
└── logs/              # Log file
```

## Cấu trúc record

```json
{
  "source": "longchau",
  "url": "https://...",
  "name": "Augmentin 625mg",
  "active_ingredient": "Amoxicillin 500mg + Acid clavulanic 125mg",
  "drug_class": "Kháng sinh nhóm beta-lactam",
  "indication": "Điều trị viêm phổi, viêm xoang...",
  "dosage": "Người lớn: 1 viên x 2 lần/ngày...",
  "adverse_effect": "Buồn nôn, tiêu chảy, phát ban...",
  "contraindication": "Dị ứng penicillin...",
  "description": "..."
}
```

## Thêm nguồn mới

1. Tạo thư mục `spiders/ten_trang/` và `parsers/ten_trang/`
2. Viết spider kế thừa `BaseSpider`, implement `get_list_urls()` và `parse_item()`
3. Viết parser kế thừa `BaseParser`, implement `parse()`
4. Thêm config vào `config/urls.py`
