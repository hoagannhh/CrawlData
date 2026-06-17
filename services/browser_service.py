import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.logger import get_logger

logger = get_logger("browser_service")


class BrowserService:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver   = None

    def _build_driver(self) -> webdriver.Chrome:
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=vi-VN")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        # Không dùng webdriver-manager, dùng Chrome có sẵn trong PATH
        return webdriver.Chrome(options=options)

    def start(self):
        if self.driver is None:
            logger.info("Khởi động browser...")
            self.driver = self._build_driver()

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Đã đóng browser.")

    def get_soup(self, url: str, wait_selector: str = None,
                 wait_timeout: int = 10) -> BeautifulSoup:
        self.start()
        logger.debug(f"Browser GET: {url}")
        self.driver.get(url)
        if wait_selector:
            try:
                WebDriverWait(self.driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except Exception:
                logger.warning(f"Timeout chờ '{wait_selector}' tại {url}")
        time.sleep(1.5)
        return BeautifulSoup(self.driver.page_source, "lxml")

    def scroll_to_bottom(self, pause: float = 1.5):
        self.start()
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.quit()