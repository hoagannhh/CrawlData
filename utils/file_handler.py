import json
import os
import pandas as pd
from utils.logger import get_logger

logger = get_logger("file_handler")


def save_json(data: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(data)} records → {path}")


def load_json(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_csv(data: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(data)} records → {path}")


def save_checkpoint(data: list[dict], source: str, batch: int) -> None:
    from config.settings import CHECKPOINT_DIR
    path = os.path.join(CHECKPOINT_DIR, f"{source}_batch_{batch:04d}.json")
    save_json(data, path)


def load_all_checkpoints(source: str) -> list[dict]:
    from config.settings import CHECKPOINT_DIR
    all_data = []
    for fname in sorted(os.listdir(CHECKPOINT_DIR)):
        if fname.startswith(source) and fname.endswith(".json"):
            path = os.path.join(CHECKPOINT_DIR, fname)
            all_data.extend(load_json(path))
    return all_data


def load_scraped_urls(source: str) -> set:
    """Load danh sách URL đã cào để tránh cào lại."""
    from config.settings import CHECKPOINT_DIR
    path = os.path.join(CHECKPOINT_DIR, f"{source}_scraped_urls.json")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_scraped_urls(source: str, urls: set) -> None:
    from config.settings import CHECKPOINT_DIR
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    path = os.path.join(CHECKPOINT_DIR, f"{source}_scraped_urls.json")
    with open(path, "w") as f:
        json.dump(list(urls), f)