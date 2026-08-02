-- =============================================================================
-- Brazilian E-Commerce Data Warehouse
-- Performance Indexes Configuration
-- =============================================================================

USE brazilian_ecommerce_dw;

-- =============================================================================
-- Dimension Alternate & Foreign Key Indexes
-- =============================================================================

-- dim_customer
CREATE INDEX IF NOT EXISTS idx_customer_unique_id ON dim_customer(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_customer_geography ON dim_customer(geography_key);

-- dim_seller
CREATE INDEX IF NOT EXISTS idx_seller_geography ON dim_seller(geography_key);

-- dim_product
CREATE INDEX IF NOT EXISTS idx_product_category ON dim_product(product_category_name_english);

-- dim_geography
CREATE INDEX IF NOT EXISTS idx_geography_state ON dim_geography(state_code);

-- dim_date
CREATE INDEX IF NOT EXISTS idx_date_year_month ON dim_date(year_number, month_number);

-- =============================================================================
-- Fact Table Foreign Key & Composite Indexes
-- =============================================================================

-- Dimension Foreign Key Indexes (Fast Join Performance)
CREATE INDEX IF NOT EXISTS idx_sales_customer ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_sales_product ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_sales_seller ON fact_sales(seller_key);
CREATE INDEX IF NOT EXISTS idx_sales_purchase_date ON fact_sales(purchase_date_key);
CREATE INDEX IF NOT EXISTS idx_sales_order_id ON fact_sales(order_id);

-- Composite Indexes for Common Analytical Patterns
CREATE INDEX IF NOT EXISTS idx_sales_customer_date ON fact_sales(customer_key, purchase_date_key);
CREATE INDEX IF NOT EXISTS idx_sales_product_date ON fact_sales(product_key, purchase_date_key);
CREATE INDEX IF NOT EXISTS idx_sales_seller_date ON fact_sales(seller_key, purchase_date_key);
