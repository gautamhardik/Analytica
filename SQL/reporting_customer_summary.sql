-- =============================================================================
-- Reporting Layer
-- Table: reporting_customer_summary
-- Purpose: Customer analytics (Repeat Customers, Revenue, Avg Spend)
-- =============================================================================

USE brazilian_ecommerce_dw;

-- 1. Drop old table
DROP TABLE IF EXISTS reporting_customer_summary;

-- 2. Create reporting table
CREATE TABLE reporting_customer_summary AS
SELECT 
    c.customer_unique_id,
    SUM(f.total_sales_amount) AS lifetime_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(f.sales_key) AS total_items_purchased,
    SUM(f.total_sales_amount) / COUNT(DISTINCT f.order_id) AS average_order_value,
    CASE WHEN COUNT(DISTINCT f.order_id) > 1 THEN 1 ELSE 0 END AS is_repeat_customer
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY 
    c.customer_unique_id
ORDER BY 
    lifetime_revenue DESC;

-- 3. Indexes
CREATE INDEX idx_rcus_customer ON reporting_customer_summary(customer_unique_id);

-- 4. Verification query
SELECT COUNT(*) AS total_rows 
FROM reporting_customer_summary;
