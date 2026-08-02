-- =============================================================================
-- Reporting Layer
-- Table: reporting_sales_summary
-- Purpose: Executive KPIs (Revenue, Orders, Customers, AOV by Month)
-- =============================================================================

USE brazilian_ecommerce_dw;

-- 1. Drop old table
DROP TABLE IF EXISTS reporting_sales_summary;

-- 2. Create reporting table
CREATE TABLE reporting_sales_summary AS
SELECT 
    d.year_number,
    d.month_number,
    d.month_year AS order_month,
    SUM(f.total_sales_amount) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(DISTINCT c.customer_unique_id) AS total_customers,
    SUM(f.total_sales_amount) / COUNT(DISTINCT f.order_id) AS average_order_value
FROM fact_sales f
JOIN dim_date d ON f.purchase_date_key = d.date_key
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY 
    d.year_number,
    d.month_number,
    d.month_year
ORDER BY 
    d.year_number, 
    d.month_number;

-- 3. Indexes
CREATE INDEX idx_rss_month ON reporting_sales_summary(order_month);

-- 4. Verification query
SELECT COUNT(*) AS total_rows 
FROM reporting_sales_summary;
