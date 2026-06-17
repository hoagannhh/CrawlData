import time
import random
import requests
from bs4 import BeautifulSoup
from config.headers import get_headers
from config.settings import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, TIMEOUT
from services.retry_service import retry
from utils.logger import get_logger

logger = get_logger("request_service")


class RequestService:
    def __init__(self):
        self.session = requests.Session()

    def _random_delay(self):
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    @retry(max_retries=3, delay=2.0)
    def get(self, url: str, referer: str = None) -> requests.Response:
        self.session.headers.update(get_headers(referer))
        response = self.session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        self._random_delay()
        return response

    def get_soup(self, url: str, referer: str = None) -> BeautifulSoup:
        response = self.get(url, referer)
        return BeautifulSoup(response.text, "lxml")

    def get_text(self, url: str, referer: str = None) -> str:
        response = self.get(url, referer)
        return response.text