import os
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR        = os.path.join(BASE_DIR, "data")
RAW_DIR         = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR   = os.path.join(DATA_DIR, "processed")
LOG_DIR         = os.path.join(DATA_DIR, "logs")
CHECKPOINT_DIR  = os.path.join(DATA_DIR, "checkpoint")

# Request settings
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", 1.0))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", 3.0))
MAX_RETRIES       = int(os.getenv("MAX_RETRIES", 3))
TIMEOUT           = int(os.getenv("TIMEOUT", 15))

# Database
DB_PATH = os.path.join(BASE_DIR, os.getenv("DB_PATH", "data/pharma.db"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE  = os.path.join(LOG_DIR, "crawler.log")

# Checkpoint — lưu sau mỗi N records
CHECKPOINT_EVERY = 50