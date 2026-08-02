-- Create denormalized fact_sales table with ALL dimension attributes embedded
-- Column names MATCH dimension table column names so existing queries work unmodified
-- Eliminates ALL JOINs when filters are applied (5-10x speedup)

DROP TABLE IF EXISTS fact_sales_denormalized;

CREATE TABLE fact_sales_denormalized AS
SELECT 
    fs.sales_key, fs.order_id, fs.order_item_id,
    fs.customer_key, fs.product_key, fs.seller_key,
    fs.purchase_date_key,
    fs.quantity, fs.price, fs.freight_value, fs.total_sales_amount,
    fs.etl_created_at, fs.etl_updated_at,
    COALESCE(dc.customer_unique_id, 'unknown') AS customer_unique_id,
    COALESCE(dcs.segment, 'unknown') AS segment,
    COALESCE(dg.state_code, 'unknown') AS state_code,
    COALESCE(dp.product_category_name_english, 'unknown') AS product_category_name_english,
    COALESCE(ds.seller_id, 'unknown') AS seller_id,
    COALESCE(dgs.city_name, 'unknown') AS seller_city,
    COALESCE(dgs.state_code, 'unknown') AS seller_state,
    dd.month_year, dd.year_number, dd.month_number
FROM fact_sales fs
LEFT JOIN dim_customer_segment dcs ON fs.customer_key = dcs.customer_key
LEFT JOIN dim_customer dc ON fs.customer_key = dc.customer_key
LEFT JOIN dim_geography dg ON dc.geography_key = dg.geography_key
LEFT JOIN dim_product dp ON fs.product_key = dp.product_key
LEFT JOIN dim_seller ds ON fs.seller_key = ds.seller_key
LEFT JOIN dim_geography dgs ON ds.geography_key = dgs.geography_key
LEFT JOIN dim_date dd ON fs.purchase_date_key = dd.date_key;

CREATE INDEX IF NOT EXISTS idx_fsd_segment ON fact_sales_denormalized(segment);
CREATE INDEX IF NOT EXISTS idx_fsd_state_code ON fact_sales_denormalized(state_code);
CREATE INDEX IF NOT EXISTS idx_fsd_product_category ON fact_sales_denormalized(product_category_name_english);
CREATE INDEX IF NOT EXISTS idx_fsd_month_year ON fact_sales_denormalized(month_year);
CREATE INDEX IF NOT EXISTS idx_fsd_year_month ON fact_sales_denormalized(year_number, month_number);
CREATE INDEX IF NOT EXISTS idx_fsd_segment_month ON fact_sales_denormalized(segment, month_year);
CREATE INDEX IF NOT EXISTS idx_fsd_state_month ON fact_sales_denormalized(state_code, month_year);
CREATE INDEX IF NOT EXISTS idx_fsd_cat_month ON fact_sales_denormalized(product_category_name_english, month_year);
CREATE INDEX IF NOT EXISTS idx_fsd_customer_key ON fact_sales_denormalized(customer_key);
CREATE INDEX IF NOT EXISTS idx_fsd_order_id ON fact_sales_denormalized(order_id);
CREATE INDEX IF NOT EXISTS idx_fsd_customer_uid ON fact_sales_denormalized(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_fsd_seller_id ON fact_sales_denormalized(seller_id);

SELECT 'fact_sales_denormalized created with ' || COUNT(*) || ' rows' AS status FROM fact_sales_denormalized;
