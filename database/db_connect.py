import sqlite3
import os
from config.settings import DB_PATH
from utils.logger import get_logger

logger = get_logger("db_connect")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with get_connection() as conn:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    logger.info(f"Database khởi tạo tại: {DB_PATH}")