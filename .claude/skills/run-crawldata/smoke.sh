#!/usr/bin/env bash
# smoke.sh — run from CrawlData/ root; exit 0 = all checks passed
set -euo pipefail
cd "$(dirname "$0")/../../.."   # land in CrawlData/

echo "=== 1. help ==="
python3 main.py --help

echo ""
echo "=== 2. --stats ==="
python3 main.py --stats

echo ""
echo "=== 3. --export ==="
python3 main.py --export

echo ""
echo "=== 4. verify export artefacts ==="
for f in \
  data/processed/merged/all_dedup.json \
  data/processed/merged/all_dedup.csv \
  data/processed/by_source/longchau_clean.json \
  data/processed/by_source/thuocbietduoc_clean.json \
  data/processed/by_source/vinmec_clean.json \
  data/processed/by_source/suckhoedoisong_clean.json; do
  [ -s "$f" ] && echo "  OK  $f" || { echo "  MISSING $f"; exit 1; }
done

echo ""
echo "=== 5. label tool server ==="
python3 -c "
from dataset.label_tool.app import app, _get_sources
import threading, time, urllib.request, sys

def run():
    app.run(host='127.0.0.1', port=5002, debug=False, use_reloader=False)

t = threading.Thread(target=run, daemon=True)
t.start()
time.sleep(2)

r = urllib.request.urlopen('http://127.0.0.1:5002/api/stats')
body = r.read().decode()
assert '\"total\"' in body, f'unexpected /api/stats response: {body}'
print(f'  /api/stats: {body[:80]}')

r2 = urllib.request.urlopen('http://127.0.0.1:5002/')
assert len(r2.read()) > 100, 'root returned empty body'
print('  / : OK')
"

echo ""
echo "=== SMOKE PASSED ==="
