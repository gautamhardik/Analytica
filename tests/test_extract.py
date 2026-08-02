"""
Unit Tests for ETL Data Extraction Module
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import polars as pl
from ETL.extract import (
    load_orders, load_order_items, load_customers, load_products
)

class TestExtractModule(unittest.TestCase):
    def test_load_orders(self):
        df = load_orders()
        self.assertIsInstance(df, pl.DataFrame)
        self.assertGreater(df.height, 0)
        self.assertIn("order_id", df.columns)

    def test_load_order_items(self):
        df = load_order_items()
        self.assertIsInstance(df, pl.DataFrame)
        self.assertGreater(df.height, 0)
        self.assertIn("order_item_id", df.columns)

    def test_load_customers(self):
        df = load_customers()
        self.assertIsInstance(df, pl.DataFrame)
        self.assertGreater(df.height, 0)
        self.assertIn("customer_id", df.columns)

if __name__ == "__main__":
    unittest.main()
