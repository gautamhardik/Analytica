-- =============================================================================
-- Brazilian E-Commerce Data Warehouse
-- Fact Table: fact_sales
-- =============================================================================

USE brazilian_ecommerce_dw;

-- =============================================================================
-- Drop Table (Development Only)
-- =============================================================================

DROP TABLE IF EXISTS fact_sales;

-- =============================================================================
-- Sales Fact Table
-- =============================================================================

CREATE TABLE fact_sales (
    sales_key BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Warehouse surrogate key',
    order_id VARCHAR(50) NOT NULL COMMENT 'Degenerate dimension',
    order_item_id TINYINT UNSIGNED NOT NULL COMMENT 'Item number within the order',
    customer_key INT NOT NULL COMMENT 'FK -> dim_customer',
    product_key INT NOT NULL COMMENT 'FK -> dim_product',
    seller_key INT NOT NULL COMMENT 'FK -> dim_seller',
    purchase_date_key INT NOT NULL COMMENT 'FK -> dim_date',
    quantity SMALLINT UNSIGNED NOT NULL COMMENT 'Number of units sold',
    price DECIMAL(10,2) NOT NULL COMMENT 'Item price',
    freight_value DECIMAL(10,2) NOT NULL COMMENT 'Shipping cost',
    total_sales_amount DECIMAL(10,2) NOT NULL COMMENT 'price + freight_value',
    etl_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Audit timestamp',
    etl_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Audit timestamp',

    -- Uniqueness Constraint on Business Grain
    CONSTRAINT uk_fact_sales_order_item UNIQUE (order_id, order_item_id),

    -- Foreign Keys
    CONSTRAINT fk_sales_customer FOREIGN KEY (customer_key) 
        REFERENCES dim_customer(customer_key) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sales_product FOREIGN KEY (product_key) 
        REFERENCES dim_product(product_key) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sales_seller FOREIGN KEY (seller_key) 
        REFERENCES dim_seller(seller_key) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sales_purchase_date FOREIGN KEY (purchase_date_key) 
        REFERENCES dim_date(date_key) ON UPDATE CASCADE ON DELETE RESTRICT,

    -- Business Rules
    CHECK (quantity > 0),
    CHECK (price >= 0),
    CHECK (freight_value >= 0),
    CHECK (total_sales_amount >= 0)
)
COMMENT='Sales fact table at order-item grain'
ENGINE = InnoDB
DEFAULT CHARSET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- =============================================================================
-- Indexes
-- =============================================================================

-- Indexes on dimensions and degenerate dimensions for fast querying
CREATE INDEX idx_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_sales_product ON fact_sales(product_key);
CREATE INDEX idx_sales_seller ON fact_sales(seller_key);
CREATE INDEX idx_sales_purchase_date ON fact_sales(purchase_date_key);
CREATE INDEX idx_sales_order_id ON fact_sales(order_id);

-- Composite Indexes for common analytical patterns
CREATE INDEX idx_sales_customer_date ON fact_sales(customer_key, purchase_date_key);
CREATE INDEX idx_sales_product_date ON fact_sales(product_key, purchase_date_key);
CREATE INDEX idx_sales_seller_date ON fact_sales(seller_key, purchase_date_key);

-- =============================================================================
-- Verify
-- =============================================================================

SHOW TABLE STATUS LIKE 'fact_sales';
DESCRIBE fact_sales;
SHOW INDEX FROM fact_sales;
