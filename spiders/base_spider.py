from abc import ABC, abstractmethod
from tqdm import tqdm
from config.settings import CHECKPOINT_EVERY
from services.request_service import RequestService
from utils.file_handler import save_checkpoint, load_scraped_urls, save_scraped_urls
from utils.logger import get_logger


class BaseSpider(ABC):
    source_name: str = "base"

    def __init__(self):
        self.request = RequestService()
        self.logger  = get_logger(f"spider.{self.source_name}")

    @abstractmethod
    def get_list_urls(self, max_pages: int) -> list[str]:
        pass

    @abstractmethod
    def parse_item(self, url: str) -> dict | None:
        pass

    def run(self, max_pages: int = 50) -> list[dict]:
        self.logger.info(f"[{self.source_name}] Bắt đầu cào (max_pages={max_pages})")

        scraped_urls = load_scraped_urls(self.source_name)
        urls         = self.get_list_urls(max_pages)
        new_urls     = [u for u in urls if u not in scraped_urls]

        self.logger.info(
            f"[{self.source_name}] Tổng {len(urls)} URL | "
            f"Mới: {len(new_urls)} | Đã cào: {len(scraped_urls)}"
        )

        results, batch = [], []

        for url in tqdm(new_urls, desc=self.source_name):
            try:
                item = self.parse_item(url)
                if item:
                    results.append(item)
                    batch.append(item)
                    scraped_urls.add(url)
            except Exception as e:
                self.logger.error(f"Lỗi [{url}]: {e}")

            if len(batch) >= CHECKPOINT_EVERY:
                batch_num = len(results) // CHECKPOINT_EVERY
                save_checkpoint(batch, self.source_name, batch_num)
                save_scraped_urls(self.source_name, scraped_urls)
                self.logger.info(f"Checkpoint {batch_num}: {len(results)} records")
                batch = []

        if batch:
            batch_num = (len(results) // CHECKPOINT_EVERY) + 1
            save_checkpoint(batch, self.source_name, batch_num)
            save_scraped_urls(self.source_name, scraped_urls)

        self.logger.info(f"[{self.source_name}] Hoàn thành: {len(results)} records")
        return results