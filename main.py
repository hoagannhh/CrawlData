"""
pharma_scraper — entry point
Cách dùng:
    python main.py                        # chạy tất cả nguồn
    python main.py --source longchau      # chỉ chạy 1 nguồn
    python main.py --source longchau vinmec   # chạy nhiều nguồn
    python main.py --stats                # xem thống kê DB
    python main.py --export               # xuất CSV + JSON
"""

import argparse
import importlib
import os
import sys

from config.urls import SOURCES
from config.settings import RAW_DIR, PROCESSED_DIR
from database.db_connect import init_db
from database.medicine_repository import MedicineRepository
from utils.file_handler import save_json, save_csv, load_all_checkpoints
from utils.helpers import dedup_records
from utils.logger import get_logger

logger = get_logger("main")


# ── Load spider động theo config ─────────────────────────────────────────────

def load_spider(source_name: str):
    cfg = SOURCES.get(source_name)
    if not cfg:
        raise ValueError(f"Không tìm thấy nguồn: {source_name}")
    module_path, class_name = cfg["spider"].rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


# ── Chạy 1 nguồn ─────────────────────────────────────────────────────────────

def run_source(source_name: str, repo: MedicineRepository) -> int:
    cfg = SOURCES[source_name]
    if not cfg.get("enabled", False):
        logger.info(f"[{source_name}] Đã tắt, bỏ qua.")
        return 0

    logger.info(f"{'='*50}")
    logger.info(f"Bắt đầu nguồn: {source_name}")
    logger.info(f"{'='*50}")

    spider  = load_spider(source_name)
    results = spider.run(max_pages=cfg.get("max_pages", 50))

    if not results:
        logger.warning(f"[{source_name}] Không cào được dữ liệu nào.")
        return 0

    # Lưu raw JSON theo nguồn
    raw_path = os.path.join(RAW_DIR, source_name, "data.json")
    os.makedirs(os.path.dirname(raw_path), exist_ok=True)
    save_json(results, raw_path)

    # Lưu vào DB
    inserted = repo.insert_many(results)
    logger.info(f"[{source_name}] Hoàn thành: {len(results)} cào | {inserted} chèn DB")
    return inserted


# ── Xuất processed data ───────────────────────────────────────────────────────

def export_data(repo: MedicineRepository):
    logger.info("Xuất processed data...")
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    all_records = repo.get_all()
    if not all_records:
        logger.warning("DB rỗng, không có gì để xuất.")
        return

    # Dedup
    deduped = dedup_records(all_records, key="description")
    logger.info(f"Tổng: {len(all_records)} | Sau dedup: {len(deduped)}")

    # Lưu merged
    merged_dir = os.path.join(PROCESSED_DIR, "merged")
    os.makedirs(merged_dir, exist_ok=True)
    save_json(deduped, os.path.join(merged_dir, "all_dedup.json"))
    save_csv(deduped,  os.path.join(merged_dir, "all_dedup.csv"))

    # Lưu theo từng nguồn
    by_source_dir = os.path.join(PROCESSED_DIR, "by_source")
    os.makedirs(by_source_dir, exist_ok=True)
    sources_present = set(r["source"] for r in deduped)
    for src in sources_present:
        src_records = [r for r in deduped if r["source"] == src]
        save_json(src_records, os.path.join(by_source_dir, f"{src}_clean.json"))
        save_csv(src_records,  os.path.join(by_source_dir, f"{src}_clean.csv"))
        logger.info(f"  {src}: {len(src_records)} records")

    logger.info(f"Export hoàn thành → {PROCESSED_DIR}")


# ── In thống kê ───────────────────────────────────────────────────────────────

def print_stats(repo: MedicineRepository):
    print("\n" + "="*50)
    print("  THỐNG KÊ DATABASE")
    print("="*50)

    by_source = repo.count_by_source()
    total = sum(by_source.values())
    print(f"\n{'Nguồn':<20} {'Số records':>12}")
    print("-"*34)
    for src, cnt in by_source.items():
        print(f"{src:<20} {cnt:>12,}")
    print("-"*34)
    print(f"{'TỔNG':<20} {total:>12,}")

    print("\nChất lượng field (records có nội dung):")
    field_stats = repo.get_non_empty_fields()
    for field, cnt in field_stats.items():
        pct = (cnt / total * 100) if total else 0
        bar = "█" * int(pct / 5)
        print(f"  {field:<22} {cnt:>6,} ({pct:5.1f}%)  {bar}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Pharma Scraper — cào dữ liệu y tế tiếng Việt")
    parser.add_argument("--source", nargs="+",
                        choices=list(SOURCES.keys()),
                        help="Chọn nguồn cụ thể (mặc định: tất cả)")
    parser.add_argument("--stats",  action="store_true", help="Xem thống kê DB")
    parser.add_argument("--export", action="store_true", help="Xuất CSV + JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    # Khởi tạo DB
    init_db()
    repo = MedicineRepository()

    # Chỉ xem thống kê
    if args.stats:
        print_stats(repo)
        return

    # Chỉ xuất data
    if args.export:
        export_data(repo)
        return

    # Chọn nguồn cần chạy
    sources_to_run = args.source if args.source else [
        s for s, cfg in SOURCES.items() if cfg.get("enabled", False)
    ]

    logger.info(f"Các nguồn sẽ chạy: {sources_to_run}")
    total_inserted = 0

    for source_name in sources_to_run:
        try:
            inserted = run_source(source_name, repo)
            total_inserted += inserted
        except Exception as e:
            logger.error(f"[{source_name}] Lỗi nghiêm trọng: {e}", exc_info=True)

    # Tự động export sau khi cào xong
    export_data(repo)
    print_stats(repo)

    logger.info(f"Tổng đã chèn DB: {total_inserted}")


if __name__ == "__main__":
    main()