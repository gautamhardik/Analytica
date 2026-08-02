-- =============================================================================
-- Reporting Layer
-- Table: reporting_state_summary
-- Purpose: Geographic analytics (Revenue, Orders, Customers by State)
-- =============================================================================

USE brazilian_ecommerce_dw;

-- 1. Drop old table
DROP TABLE IF EXISTS reporting_state_summary;

-- 2. Create reporting table
CREATE TABLE reporting_state_summary AS
SELECT 
    g.state_code,
    SUM(f.total_sales_amount) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(DISTINCT c.customer_unique_id) AS total_customers,
    SUM(f.freight_value) AS total_freight_cost
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
JOIN dim_geography g ON c.geography_key = g.geography_key
GROUP BY 
    g.state_code
ORDER BY 
    total_revenue DESC;

-- 3. Indexes
CREATE INDEX idx_rsts_state ON reporting_state_summary(state_code);

-- 4. Verification query
SELECT COUNT(*) AS total_rows
FROM reporting_state_summary;
