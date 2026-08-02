-- Pre-aggregated tables for fast filtered queries
-- These pre-compute aggregates at every filter-dimension grain
-- eliminating expensive COUNT(DISTINCT) operations on 100K+ rows

-- Table 1: Monthly aggregate at (segment, state, month) grain
DROP TABLE IF EXISTS reporting_filter_monthly;
CREATE TABLE reporting_filter_monthly AS
SELECT
    COALESCE(dcs.segment, 'unknown') AS segment,
    COALESCE(dg.state_code, 'unknown') AS state_code,
    dd.month_year,
    dd.year_number,
    dd.month_number,
    SUM(fs.total_sales_amount) AS total_revenue,
    COUNT(DISTINCT fs.order_id) AS total_orders,
    COUNT(DISTINCT fs.customer_key) AS total_customers,
    SUM(fs.quantity) AS total_items_sold,
    SUM(fs.freight_value) AS total_freight
FROM fact_sales fs
JOIN dim_date dd ON fs.purchase_date_key = dd.date_key
LEFT JOIN dim_customer_segment dcs ON fs.customer_key = dcs.customer_key
LEFT JOIN dim_customer dc ON fs.customer_key = dc.customer_key
LEFT JOIN dim_geography dg ON dc.geography_key = dg.geography_key
GROUP BY dcs.segment, dg.state_code, dd.month_year, dd.year_number, dd.month_number;

CREATE INDEX idx_rfm_segment ON reporting_filter_monthly(segment);
CREATE INDEX idx_rfm_state ON reporting_filter_monthly(state_code);
CREATE INDEX idx_rfm_month ON reporting_filter_monthly(month_year);
CREATE INDEX idx_rfm_seg_state ON reporting_filter_monthly(segment, state_code);
CREATE INDEX idx_rfm_seg_month ON reporting_filter_monthly(segment, month_year);
CREATE INDEX idx_rfm_state_month ON reporting_filter_monthly(state_code, month_year);

-- Table 2: Total aggregate at (segment, state) grain (correct distinct customer counts)
DROP TABLE IF EXISTS reporting_filter_totals;
CREATE TABLE reporting_filter_totals AS
SELECT
    COALESCE(dcs.segment, 'unknown') AS segment,
    COALESCE(dg.state_code, 'unknown') AS state_code,
    SUM(fs.total_sales_amount) AS total_revenue,
    COUNT(DISTINCT fs.order_id) AS total_orders,
    COUNT(DISTINCT fs.customer_key) AS total_customers,
    SUM(fs.quantity) AS total_items_sold,
    SUM(fs.freight_value) AS total_freight
FROM fact_sales fs
LEFT JOIN dim_customer_segment dcs ON fs.customer_key = dcs.customer_key
LEFT JOIN dim_customer dc ON fs.customer_key = dc.customer_key
LEFT JOIN dim_geography dg ON dc.geography_key = dg.geography_key
GROUP BY dcs.segment, dg.state_code;

CREATE INDEX idx_rft_segment ON reporting_filter_totals(segment);
CREATE INDEX idx_rft_state ON reporting_filter_totals(state_code);
CREATE INDEX idx_rft_seg_state ON reporting_filter_totals(segment, state_code);

-- Table 3: Category aggregate at (segment, category) grain
DROP TABLE IF EXISTS reporting_filter_categories;
CREATE TABLE reporting_filter_categories AS
SELECT
    COALESCE(dcs.segment, 'unknown') AS segment,
    COALESCE(dp.product_category_name_english, 'unknown') AS product_category,
    SUM(fs.total_sales_amount) AS total_revenue,
    COUNT(DISTINCT fs.order_id) AS total_orders,
    SUM(fs.quantity) AS total_items_sold
FROM fact_sales fs
LEFT JOIN dim_customer_segment dcs ON fs.customer_key = dcs.customer_key
LEFT JOIN dim_product dp ON fs.product_key = dp.product_key
GROUP BY dcs.segment, dp.product_category_name_english;

CREATE INDEX idx_rfc_segment ON reporting_filter_categories(segment);
CREATE INDEX idx_rfc_category ON reporting_filter_categories(product_category);
CREATE INDEX idx_rfc_seg_cat ON reporting_filter_categories(segment, product_category);

-- Covering index for denormalized table (used for customer-level filtered queries)
DROP INDEX idx_fsd_covering ON fact_sales_denormalized;
CREATE INDEX idx_fsd_covering ON fact_sales_denormalized(segment, state_code, month_year, product_category_name_english, order_id, customer_key, total_sales_amount, quantity, freight_value);
