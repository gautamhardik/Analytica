"""
Unit Tests for ETL Transformation Module
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import polars as pl
from ETL.transform import (
    transform_geography, transform_product, aggregate_payments
)

class TestTransformModule(unittest.TestCase):
    def test_transform_geography_aggregation(self):
        sample_geo = pl.DataFrame({
            "geolocation_zip_code_prefix": [1001, 1001, 1002],
            "geolocation_city": ["sao paulo", "sao paulo", "rio"],
            "geolocation_state": ["SP", "SP", "RJ"],
            "geolocation_lat": [-23.5, -23.6, -22.9],
            "geolocation_lng": [-46.6, -46.7, -43.1]
        })
        res = transform_geography(sample_geo)
        self.assertEqual(res.height, 2)
        self.assertIn("zip_code_prefix", res.columns)
        self.assertIn("city_name", res.columns)

    def test_transform_product_volume(self):
        sample_prod = pl.DataFrame({
            "product_id": ["p1"],
            "product_category_name": ["perfumaria"],
            "product_name_lenght": [10],
            "product_description_lenght": [50],
            "product_photos_qty": [2],
            "product_weight_g": [500],
            "product_length_cm": [10],
            "product_height_cm": [5],
            "product_width_cm": [4]
        })
        sample_cat = pl.DataFrame({
            "product_category_name": ["perfumaria"],
            "product_category_name_english": ["perfumery"]
        })
        res = transform_product(sample_prod, sample_cat)
        self.assertEqual(res["product_volume_cm3"][0], 200) # 10 * 5 * 4
        self.assertEqual(res["product_category_name_english"][0], "perfumery")

    def test_aggregate_payments(self):
        sample_pmt = pl.DataFrame({
            "order_id": ["o1", "o1"],
            "payment_sequential": [1, 2],
            "payment_type": ["credit_card", "voucher"],
            "payment_installments": [2, 1],
            "payment_value": [50.0, 25.0]
        })
        res = aggregate_payments(sample_pmt)
        self.assertEqual(res.height, 1)
        self.assertEqual(res["payment_total"][0], 75.0)
        self.assertEqual(res["payment_installments_max"][0], 2)

if __name__ == "__main__":
    unittest.main()
