"""Shared daily-forecast feature engineering (polars + numpy only).

Mirrors the feature construction in ``ml/train_forecast.py`` so the backend can
recompute features for drift monitoring without importing the full ML stack
(pandas/optuna/lightgbm/sklearn).
"""

import numpy as np
import polars as pl
from sqlalchemy import text

LAG_DAYS = [1, 2, 3, 7, 14, 28, 30, 60, 90]
ROLLING_WINDOWS = [7, 14, 30, 60, 90]
CUTOFF_SELLER_RATIO = 0.5
CUTOFF_TRAIL_WINDOW = 90

DAILY_SQL = """
    SELECT
        d.full_date AS order_date,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(f.sales_key) AS total_items,
        COUNT(DISTINCT f.customer_key) AS total_customers,
        COUNT(DISTINCT f.seller_key) AS total_sellers,
        SUM(f.total_sales_amount) AS daily_revenue,
        AVG(f.price) AS avg_item_price,
        SUM(f.freight_value) AS total_freight,
        AVG(f.freight_value) AS avg_freight
    FROM fact_sales f
    JOIN dim_date d ON f.purchase_date_key = d.date_key
    GROUP BY d.full_date
    ORDER BY order_date
"""


def extract_daily(engine):
    """Daily aggregates from the raw fact table (matches the trainer query)."""
    with engine.connect() as conn:
        rows = conn.execute(text(DAILY_SQL)).mappings().all()
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame([dict(r) for r in rows])
    return df.with_columns([
        pl.col("order_date").cast(pl.Date),
        pl.col("daily_revenue").cast(pl.Float64),
        pl.col("total_orders").cast(pl.Float64),
        pl.col("total_items").cast(pl.Float64),
        pl.col("total_customers").cast(pl.Float64),
        pl.col("total_sellers").cast(pl.Float64),
        pl.col("avg_item_price").cast(pl.Float64),
        pl.col("total_freight").cast(pl.Float64),
        pl.col("avg_freight").cast(pl.Float64),
    ]).sort("order_date")


def build_ts(df_raw):
    """Continuous daily series with zero-filled gaps."""
    if df_raw.is_empty():
        return df_raw
    min_date = df_raw["order_date"].min()
    max_date = df_raw["order_date"].max()
    full_date_grid = pl.date_range(start=min_date, end=max_date, interval="1d", eager=True).alias("order_date")
    df_grid = pl.DataFrame({"order_date": full_date_grid})
    df_ts = df_grid.join(df_raw, on="order_date", how="left").with_columns([
        pl.col("daily_revenue").fill_null(0.0),
        pl.col("total_orders").fill_null(0.0),
        pl.col("total_items").fill_null(0.0),
        pl.col("total_customers").fill_null(0.0),
        pl.col("total_sellers").fill_null(0.0),
        pl.col("avg_item_price").fill_null(0.0),
        pl.col("total_freight").fill_null(0.0),
        pl.col("avg_freight").fill_null(0.0),
    ]).sort("order_date")
    return df_ts.with_columns([
        (pl.col("total_items") / (pl.col("total_orders").clip(lower_bound=1.0))).alias("avg_items_per_order"),
        (pl.col("daily_revenue") / (pl.col("total_orders").clip(lower_bound=1.0))).alias("avg_order_value"),
        (1.0 + pl.col("daily_revenue")).log().alias("log_daily_revenue"),
    ])


def detect_data_cutoff(df_ts):
    """Return the last 'complete' date (inclusive). Same rule as the trainer."""
    if df_ts.is_empty():
        return None
    sellers = df_ts["total_sellers"].to_numpy()
    dates = df_ts["order_date"].to_numpy()
    n = len(sellers)
    tail_mean = float(np.mean(sellers[max(0, n - CUTOFF_TRAIL_WINDOW):]))
    last_ok = None
    for i in range(n - 1, -1, -1):
        if sellers[i] >= CUTOFF_SELLER_RATIO * tail_mean:
            last_ok = dates[i]
            break
    if last_ok is None:
        last_ok = dates[-1]
    return last_ok


