-- =============================================================================
-- Brazilian E-Commerce Data Warehouse
-- Comprehensive SQL Validation & Referential Integrity Test Suite
-- =============================================================================

USE brazilian_ecommerce_dw;

-- =============================================================================
-- 1. Table Row Counts
-- =============================================================================
SELECT 'dim_geography' AS Table_Name, COUNT(*) AS Row_Count FROM dim_geography
UNION ALL
SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL
SELECT 'dim_seller', COUNT(*) FROM dim_seller
UNION ALL
SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL
SELECT 'dim_date', COUNT(*) FROM dim_date
UNION ALL
SELECT 'fact_sales', COUNT(*) FROM fact_sales;

-- =============================================================================
-- 2. Business Key Uniqueness Checks (Should all return 0 rows)
-- =============================================================================

-- Customer ID Uniqueness
SELECT customer_id, COUNT(*) AS dup_count 
FROM dim_customer 
GROUP BY customer_id 
HAVING COUNT(*) > 1;

-- Seller ID Uniqueness
SELECT seller_id, COUNT(*) AS dup_count 
FROM dim_seller 
GROUP BY seller_id 
HAVING COUNT(*) > 1;

-- Product ID Uniqueness
SELECT product_id, COUNT(*) AS dup_count 
FROM dim_product 
GROUP BY product_id 
HAVING COUNT(*) > 1;

-- Fact Sales Order Item Uniqueness
SELECT order_id, order_item_id, COUNT(*) AS dup_count 
FROM fact_sales 
GROUP BY order_id, order_item_id 
HAVING COUNT(*) > 1;

-- =============================================================================
-- 3. Referential Integrity Checks (Should all return 0 orphan rows)
-- =============================================================================

-- Customer -> Geography Foreign Key
SELECT COUNT(*) AS orphan_customer_geography
FROM dim_customer c
LEFT JOIN dim_geography g ON c.geography_key = g.geography_key
WHERE c.geography_key IS NOT NULL AND g.geography_key IS NULL;

-- Seller -> Geography Foreign Key
SELECT COUNT(*) AS orphan_seller_geography
FROM dim_seller s
LEFT JOIN dim_geography g ON s.geography_key = g.geography_key
WHERE s.geography_key IS NOT NULL AND g.geography_key IS NULL;

-- Fact -> Customer Foreign Key
SELECT COUNT(*) AS orphan_sales_customer
FROM fact_sales f
LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
WHERE c.customer_key IS NULL;

-- Fact -> Seller Foreign Key
SELECT COUNT(*) AS orphan_sales_seller
FROM fact_sales f
LEFT JOIN dim_seller s ON f.seller_key = s.seller_key
WHERE s.seller_key IS NULL;

-- Fact -> Product Foreign Key
SELECT COUNT(*) AS orphan_sales_product
FROM fact_sales f
LEFT JOIN dim_product p ON f.product_key = p.product_key
WHERE p.product_key IS NULL;

-- Fact -> Date Foreign Key
SELECT COUNT(*) AS orphan_sales_date
FROM fact_sales f
LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
WHERE d.date_key IS NULL;

-- =============================================================================
-- 4. Executive Warehouse Aggregations
-- =============================================================================
SELECT 
    COUNT(*) AS Total_Fact_Rows,
    COUNT(DISTINCT order_id) AS Total_Orders,
    SUM(price) AS Total_Item_Revenue,
    SUM(freight_value) AS Total_Freight_Revenue,
    SUM(total_sales_amount) AS Total_Gross_Revenue,
    AVG(total_sales_amount) AS Average_Order_Item_Value,
    AVG(price) AS Average_Item_Price,
    AVG(freight_value) AS Average_Freight_Cost
FROM fact_sales;
