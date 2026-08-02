-- Indexes for fact_sales JOIN columns
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_key ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_purchase_date_key ON fact_sales(purchase_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_order_id ON fact_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product_key ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_seller_key ON fact_sales(seller_key);

-- Indexes for dimension table JOIN and filter columns
CREATE INDEX IF NOT EXISTS idx_dim_customer_segment_customer_key ON dim_customer_segment(customer_key);
CREATE INDEX IF NOT EXISTS idx_dim_customer_segment_segment ON dim_customer_segment(segment);

CREATE INDEX IF NOT EXISTS idx_dim_customer_geography_key ON dim_customer(geography_key);

CREATE INDEX IF NOT EXISTS idx_dim_geography_state_code ON dim_geography(state_code);

CREATE INDEX IF NOT EXISTS idx_dim_product_category ON dim_product(product_category_name_english);

CREATE INDEX IF NOT EXISTS idx_dim_seller_geography_key ON dim_seller(geography_key);

CREATE INDEX IF NOT EXISTS idx_dim_date_month_year ON dim_date(month_year);
CREATE INDEX IF NOT EXISTS idx_dim_date_year_month ON dim_date(year_number, month_number);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_fact_sales_cust_date ON fact_sales(customer_key, purchase_date_key);
CREATE INDEX IF NOT EXISTS idx_dim_customer_segment_combo ON dim_customer_segment(segment, customer_key);

-- Verify indexes were created
SELECT name AS index_name FROM sqlite_master WHERE type = 'index' ORDER BY name;
