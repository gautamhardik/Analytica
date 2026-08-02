"""
Centralized Configuration & Settings Module
Enterprise settings, environment loading, directory resolution, and logger factory.
"""

import os
import sys
import urllib.parse
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Resolve project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Directory Structure
RAW_DATA_DIR = PROJECT_ROOT / "DATA" / "raw"
LOG_DIR = PROJECT_ROOT / "DOCS" / "logs"
OUTPUT_DIR = PROJECT_ROOT / "NOTEBOOKS"
REPORT_DIR = PROJECT_ROOT / "DOCS" / "reports"
SQL_DIR = PROJECT_ROOT / "SQL"

# Ensure output directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

# Application Constants
APP_NAME = "Brazilian E-Commerce Data Warehouse ETL"
APP_VERSION = "1.0.0"
BATCH_SIZE = 10000
CHUNK_SIZE = 5000

# Database Credentials
DB_USER = os.getenv("DB_USER", "root")
DB_RAW_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PASSWORD = urllib.parse.quote_plus(DB_RAW_PASSWORD)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "brazilian_ecommerce_dw")

# SQLAlchemy Connection String
DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_logger(name: str = "ETL") -> logging.Logger:
    """Logger factory returning configured logger instance with stream handler."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

def get_db_engine():
    """Create and return a SQLAlchemy engine instance."""
    return create_engine(DATABASE_URI)
