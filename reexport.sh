#!/bin/bash
# Chờ LongChau xong rồi re-export data sạch
cd /home/hoanganh/workspace/CrawlData
source venv/bin/activate

echo "Chờ LongChau spider kết thúc..."
while ps aux | grep -q "[p]ython main.py --source longchau"; do
    sleep 10
done

echo "LongChau xong! Bắt đầu re-export..."
python3 - << 'PYEOF'
import json, re, os, sys
sys.path.insert(0, '.')
from database.db_connect import init_db
from database.medicine_repository import MedicineRepository
from utils.helpers import clean_text, dedup_records
from utils.file_handler import save_json, save_csv
from collections import Counter

init_db()
repo = MedicineRepository()
all_records = repo.get_all()
print(f"DB records: {len(all_records)}")

# Clean vinmec noise
for r in all_records:
    if r.get('source') == 'vinmec':
        desc = r.get('description', '')
        desc = re.sub(r'^[☰\s]*Mục lục\s*', '', desc)
        desc = re.sub(r'^Bài viết được tư vấn chuyên môn bởi[^.]+\.\s*', '', desc)
        r['description'] = desc.strip()

# ThuocBietDuoc: rebuild description
for r in all_records:
    if r.get('source') == 'thuocbietduoc' and not r.get('description','').strip():
        parts = [r.get(f,'').strip() for f in ('indication','dosage','adverse_effect','contraindication','active_ingredient') if r.get(f,'').strip()]
        r['description'] = ' '.join(parts)

# Lọc rác
all_records = [r for r in all_records if len(r.get('description','')) >= 100 and 'cơ quan ngôn luận' not in r.get('description','')[:200]]

# Dedup theo URL
deduped = dedup_records(all_records, key='url')
src_count = Counter(r['source'] for r in deduped)

print(f"Sau dedup: {len(deduped)} records")
for src, cnt in sorted(src_count.items()):
    print(f"  {src}: {cnt}")

os.makedirs('data/processed/merged', exist_ok=True)
os.makedirs('data/processed/by_source', exist_ok=True)
save_json(deduped, 'data/processed/merged/all_dedup.json')
save_csv(deduped, 'data/processed/merged/all_dedup.csv')
for src in src_count:
    recs = [r for r in deduped if r['source']==src]
    save_json(recs, f'data/processed/by_source/{src}_clean.json')
    save_csv(recs, f'data/processed/by_source/{src}_clean.csv')
print("Export xong.")
PYEOF
