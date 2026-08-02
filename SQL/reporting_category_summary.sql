-- =============================================================================
-- Reporting Layer
-- Table: reporting_category_summary
-- Purpose: Product performance (Revenue, Orders, Average Price by Category)
-- =============================================================================

USE brazilian_ecommerce_dw;

-- 1. Drop old table
DROP TABLE IF EXISTS reporting_category_summary;

-- 2. Create reporting table
CREATE TABLE reporting_category_summary AS
SELECT 
    COALESCE(p.product_category_name_english, 'Uncategorized') AS product_category,
    SUM(f.total_sales_amount) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(f.sales_key) AS total_items_sold,
    AVG(f.price) AS average_item_price
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY 
    COALESCE(p.product_category_name_english, 'Uncategorized')
ORDER BY 
    total_revenue DESC;

-- 3. Indexes
CREATE INDEX idx_rcs_category ON reporting_category_summary(product_category);

-- 4. Verification query
SELECT COUNT(*) AS total_rows
FROM reporting_category_summary;
