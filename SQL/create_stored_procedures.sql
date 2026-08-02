-- =============================================================================
-- Stored Procedure: refresh_reporting_layer
-- Purpose: Atomically truncate and reload all 4 reporting summary tables.
-- Run this after the ETL pipeline completes, or whenever fact_sales changes.
-- =============================================================================

USE brazilian_ecommerce_dw;

DROP PROCEDURE IF EXISTS refresh_reporting_layer;

DELIMITER //

CREATE PROCEDURE refresh_reporting_layer()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- 1. Sales summary (monthly grain)
    TRUNCATE TABLE reporting_sales_summary;
    INSERT INTO reporting_sales_summary
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
    GROUP BY d.year_number, d.month_number, d.month_year
    ORDER BY d.year_number, d.month_number;

    -- 2. Category summary
    TRUNCATE TABLE reporting_category_summary;
    INSERT INTO reporting_category_summary
    SELECT 
        COALESCE(p.product_category_name_english, 'Uncategorized') AS product_category,
        SUM(f.total_sales_amount) AS total_revenue,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(f.sales_key) AS total_items_sold,
        AVG(f.price) AS average_item_price
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    GROUP BY COALESCE(p.product_category_name_english, 'Uncategorized')
    ORDER BY total_revenue DESC;

    -- 3. State summary
    TRUNCATE TABLE reporting_state_summary;
    INSERT INTO reporting_state_summary
    SELECT 
        g.state_code,
        SUM(f.total_sales_amount) AS total_revenue,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(DISTINCT c.customer_unique_id) AS total_customers,
        SUM(f.freight_value) AS total_freight_cost
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_geography g ON c.geography_key = g.geography_key
    GROUP BY g.state_code
    ORDER BY total_revenue DESC;

    -- 4. Customer summary
    TRUNCATE TABLE reporting_customer_summary;
    INSERT INTO reporting_customer_summary
    SELECT 
        c.customer_unique_id,
        SUM(f.total_sales_amount) AS lifetime_revenue,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(f.sales_key) AS total_items_purchased,
        SUM(f.total_sales_amount) / COUNT(DISTINCT f.order_id) AS average_order_value,
        CASE WHEN COUNT(DISTINCT f.order_id) > 1 THEN 1 ELSE 0 END AS is_repeat_customer
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    GROUP BY c.customer_unique_id
    ORDER BY lifetime_revenue DESC;

    COMMIT;
END //

DELIMITER ;
