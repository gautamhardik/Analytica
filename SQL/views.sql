-- =============================================================================
-- Brazilian E-Commerce Data Warehouse
-- Production Analytical Business Views
-- =============================================================================

USE brazilian_ecommerce_dw;

-- =============================================================================
-- 1. Sales Performance by Category
-- =============================================================================
CREATE OR REPLACE VIEW vw_sales_by_category AS
SELECT 
    COALESCE(p.product_category_name_english, 'Uncategorized') AS product_category,
    COUNT(f.sales_key) AS total_items_sold,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.price) AS total_item_revenue,
    SUM(f.freight_value) AS total_freight_revenue,
    SUM(f.total_sales_amount) AS total_gross_revenue,
    AVG(f.price) AS avg_item_price
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY COALESCE(p.product_category_name_english, 'Uncategorized');

-- =============================================================================
-- 2. Customer Order & Spending Summary
-- =============================================================================
CREATE OR REPLACE VIEW vw_customer_rfm_summary AS
SELECT 
    c.customer_unique_id,
    g.state_code AS customer_state,
    g.city_name AS customer_city,
    COUNT(DISTINCT f.order_id) AS total_orders_placed,
    COUNT(f.sales_key) AS total_items_purchased,
    SUM(f.total_sales_amount) AS total_lifetime_spend,
    AVG(f.total_sales_amount) AS avg_order_item_spend,
    MAX(d.full_date) AS most_recent_purchase_date
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
LEFT JOIN dim_geography g ON c.geography_key = g.geography_key
JOIN dim_date d ON f.purchase_date_key = d.date_key
GROUP BY c.customer_unique_id, g.state_code, g.city_name;

-- =============================================================================
-- 3. Monthly Sales & Freight Revenue Trend
-- =============================================================================
CREATE OR REPLACE VIEW vw_monthly_revenue_trend AS
SELECT 
    d.year_number,
    d.month_number,
    d.month_year,
    COUNT(DISTINCT f.order_id) AS monthly_orders,
    COUNT(f.sales_key) AS monthly_items_sold,
    SUM(f.price) AS monthly_item_revenue,
    SUM(f.freight_value) AS monthly_freight_revenue,
    SUM(f.total_sales_amount) AS monthly_gross_revenue,
    AVG(f.total_sales_amount) AS monthly_avg_item_value
FROM fact_sales f
JOIN dim_date d ON f.purchase_date_key = d.date_key
GROUP BY d.year_number, d.month_number, d.month_year
ORDER BY d.year_number, d.month_number;

-- =============================================================================
-- 4. Seller Performance Analysis
-- =============================================================================
CREATE OR REPLACE VIEW vw_seller_performance AS
SELECT 
    s.seller_id,
    g.state_code AS seller_state,
    g.city_name AS seller_city,
    COUNT(DISTINCT f.order_id) AS orders_fulfilled,
    COUNT(f.sales_key) AS items_sold,
    SUM(f.price) AS gross_item_revenue,
    SUM(f.freight_value) AS freight_generated,
    SUM(f.total_sales_amount) AS total_revenue_generated
FROM fact_sales f
JOIN dim_seller s ON f.seller_key = s.seller_key
LEFT JOIN dim_geography g ON s.geography_key = g.geography_key
GROUP BY s.seller_id, g.state_code, g.city_name;
