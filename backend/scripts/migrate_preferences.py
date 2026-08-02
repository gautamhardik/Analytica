"""
Simple migration script to create preferences table used by the portfolio demo.
Run with: python backend/scripts/migrate_preferences.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "brazilian_ecommerce_dw")

import urllib.parse

# Build a sync connection string using pymysql if available
# URL-encode the password to handle special characters (e.g., @, :)
password = urllib.parse.quote_plus(DB_PASSWORD)
conn_str = f"mysql+pymysql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(conn_str)

with engine.begin() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS preferences (
        `key` VARCHAR(128) PRIMARY KEY,
        `value` TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """))

print("preferences table ensured.")