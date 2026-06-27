---
name: run-crawldata
description: run, start, build, test, smoke, screenshot, verify CrawlData pharma scraper — CLI crawl, stats, export, label-tool server
---

# CrawlData — Pharma Scraper

Vietnamese pharmaceutical data scraper (nhathuoclongchau, thuocbietduoc, vinmec, suckhoedoisong).
Driven as a CLI tool (`main.py`). Outputs SQLite DB + JSON/CSV exports.
Secondary component: Flask annotation tool (`run_label_tool.py`).

Smoke harness: `.claude/skills/run-crawldata/smoke.sh`

---

## Prerequisites

```bash
pip3 install python-dotenv fake-useragent tqdm lxml selenium webdriver-manager
# All other deps (requests, bs4, pandas, SQLAlchemy, flask) were already present
```

No `.env` file required — all settings have defaults in `config/settings.py`.

---

## Run: agent path (smoke)

Run from `CrawlData/`:

```bash
bash .claude/skills/run-crawldata/smoke.sh
```

Covers: `--help`, `--stats`, `--export`, artefact presence, label-tool HTTP round-trip.
Exit 0 = all pass.

---

## Run: individual commands

All commands run from `CrawlData/`:

```bash
# DB stats (no network)
python3 main.py --stats

# Export processed CSV + JSON (no network)
python3 main.py --export
# → data/processed/merged/all_dedup.{json,csv}
# → data/processed/by_source/<source>_clean.{json,csv}

# Crawl a single source (needs network + chromedriver for longchau)
python3 main.py --source thuocbietduoc

# Crawl all enabled sources
python3 main.py
```

---

## Run: label tool (annotation web UI)

```bash
python3 run_label_tool.py
# → http://localhost:5000
```

Loads processed records from `data/processed/` into an in-memory cache.
`FileNotFoundError` on startup means `--export` has not been run yet.

To verify programmatically:

```python
from dataset.label_tool.app import app, _get_sources
import threading, time, urllib.request

t = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5002, debug=False, use_reloader=False), daemon=True)
t.start(); time.sleep(2)
print(urllib.request.urlopen('http://127.0.0.1:5002/api/stats').read().decode())
```

---

## Direct invocation (no scraping)

To call internal code without crawling:

```python
from database.db_connect import init_db
from database.medicine_repository import MedicineRepository
init_db()
repo = MedicineRepository()
records = repo.get_all(source="longchau")   # or None for all
print(repo.count_by_source())
```

DB lives at `data/pharma.db` (4,517 records across 4 sources as of 2026-06-27).

---

## Gotchas

- **`from dotenv import load_dotenv` fails at import** — `python-dotenv` is not in the system Python. Run `pip3 install python-dotenv` first. Everything else in `requirements.txt` was already installed system-wide.
- **longchau spider requires Chrome/chromedriver** — uses Selenium headless. On a headless machine, install `chromium-browser` and let `webdriver-manager` handle the driver. `--headless=new` and `--no-sandbox` flags are already set.
- **Label tool needs export data first** — `_get_sources()` reads `data/processed/` via `load_source_records()`. If the directory is empty or missing, you get `FileNotFoundError`. Run `python3 main.py --export` first.
- **Sources `longchau` and others are `"enabled": True`** in `config/urls.py` — running `python3 main.py` (no flags) will attempt to crawl all of them over the network.
- **`--stats` and `--export` are safe offline** — they only touch the local SQLite DB and filesystem.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'dotenv'` | `pip3 install python-dotenv` |
| `FileNotFoundError` on label tool startup | Run `python3 main.py --export` first |
| `WebDriverException: no such file chromedriver` | `pip3 install webdriver-manager` (already in requirements) — it auto-downloads |
| DB appears empty after `--stats` | `data/pharma.db` missing; run a crawl or restore from backup |
