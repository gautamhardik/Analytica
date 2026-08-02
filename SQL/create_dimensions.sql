-- =============================================================================
-- Brazilian E-Commerce Data Warehouse
-- Dimension Tables
-- =============================================================================

USE brazilian_ecommerce_dw;

-- =============================================================================
-- Drop Tables (Development Only)
-- =============================================================================

DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_geography;
DROP TABLE IF EXISTS dim_date;

-- =============================================================================
-- Geography Dimension
-- =============================================================================

CREATE TABLE dim_geography (
    geography_key INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Warehouse surrogate key',
    zip_code_prefix INT NOT NULL,
    city_name VARCHAR(100) NOT NULL,
    state_code CHAR(2) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    etl_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    etl_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_geography (zip_code_prefix, city_name, state_code),
    CHECK (state_code REGEXP '^[A-Z]{2}$'),
    CHECK (zip_code_prefix >= 0)
)
COMMENT='Geography dimension'
ENGINE = InnoDB
DEFAULT CHARSET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- =============================================================================
-- Customer Dimension
-- =============================================================================

CREATE TABLE dim_customer (
    customer_key INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Warehouse surrogate key',
    customer_id VARCHAR(50) NOT NULL COMMENT 'Original customer identifier from Olist',
    customer_unique_id VARCHAR(50) NOT NULL,
    geography_key INT,
    etl_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    etl_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_customer_id UNIQUE (customer_id),
    CONSTRAINT fk_customer_geography FOREIGN KEY (geography_key) 
        REFERENCES dim_geography (geography_key) 
        ON UPDATE CASCADE 
        ON DELETE RESTRICT
)
COMMENT='Customer dimension'
ENGINE = InnoDB
DEFAULT CHARSET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- =============================================================================
-- Seller Dimension
-- =============================================================================

CREATE TABLE dim_seller (
    seller_key INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Warehouse surrogate key',
    seller_id VARCHAR(50) NOT NULL COMMENT 'Original seller identifier from Olist',
    geography_key INT,
    etl_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    etl_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_seller_id UNIQUE (seller_id),
    CONSTRAINT fk_seller_geography FOREIGN KEY (geography_key) 
        REFERENCES dim_geography (geography_key) 
        ON UPDATE CASCADE 
        ON DELETE RESTRICT
)
COMMENT='Seller dimension'
ENGINE = InnoDB
DEFAULT CHARSET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- =============================================================================
-- Product Dimension
-- =============================================================================

CREATE TABLE dim_product (
    product_key INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Warehouse surrogate key',
    product_id VARCHAR(50) NOT NULL COMMENT 'Original product identifier from Olist',
    product_category_name VARCHAR(255),
    product_category_name_english VARCHAR(255),
    product_name_length SMALLINT UNSIGNED,
    product_description_length SMALLINT UNSIGNED,
    product_photos_qty SMALLINT UNSIGNED,
    product_weight_g INT UNSIGNED,
    product_length_cm SMALLINT UNSIGNED,
    product_height_cm SMALLINT UNSIGNED,
    product_width_cm SMALLINT UNSIGNED,
    product_volume_cm3 INT UNSIGNED COMMENT 'Calculated during ETL as length × width × height',
    etl_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    etl_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_product_id UNIQUE (product_id)
)
COMMENT='Product dimension'
ENGINE = InnoDB
DEFAULT CHARSET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- =============================================================================
-- Date Dimension
-- =============================================================================

CREATE TABLE dim_date (
    date_key INT PRIMARY KEY COMMENT 'Date surrogate key in YYYYMMDD format',
    full_date DATE NOT NULL,
    day_number TINYINT UNSIGNED NOT NULL,
    day_name VARCHAR(15) NOT NULL,
    week_number TINYINT UNSIGNED NOT NULL,
    month_number TINYINT UNSIGNED NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    month_short_name VARCHAR(3) NOT NULL,
    month_year CHAR(7) NOT NULL,
    quarter_number TINYINT UNSIGNED NOT NULL,
    quarter_name VARCHAR(2) NOT NULL,
    quarter_label VARCHAR(6) NOT NULL,
    year_number SMALLINT UNSIGNED NOT NULL,
    day_of_year SMALLINT UNSIGNED,
    is_weekend BOOLEAN NOT NULL,
    is_month_start BOOLEAN NOT NULL,
    is_month_end BOOLEAN NOT NULL,
    etl_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    etl_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_full_date UNIQUE (full_date)
)
COMMENT='Date dimension'
ENGINE = InnoDB
DEFAULT CHARSET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- =============================================================================
-- Indexes
-- =============================================================================

-- Foreign Key Indexes
CREATE INDEX idx_customer_geography ON dim_customer(geography_key);
CREATE INDEX idx_seller_geography ON dim_seller(geography_key);

-- Alternate Key Indexes
CREATE INDEX idx_customer_unique_id ON dim_customer(customer_unique_id);

-- =============================================================================
-- Verify
-- =============================================================================

SHOW TABLE STATUS;

SHOW INDEX FROM dim_customer;
SHOW INDEX FROM dim_product;
SHOW INDEX FROM dim_seller;
SHOW INDEX FROM dim_geography;
SHOW INDEX FROM dim_date;