# Source-to-Warehouse Mapping (ETL Specification)

> **Project:** Enterprise E-Commerce Analytics & ML Platform (Analytica 360)  
> **ETL Engine:** Vectorized Python (Polars & PyArrow) & MySQL DDL Scripts  
> **Target Schema:** `brazilian_ecommerce_dw` (Star Schema)  

This document provides the field-level mapping from operational (OLTP) source tables to dimensional (OLAP) data warehouse tables.

---

## 1. Dimensions

### `DimCustomer`
| Target Column (Warehouse) | Data Type | Source Table | Source Column | Transformation Rules / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `customer_key` | INT | *Generated* | - | Auto-incrementing Surrogate Key. |
| `customer_id` | VARCHAR | `customers` | `customer_id` | Natural Key. |
| `customer_unique_id` | VARCHAR | `customers` | `customer_unique_id` | |
| `city` | VARCHAR | `customers` | `customer_city` | Title case standardizing. |
| `state` | VARCHAR | `customers` | `customer_state` | Uppercase (2-letter codes). |
| `zip_code_prefix` | VARCHAR | `customers` | `customer_zip_code_prefix`| |

### `DimProduct`
| Target Column (Warehouse) | Data Type | Source Table | Source Column | Transformation Rules / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `product_key` | INT | *Generated* | - | Auto-incrementing Surrogate Key. |
| `product_id` | VARCHAR | `products` | `product_id` | Natural Key. |
| `category_name` | VARCHAR | `translation` | `product_category_name_english` | **JOIN** `products` to `category_translation`. Use English. |
| `weight_g` | INT | `products` | `product_weight_g` | Handle NULLs. |
| `length_cm` | INT | `products` | `product_length_cm` | Handle NULLs. |
| `height_cm` | INT | `products` | `product_height_cm` | Handle NULLs. |
| `width_cm` | INT | `products` | `product_width_cm` | Handle NULLs. |

### `DimSeller`
| Target Column (Warehouse) | Data Type | Source Table | Source Column | Transformation Rules / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `seller_key` | INT | *Generated* | - | Auto-incrementing Surrogate Key. |
| `seller_id` | VARCHAR | `sellers` | `seller_id` | Natural Key. |
| `city` | VARCHAR | `sellers` | `seller_city` | Title case standardizing. |
| `state` | VARCHAR | `sellers` | `seller_state` | Uppercase (2-letter codes). |
| `zip_code_prefix` | VARCHAR | `sellers` | `seller_zip_code_prefix`| |

### `DimDate`
Generated in ETL using a calendar script. Contains standard fields: `date_key`, `full_date`, `year`, `quarter`, `month`, `month_name`, `day`, `day_of_week`.

---

## 2. Fact Table

### `FactSales`
**Grain:** One row per order item.

| Target Column (Warehouse) | Data Type | Source Table | Source Column | Transformation Rules / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `order_item_key` | INT | *Generated* | - | Surrogate Key (Primary Key). |
| `order_id` | VARCHAR | `order_items` | `order_id` | **Degenerate Dimension**. |
| `customer_key` | INT | `customers` | `customer_id` | FK Lookup to `DimCustomer`. |
| `product_key` | INT | `order_items` | `product_id` | FK Lookup to `DimProduct`. |
| `seller_key` | INT | `order_items` | `seller_id` | FK Lookup to `DimSeller`. |
| `order_date_key` | INT | `orders` | `order_purchase_timestamp` | Convert timestamp to YYYYMMDD integer. |
| `price` | DECIMAL | `order_items` | `price` | |
| `freight_value` | DECIMAL | `order_items` | `freight_value` | |
| `payment_value` | DECIMAL | `payments` | `payment_value` | **Enrichment:** Join on `order_id` and distribute payment value. |
| `review_score` | INT | `reviews` | `review_score` | **Enrichment:** Join on `order_id`. |
| `delivery_days` | INT | `orders` | *Derived* | `DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)` |
| `is_late_delivery`| BOOLEAN | `orders` | *Derived* | `TRUE` if `delivered_date` > `estimated_date`. |
