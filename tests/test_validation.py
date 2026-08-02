"""
Unit Tests for ETL Validation Module
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import polars as pl
from ETL.validation import (
    validate_grain_uniqueness, validate_business_rules, ValidationError
)

class TestValidationModule(unittest.TestCase):
    def test_validate_grain_uniqueness_pass(self):
        df = pl.DataFrame({
            "order_id": ["o1", "o2"],
            "order_item_id": [1, 1]
        })
        try:
            validate_grain_uniqueness(df, ["order_id", "order_item_id"], "test")
        except ValidationError:
            self.fail("Grain validation unexpectedly raised ValidationError!")

    def test_validate_grain_uniqueness_fail(self):
        df = pl.DataFrame({
            "order_id": ["o1", "o1"],
            "order_item_id": [1, 1]
        })
        with self.assertRaises(ValidationError):
            validate_grain_uniqueness(df, ["order_id", "order_item_id"], "test")

    def test_validate_business_rules_fail(self):
        df = pl.DataFrame({
            "price": [-10.0],
            "freight_value": [5.0],
            "total_sales_amount": [-5.0],
            "quantity": [1]
        })
        with self.assertRaises(ValidationError):
            validate_business_rules(df)

if __name__ == "__main__":
    unittest.main()
