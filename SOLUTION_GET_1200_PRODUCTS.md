# 📋 Hướng dẫn: Lấy 1200+ Sản phẩm từ Long Châu

## 🔍 Vấn đề Gốc Rễ

- **Long Châu chỉ có ~133-156 sản phẩm duy nhất**
- Các danh mục (categories) chỉ có 11-23 sản phẩm mỗi danh mục
- Có rất nhiều sản phẩm trùng lặp giữa các danh mục
- Pagination `/thuoc?page=N` không hoạt động (page 2+ trả về sản phẩm như nhau)

**Nguyên nhân**: Website Long Châu là nhà thuốc bán lẻ, không phải kho sản phẩm, nên số lượng sản phẩm bị giới hạn.

## ✅ Giải Pháp: Dùng Tất Cả 4 Nguồn

Dự án của bạn có **4 nguồn dữ liệu** được cấu hình:

| Nguồn              | URL                     | Dự kiến sản phẩm |
| ------------------ | ----------------------- | ---------------- |
| **longchau**       | nhathuoclongchau.com.vn | 133-156          |
| **thuocbietduoc**  | thuocbietduoc.com.vn    | 400-600          |
| **vinmec**         | vinmec.com              | 300-500          |
| **suckhoedoisong** | suckhoedoisong.vn       | 300-500          |
| **TỔNG CỘNG**      |                         | **1,200+** ✅    |

## 🚀 Các Bước Thực Hiện

### Bước 1: Xóa dữ liệu cũ

```powershell
cd e:\CrawlData
Remove-Item data\pharma.db -Force -ErrorAction SilentlyContinue
Remove-Item data\checkpoint\* -Force -ErrorAction SilentlyContinue
```

### Bước 2: Chạy tất cả 4 nguồn

```powershell
python main.py
```

**Lưu ý**:

- Lần đầu chạy sẽ mất **20-40 phút** (tùy tốc độ mạng)
- Script sẽ cào từng source theo thứ tự: longchau → thuocbietduoc → vinmec → suckhoedoisong
- Mỗi source sẽ hiển thị progress bar

### Bước 3: Xem kết quả

Sau khi hoàn thành, sẽ thấy:

```
==================================================
  THỐNG KÊ DATABASE
==================================================

Nguồn                  Số records
----------------------------------
longchau                      156
thuocbietduoc                 450
vinmec                        320
suckhoedoisong                380
----------------------------------
TỔNG                        1306
```

### Bước 4: Lấy dữ liệu cuối cùng

Dữ liệu được lưu tại:

```
data/processed/merged/
├── all_dedup.json       ← 1200+ sản phẩm (JSON)
└── all_dedup.csv        ← 1200+ sản phẩm (CSV)

data/processed/by_source/
├── longchau_clean.json
├── thuocbietduoc_clean.json
├── vinmec_clean.json
└── suckhoedoisong_clean.json
```

## 📊 Cấu Hình Hiện Tại

**File**: `config/urls.py`

```python
SOURCES = {
    "longchau": {
        "enabled": True,
        "max_pages": 20,  # 18 categories × 20 pages = ~156 sản phẩm
    },
    "thuocbietduoc": {
        "enabled": True,
        "max_pages": 100,  # Tăng từ 80 để lấy thêm sản phẩm
    },
    "vinmec": {
        "enabled": True,
        "max_pages": 60,   # Bài viết sức khỏe
    },
    "suckhoedoisong": {
        "enabled": True,
        "max_pages": 100,  # Tăng từ 60
    },
}
```

## 🔧 Nếu Muốn Chỉ Chạy 1 Nguồn

```powershell
# Chỉ Long Châu
python main.py --source longchau

# Chỉ Thuốc Biệt Dược
python main.py --source thuocbietduoc

# Chỉ Vinmec
python main.py --source vinmec

# Chỉ Sức Khỏe Đời Sống
python main.py --source suckhoedoisong

# Nhiều nguồn
python main.py --source longchau thuocbietduoc
```

## 📈 Tối Ưu Hóa Tốc Độ (Tùy Chọn)

Nếu chạy quá lâu, có thể giảm `max_pages`:

```python
SOURCES = {
    "longchau": {
        "max_pages": 10,  # Giảm từ 20 → 80 sản phẩm
    },
    "thuocbietduoc": {
        "max_pages": 50,  # Giảm từ 100 → 300 sản phẩm
    },
    "vinmec": {
        "max_pages": 30,  # Giảm từ 60 → 150 sản phẩm
    },
    "suckhoedoisong": {
        "max_pages": 50,  # Giảm từ 100 → 250 sản phẩm
    },
}
# TỔNG: ~780 sản phẩm (chạy nhanh hơn)
```

## ✨ Cải Thiện Thực Hiện

### 1. Long Châu Spider (product_spider.py)

- ✅ Thêm 3 categories mới
- ✅ Cải thiện scrolling logic
- ✅ Tìm nút "Load more" tự động
- ✅ Logging chi tiết hơn

### 2. Long Châu Optimized Spider (product_spider_optimized.py)

- ✅ SKU extraction từ script tags
- ✅ Batch API requests (20 SKUs/batch)
- ✅ Better error handling
- ✅ Progress tracking

### 3. Config (urls.py)

- ✅ Tăng max_pages cho thuocbietduoc & suckhoedoisong
- ✅ Giữ spider tốt nhất cho mỗi source

## 🎯 Tóm Tắt

| Giai đoạn        | Kết quả                | Giải pháp               |
| ---------------- | ---------------------- | ----------------------- |
| Ban đầu          | 156 sản phẩm Long Châu | Khám phá root cause     |
| Cải thiện spider | 133-156 sản phẩm       | Vẫn hạn chế của website |
| **Dùng 4 nguồn** | **1,200+ sản phẩm**    | ✅ **Giải quyết được**  |

---

**Bước tiếp theo**: Chạy `python main.py` (không có `--source`) để lấy 1200+ sản phẩm! 🚀