def build_features(df_ts):
    """Full feature matrix — mirrors build_features in ml/train_forecast.py."""
    df_feat = df_ts.with_columns([
        pl.col("order_date").dt.year().alias("year"),
        pl.col("order_date").dt.quarter().alias("quarter"),
        pl.col("order_date").dt.month().alias("month"),
        pl.col("order_date").dt.week().alias("week_of_year"),
        pl.col("order_date").dt.day().alias("day_of_month"),
        pl.col("order_date").dt.weekday().alias("day_of_week"),
        pl.col("order_date").dt.ordinal_day().alias("day_of_year"),
        (pl.col("order_date").dt.weekday() >= 6).cast(pl.Int32).alias("weekend_flag"),
        (pl.col("order_date").dt.day() == 1).cast(pl.Int32).alias("month_start"),
        (pl.col("order_date") == pl.col("order_date").dt.month_end()).cast(pl.Int32).alias("month_end"),
        ((pl.col("order_date").dt.month().is_in([1, 4, 7, 10])) & (pl.col("order_date").dt.day() == 1)).cast(pl.Int32).alias("quarter_start"),
        ((pl.col("order_date").dt.month().is_in([3, 6, 9, 12])) & (pl.col("order_date") == pl.col("order_date").dt.month_end())).cast(pl.Int32).alias("quarter_end"),
        (np.sin(2 * np.pi * pl.col("order_date").dt.weekday() / 7.0)).alias("day_sin"),
        (np.cos(2 * np.pi * pl.col("order_date").dt.weekday() / 7.0)).alias("day_cos"),
        (np.sin(2 * np.pi * pl.col("order_date").dt.month() / 12.0)).alias("month_sin"),
        (np.cos(2 * np.pi * pl.col("order_date").dt.month() / 12.0)).alias("month_cos"),
    ])

    df_feat = df_feat.with_columns([
        ((pl.col("month") == 11) & (pl.col("day_of_month") >= 20) & (pl.col("day_of_month") <= 30)).cast(pl.Int32).alias("black_friday_week"),
        ((pl.col("month") == 12) & (pl.col("day_of_month") >= 18) & (pl.col("day_of_month") <= 25)).cast(pl.Int32).alias("christmas_season"),
        ((pl.col("month") == 1) & (pl.col("day_of_month") == 1)).cast(pl.Int32).alias("new_year_day"),
        ((pl.col("month") == 5) & (pl.col("day_of_month") >= 8) & (pl.col("day_of_month") <= 14) & (pl.col("day_of_week") == 7)).cast(pl.Int32).alias("mothers_day"),
        ((pl.col("month") == 8) & (pl.col("day_of_month") >= 8) & (pl.col("day_of_month") <= 14) & (pl.col("day_of_week") == 7)).cast(pl.Int32).alias("fathers_day"),
    ])

    fourier_exprs = []
    for k in range(1, 4):
        fourier_exprs.append((np.sin(2 * np.pi * k * pl.col("day_of_year") / 365.25)).alias(f"fourier_sin_{k}"))
        fourier_exprs.append((np.cos(2 * np.pi * k * pl.col("day_of_year") / 365.25)).alias(f"fourier_cos_{k}"))
    df_feat = df_feat.with_columns(fourier_exprs)

    lag_exprs = []
    for lag in LAG_DAYS:
        lag_exprs.append(pl.col("log_daily_revenue").shift(lag).alias(f"log_rev_lag_{lag}"))
        lag_exprs.append(pl.col("daily_revenue").shift(lag).alias(f"rev_lag_{lag}"))
        lag_exprs.append(pl.col("total_orders").shift(lag).alias(f"orders_lag_{lag}"))
        lag_exprs.append(pl.col("total_customers").shift(lag).alias(f"customers_lag_{lag}"))
        lag_exprs.append(pl.col("avg_order_value").shift(lag).alias(f"aov_lag_{lag}"))
    df_feat = df_feat.with_columns(lag_exprs)

    rolling_exprs = []
    for w in ROLLING_WINDOWS:
        rolling_exprs.append(pl.col("log_daily_revenue").shift(1).rolling_mean(window_size=w).alias(f"log_rev_roll_mean_{w}"))
        rolling_exprs.append(pl.col("daily_revenue").shift(1).rolling_mean(window_size=w).alias(f"rev_roll_mean_{w}"))
        rolling_exprs.append(pl.col("log_daily_revenue").shift(1).rolling_std(window_size=w).alias(f"log_rev_roll_std_{w}"))
        rolling_exprs.append(pl.col("log_daily_revenue").shift(1).rolling_min(window_size=w).alias(f"log_rev_roll_min_{w}"))
        rolling_exprs.append(pl.col("log_daily_revenue").shift(1).rolling_max(window_size=w).alias(f"log_rev_roll_max_{w}"))
        rolling_exprs.append(pl.col("log_daily_revenue").shift(1).ewm_mean(span=w).alias(f"log_rev_roll_ema_{w}"))
    df_feat = df_feat.with_columns(rolling_exprs)

    df_feat = df_feat.with_columns([
        pl.col("total_orders").shift(1).alias("orders_prev_day"),
        pl.col("avg_order_value").shift(1).alias("aov_prev_day"),
        pl.col("total_customers").shift(1).alias("customers_prev_day"),
        pl.col("total_items").shift(1).alias("items_prev_day"),
        pl.col("avg_items_per_order").shift(1).alias("items_per_order_prev_day"),
        pl.col("total_freight").shift(1).alias("freight_prev_day"),
        pl.col("avg_freight").shift(1).alias("avg_freight_prev_day"),
        pl.col("total_sellers").shift(1).alias("sellers_prev_day"),
        pl.col("total_sellers").shift(1).rolling_mean(window_size=7).alias("sellers_roll_mean_7"),
        (pl.col("daily_revenue") / (pl.col("total_sellers").shift(1).clip(lower_bound=1.0))).alias("rev_per_seller_prev_day"),
        (pl.col("order_date") - df_ts["order_date"].min()).dt.total_days().alias("time_index"),
    ])
    return df_feat
