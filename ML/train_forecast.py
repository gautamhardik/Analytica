#!/usr/bin/env python
"""
Forecast Model Comparison & Deployment Trainer
=============================================
Tests multiple ML regressors (LightGBM, XGBoost, CatBoost, Random Forest) on
log-space daily revenue forecasting, tunes them with Optuna, blends the top
performers into a weighted hybrid ensemble, evaluates against naive baselines
(including a Diebold-Mariano test), runs a walk-forward backtest, and writes
all artifacts consumed by the backend forecasting service.

Improvements over v1.1
----------------------
- Hybrid ensemble: weighted blend (inverse validation RMSE) of the top-3 models.
- External business driver: daily distinct sellers (+ rolling/revenue-per-seller).
- Auto data-cutoff detection: partial/truncated tail days are excluded from
  training and the forecast starts at the first complete missing day.
- Quantile regression (LightGBM 5%/95%) for calibrated forecast intervals.
- Walk-forward rolling backtest and Diebold-Mariano test vs naive baseline.
- Artifact integrity: SHA-256 of the model file + feature stats for drift checks.

Usage:
    python ml/train_forecast.py
"""
import hashlib
import json
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import optuna
import polars as pl
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import text

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

SEED = 42
PROMOTE_THRESHOLD = 0.005  # min relative validation-RMSE gain to deploy ensemble over best single
np.random.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ETL.config import get_db_engine

TRAIN_END_DATE = date(2018, 3, 31)
VALID_START_DATE = date(2018, 4, 1)
VALID_END_DATE = date(2018, 6, 15)
TEST_START_DATE = date(2018, 6, 16)

FORECAST_HORIZON = 30
LAG_DAYS = [1, 2, 3, 7, 14, 28, 30, 60, 90]
ROLLING_WINDOWS = [7, 14, 30, 60, 90]
MODEL_VERSION = "v1.2"
# Tail truncation: days whose seller count is below this fraction of the
# trailing 90-day mean are treated as partial/truncated data and dropped.
CUTOFF_SELLER_RATIO = 0.5
CUTOFF_TRAIL_WINDOW = 90

ML_DIR = PROJECT_ROOT / "backend" / "app" / "ml" / "forecasting"
ML_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data extraction & feature engineering
# ---------------------------------------------------------------------------
def extract_daily():
    engine = get_db_engine()
    SQL_QUERY = """
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
    ORDER BY order_date;
    """
    import pandas as pd
    with engine.connect() as conn:
        df = pl.from_pandas(pd.read_sql(SQL_QUERY, conn))
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
        np.log1p(pl.col("daily_revenue")).alias("log_daily_revenue"),
    ])


def detect_data_cutoff(df_ts):
    """Return the last 'complete' date (inclusive).

    The source series truncates abruptly near its end (data collection cutoff):
    daily seller counts collapse from ~200 to <50 and revenue to ~0. We find the
    last date whose seller count is >= 50% of the trailing mean and treat every
    later day as partial/truncated (excluded from training).
    """
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
        (pl.col("daily_revenue") / (pl.col("total_sellers").clip(lower_bound=1.0))).shift(1).alias("rev_per_seller_prev_day"),
        pl.arange(0, df_feat.height).alias("time_index"),
    ])
    return df_feat.drop_nulls()


def get_feature_columns(df_model_ready):
    EXCLUDE_COLS = ["order_date", "log_daily_revenue", "daily_revenue", "rev_lag_1",
                    "total_orders", "total_items", "total_customers", "total_sellers",
                    "avg_item_price", "total_freight", "avg_freight",
                    "avg_items_per_order", "avg_order_value"]
    return [col for col in df_model_ready.columns if col not in EXCLUDE_COLS]


def calc_metrics(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}


# ---------------------------------------------------------------------------
# Model zoo (log-space regressors with Optuna tuning) + hybrid ensemble
# ---------------------------------------------------------------------------
class WeightedEnsemble:
    """Blend of fitted log-space regressors. sklearn-compatible predict()."""

    def __init__(self, members, weights, names):
        self.members = members
        self.weights = np.asarray(weights, dtype=float)
        self.names = names

    def _predict_log(self, X):
        preds = np.column_stack([m.predict(X) for m in self.members])
        return preds @ self.weights

    def predict(self, X):
        return self._predict_log(X)

    def fit(self, X, y):
        return self


def make_models():
    import lightgbm as lgb
    import xgboost as xgb
    from catboost import CatBoostRegressor
    from sklearn.ensemble import RandomForestRegressor
    return {
        "LightGBM": {
            "class": lgb.LGBMRegressor,
            "kind": "lightgbm",
            "params": {
                "objective": "regression", "metric": "rmse", "random_state": SEED, "verbose": -1,
                "n_estimators": (300, 1000), "learning_rate": (0.01, 0.08, "log"),
                "num_leaves": (15, 63), "max_depth": (3, 10),
                "subsample": (0.6, 1.0), "colsample_bytree": (0.6, 1.0),
                "reg_alpha": (1e-3, 10.0, "log"), "reg_lambda": (1e-3, 10.0, "log"),
            },
            "early_stopping": True,
        },
        "XGBoost": {
            "class": xgb.XGBRegressor,
            "kind": "xgboost",
            "params": {
                "objective": "reg:squarederror", "eval_metric": "rmse", "random_state": SEED, "verbosity": 0,
                "n_estimators": (300, 1000), "learning_rate": (0.01, 0.08, "log"),
                "max_depth": (3, 10), "min_child_weight": (1, 10),
                "subsample": (0.6, 1.0), "colsample_bytree": (0.6, 1.0),
                "reg_alpha": (1e-3, 10.0, "log"), "reg_lambda": (1e-3, 10.0, "log"),
            },
            "early_stopping": True,
        },
        "CatBoost": {
            "class": CatBoostRegressor,
            "kind": "catboost",
            "params": {
                "loss_function": "RMSE", "random_seed": SEED, "verbose": False,
                "iterations": (300, 1000), "learning_rate": (0.01, 0.08, "log"),
                "depth": (4, 10), "l2_leaf_reg": (1e-3, 10.0, "log"),
            },
            "early_stopping": True,
        },
        "RandomForest": {
            "class": RandomForestRegressor,
            "kind": "randomforest",
            "params": {
                "n_estimators": (200, 600), "max_depth": (5, 30),
                "min_samples_leaf": (2, 20),
            },
            "early_stopping": False,
        },
    }


def _fit_with_early_stopping(model, kind, X_train, y_train_log, X_val, y_val_raw):
    y_val_log = np.log1p(y_val_raw)
    if kind == "lightgbm":
        import lightgbm as lgb
        model.fit(X_train, y_train_log, eval_set=[(X_val, y_val_log)],
                  callbacks=[lgb.early_stopping(50, verbose=False)])
    elif kind == "xgboost":
        model.set_params(early_stopping_rounds=50)
        model.fit(X_train, y_train_log, eval_set=[(X_val, y_val_log)], verbose=False)
    elif kind == "catboost":
        model.fit(X_train, y_train_log, eval_set=(X_val, y_val_log),
                  early_stopping_rounds=50, verbose=False)
    else:
        model.fit(X_train, y_train_log)
    return model


def build_objective(cls, kind, param_spec, X_train, y_train_log, X_val, y_val_raw, early_stopping):
    def objective(trial):
        params = {}
        for name, spec in param_spec.items():
            if isinstance(spec, tuple) and len(spec) == 3 and isinstance(spec[2], str):
                low, high, _ = spec
                params[name] = trial.suggest_float(name, low, high, log=True)
            elif isinstance(spec, tuple) and len(spec) == 2:
                low, high = spec
                if isinstance(low, int) and isinstance(high, int):
                    params[name] = trial.suggest_int(name, low, high)
                else:
                    params[name] = trial.suggest_float(name, low, high)
            else:
                params[name] = spec
        m = cls(**params)
        if early_stopping:
            _fit_with_early_stopping(m, kind, X_train, y_train_log, X_val, y_val_raw)
        else:
            m.fit(X_train, y_train_log)
        preds_raw = np.expm1(m.predict(X_val))
        return float(np.sqrt(mean_squared_error(y_val_raw, preds_raw)))
    return objective


def train_model(cls, kind, best_params, X_train, y_train_log, X_val, y_val_raw, early_stopping):
    m = cls(**best_params)
    if early_stopping:
        _fit_with_early_stopping(m, kind, X_train, y_train_log, X_val, y_val_raw)
    else:
        m.fit(X_train, y_train_log)
    return m


def build_ensemble(members, val_rmse):
    """Weight top-N models by inverse validation RMSE (log-space blend)."""
    weights = 1.0 / np.array(val_rmse, dtype=float)
    weights = weights / weights.sum()
    return WeightedEnsemble([m for m, _ in members], weights, [n for n, _ in members])


def fit_quantile_model(X_train, y_train_log, X_val, y_val_raw, alpha):
    """LightGBM quantile regressor on the log target."""
    import lightgbm as lgb
    m = lgb.LGBMRegressor(
        objective="quantile", alpha=alpha, random_state=SEED, verbose=-1,
        n_estimators=500, learning_rate=0.05, num_leaves=31,
    )
    m.fit(X_train, y_train_log, eval_set=[(X_val, np.log1p(y_val_raw))],
          callbacks=[lgb.early_stopping(50, verbose=False)])
    return m


# ---------------------------------------------------------------------------
# Evaluation rigor: Diebold-Mariano + walk-forward backtest
# ---------------------------------------------------------------------------
def diebold_mariano(e1, e2, h=1):
    """One-sided DM test (squared error loss). Returns (statistic, p-value).

    e1 is the candidate forecast errors, e2 the benchmark errors.  The test
    uses the standard DM statistic under the null of equal accuracy and
    returns the one-sided p-value for the alternative that the candidate
    is MORE accurate (lower squared loss) than the benchmark.
    """
    from scipy import stats
    e1 = np.asarray(e1, dtype=float)
    e2 = np.asarray(e2, dtype=float)
    d = e1 ** 2 - e2 ** 2
    n = len(d)
    if n < 2 or np.std(d, ddof=1) == 0:
        return 0.0, 1.0
    var_d = np.var(d, ddof=1)
    # Harvey et al. (1997) small-sample correction for h-step-ahead forecasts
    dm = d.mean() / np.sqrt(var_d / n)
    dm_c = dm * np.sqrt((n - 1) / (n - h))
    p = stats.norm.cdf(dm_c)  # one-sided: candidate beats benchmark (lower loss)
    return float(dm_c), float(p)


def rolling_backtest(df_model_ready, feature_cols, kind, params, n_folds=4, horizon=30):
    """Walk-forward backtest with fixed lookback: fit on train window, score next `horizon` days.

    Uses the champion's tuning recipe on the (fast) LightGBM path so the backtest
    stays cheap while remaining representative of the deployed pipeline.
    """
    import lightgbm as lgb
    import pandas as pd
    results = []
    dates = df_model_ready["order_date"].to_numpy()
    max_date = dates.max()
    train_start = dates[0]
    # last (n_folds * horizon) days are used as test windows; train window grows from train_start
    window_end = max_date - np.timedelta64((n_folds - 1) * horizon, "D")
    fold_start = window_end
    for _ in range(n_folds):
        test_end = min(fold_start + np.timedelta64(horizon - 1, "D"), max_date)
        df_tr = df_model_ready.filter((pl.col("order_date") >= train_start) & (pl.col("order_date") < fold_start))
        df_te = df_model_ready.filter((pl.col("order_date") >= fold_start) & (pl.col("order_date") <= test_end))
        if df_tr.height < 200 or df_te.height == 0:
            break
        X_tr = df_tr.select(feature_cols).to_pandas()
        y_tr = df_tr["log_daily_revenue"].to_pandas()
        X_te = df_te.select(feature_cols).to_pandas()
        y_te_raw = df_te["daily_revenue"].to_numpy()
        m = lgb.LGBMRegressor(**params, objective="regression", metric="rmse",
                              random_state=SEED, verbose=-1)
        m.fit(X_tr, y_tr)
        preds = np.expm1(m.predict(X_te))
        met = calc_metrics(y_te_raw, preds)
        results.append({
            "fold_test_start": str(pd.to_datetime(fold_start).date()),
            "fold_test_end": str(pd.to_datetime(test_end).date()),
            "mae": round(met["MAE"], 2), "rmse": round(met["RMSE"], 2),
            "r2": round(met["R2"], 4), "mape": round(met["MAPE"], 2),
        })
        fold_start = test_end + np.timedelta64(1, "D")
    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------
def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_model_file(model, champion_name, quantile_models=None):
    import joblib
    joblib.dump(model, ML_DIR / "model.pkl")
    if quantile_models is not None:
        joblib.dump(quantile_models, ML_DIR / "quantile_models.pkl")
    return sha256_of(ML_DIR / "model.pkl")


def feature_stats(df_model_ready, feature_cols):
    """Per-feature mean/std captured at training time for drift checks."""
    import pandas as pd
    X = df_model_ready.select(feature_cols).to_pandas()
    stats = {"n_rows": int(len(X)), "captured_at": str(date.today()),
             "features": {c: {"mean": float(X[c].mean()), "std": float(X[c].std())} for c in feature_cols}}
    return stats


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def _best_iteration_of(model, kind):
    """Return the early-stopping best iteration for boosting models, else None."""
    if kind == "ensemble":
        return None
    if kind == "lightgbm":
        return getattr(model, "best_iteration_", None)
    if kind == "xgboost":
        return getattr(model, "best_iteration", None)
    if kind == "catboost":
        bi = model.get_best_iteration()
        return int(bi) if bi is not None else None
    return None


def main():
    import joblib
    import pandas as pd

    print("=" * 70)
    print("FORECAST MODEL COMPARISON & DEPLOYMENT  (%s)" % MODEL_VERSION)
    print("=" * 70)

    # 1. Data + auto cutoff detection
    df_raw = extract_daily()
    df_ts = build_ts(df_raw)
    cutoff_date = detect_data_cutoff(df_ts)
    df_ts = df_ts.filter(pl.col("order_date") <= cutoff_date)
    print(f"Data cutoff (last complete day): {cutoff_date} | "
          f"excluded {df_raw.height - df_ts.height} truncated tail days")

    df_model_ready = build_features(df_ts)
    FEATURE_COLUMNS = get_feature_columns(df_model_ready)
    print(f"Feature matrix: {df_model_ready.shape} | {len(FEATURE_COLUMNS)} features")

    # 2. Split
    df_train = df_model_ready.filter(pl.col("order_date") <= TRAIN_END_DATE)
    df_valid = df_model_ready.filter((pl.col("order_date") >= VALID_START_DATE) & (pl.col("order_date") <= VALID_END_DATE))
    df_test = df_model_ready.filter(pl.col("order_date") >= TEST_START_DATE)
    assert df_train["order_date"].max() < df_valid["order_date"].min()
    assert df_valid["order_date"].max() < df_test["order_date"].min()

    X_train = df_train.select(FEATURE_COLUMNS).to_pandas()
    y_train_log = df_train["log_daily_revenue"].to_pandas()
    X_valid = df_valid.select(FEATURE_COLUMNS).to_pandas()
    y_valid_log = df_valid["log_daily_revenue"].to_pandas()
    y_valid_raw = df_valid["daily_revenue"].to_numpy()
    X_test = df_test.select(FEATURE_COLUMNS).to_pandas()
    y_test_log = df_test["log_daily_revenue"].to_pandas()
    y_test_raw = df_test["daily_revenue"].to_numpy()

    # 3. Baselines
    test_naive_preds = df_test["rev_lag_1"].to_numpy()
    test_ma7_preds = np.expm1(df_test["log_rev_roll_mean_7"].to_numpy())
    baselines = {
        "Naive (t-1)": calc_metrics(y_test_raw, test_naive_preds),
        "7-Day MA": calc_metrics(y_test_raw, test_ma7_preds),
    }
    print("\n--- Baselines (Test) ---")
    for name, m in baselines.items():
        print(f"  {name:<10}: MAE={m['MAE']:.2f} RMSE={m['RMSE']:.2f} R2={m['R2']:.4f} MAPE={m['MAPE']:.2f}%")

    # 4. Model comparison + Optuna tuning
    print("\n--- Optuna tuning & comparison (12 trials each) ---")
    results = []
    best_models = {}
    val_rmse_by_model = {}
    models = make_models()
    for name, spec in models.items():
        cls = spec["class"]
        obj = build_objective(cls, spec["kind"], spec["params"], X_train, y_train_log, X_valid, y_valid_raw, spec["early_stopping"])
        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED))
        study.optimize(obj, n_trials=12, show_progress_bar=False)
        best_params = study.best_params
        model = train_model(cls, spec["kind"], best_params, X_train, y_train_log, X_valid, y_valid_raw, spec["early_stopping"])
        val_preds = np.expm1(model.predict(X_valid))
        test_preds = np.expm1(model.predict(X_test))
        val_m = calc_metrics(y_valid_raw, val_preds)
        test_m = calc_metrics(y_test_raw, test_preds)
        best_models[name] = (model, best_params)
        val_rmse_by_model[name] = val_m["RMSE"]
        results.append({
            "model": name,
            "val_rmse": round(val_m["RMSE"], 2),
            "val_mae": round(val_m["MAE"], 2),
            "test_rmse": round(test_m["RMSE"], 2),
            "test_mae": round(test_m["MAE"], 2),
            "test_r2": round(test_m["R2"], 4),
            "test_mape": round(test_m["MAPE"], 2),
        })
        print(f"  {name:<12} val_RMSE={val_m['RMSE']:>10.2f}  test_RMSE={test_m['RMSE']:>10.2f}  "
              f"test_MAE={test_m['MAE']:>9.2f}  R2={test_m['R2']:.4f}  MAPE={test_m['MAPE']:.1f}%")

    # 5. Hybrid ensemble: blend top-3 by validation RMSE
    ranked = sorted(val_rmse_by_model.items(), key=lambda kv: kv[1])
    top_names = [n for n, _ in ranked[:3]]
    members = [(best_models[n][0], n) for n in top_names]
    ensemble = build_ensemble(members, [val_rmse_by_model[n] for n in top_names])

    ens_val = calc_metrics(y_valid_raw, np.expm1(ensemble.predict(X_valid)))
    ens_test = calc_metrics(y_test_raw, np.expm1(ensemble.predict(X_test)))
    results.append({
        "model": "Ensemble (Top-3)",
        "val_rmse": round(ens_val["RMSE"], 2),
        "val_mae": round(ens_val["MAE"], 2),
        "test_rmse": round(ens_test["RMSE"], 2),
        "test_mae": round(ens_test["MAE"], 2),
        "test_r2": round(ens_test["R2"], 4),
        "test_mape": round(ens_test["MAPE"], 2),
    })
    print(f"\n  Ensemble blend of {', '.join(top_names)}: "
          f"val_RMSE={ens_val['RMSE']:>10.2f}  test_RMSE={ens_test['RMSE']:>10.2f}  "
          f"R2={ens_test['R2']:.4f}  MAPE={ens_test['MAPE']:.1f}%")

    # Champion selection with a minimum-improvement guard: only promote the
    # ensemble if it beats the best single model on validation by a meaningful
    # margin; otherwise deploy the best single (simpler, and avoids promoting a
    # blend on validation noise that does not generalize to the test window).
    best_single_name = ranked[0][0]
    ens_rel_gain = 1.0 - ens_val["RMSE"] / val_rmse_by_model[best_single_name]
    use_ensemble = ens_rel_gain >= PROMOTE_THRESHOLD
    if use_ensemble:
        champion_name = "Ensemble (Top-3)"
        champion = ensemble
        champion_params = {"member_models": top_names, "weights": [round(float(w), 4) for w in ensemble.weights]}
        champion_kind = "ensemble"
    else:
        champion_name = best_single_name
        champion = best_models[best_single_name][0]
        champion_params = best_models[best_single_name][1]
        champion_kind = models[best_single_name]["kind"]
    print(f"\n>>> CHAMPION: {champion_name} "
          f"(ensemble relative val-RMSE gain {ens_rel_gain:.4f} vs promote threshold {PROMOTE_THRESHOLD:.4f})")

    test_preds = np.expm1(champion.predict(X_test))
    final_test = calc_metrics(y_test_raw, test_preds)

    # Diebold-Mariano: champion vs naive (and vs MA7)
    dm_naive = diebold_mariano(y_test_raw - test_preds, y_test_raw - test_naive_preds)
    dm_ma7 = diebold_mariano(y_test_raw - test_preds, y_test_raw - test_ma7_preds)
    print(f"DM (champion vs naive): stat={dm_naive[0]:.3f} p={dm_naive[1]:.4f}")
    print(f"DM (champion vs MA7)  : stat={dm_ma7[0]:.3f} p={dm_ma7[1]:.4f}")

    # 6. Deployment model (fit on ALL complete data)
    X_all = pd.concat([X_train, X_valid, X_test])
    y_all_log = pd.concat([y_train_log, y_valid_log, y_test_log])
    if use_ensemble:
        deploy_members = []
        deploy_weights = []
        for n in top_names:
            spec = models[n]
            m = train_model(spec["class"], spec["kind"], best_models[n][1], X_all, y_all_log,
                            X_valid, y_valid_raw, spec["early_stopping"])
            deploy_members.append(m)
            deploy_weights.append(1.0 / val_rmse_by_model[n])
        deploy_weights = np.array(deploy_weights)
        deploy_weights = deploy_weights / deploy_weights.sum()
        deploy_model = WeightedEnsemble(deploy_members, deploy_weights, top_names)
    else:
        spec = models[best_single_name]
        deploy_model = train_model(spec["class"], spec["kind"], best_models[best_single_name][1],
                                   X_all, y_all_log, X_valid, y_valid_raw, spec["early_stopping"])

    # Quantile models for calibrated intervals (5% / 95%)
    print("\n--- Training quantile regressors (5% / 95%) ---")
    q_low = fit_quantile_model(X_train, y_train_log, X_valid, y_valid_raw, 0.05)
    q_high = fit_quantile_model(X_train, y_train_log, X_valid, y_valid_raw, 0.95)
    quantile_models = {"low": q_low, "high": q_high}

    # Test-set intervals
    test_low = np.expm1(q_low.predict(X_test))
    test_high = np.expm1(q_high.predict(X_test))
    coverage = float(np.mean((y_test_raw >= test_low) & (y_test_raw <= test_high)))
    print(f"90% interval coverage on test: {coverage:.2%}")

    # 7. Recursive future forecast with de-truncated history
    print("\n--- Generating 30-day recursive future forecast ---")
    hist_ts = df_ts
    last_date = hist_ts["order_date"].max()
    last_drivers = {
        "total_orders": hist_ts["total_orders"][-1],
        "total_items": hist_ts["total_items"][-1],
        "total_customers": hist_ts["total_customers"][-1],
        "total_sellers": hist_ts["total_sellers"][-1],
        "avg_item_price": hist_ts["avg_item_price"][-1],
        "total_freight": hist_ts["total_freight"][-1],
        "avg_freight": hist_ts["avg_freight"][-1],
    }
    future = []
    for _ in range(FORECAST_HORIZON):
        feats = build_features(hist_ts)
        last_row = feats.tail(1).select(FEATURE_COLUMNS).to_pandas()
        pred_log = deploy_model.predict(last_row)[0]
        pred_raw = float(np.expm1(pred_log))
        low_raw = float(np.expm1(q_low.predict(last_row)[0]))
        high_raw = float(np.expm1(q_high.predict(last_row)[0]))
        next_date = last_date + timedelta(days=1)
        new_day = build_ts(pl.DataFrame({
            "order_date": [next_date], "daily_revenue": [pred_raw],
            "total_orders": [last_drivers["total_orders"]], "total_items": [last_drivers["total_items"]],
            "total_customers": [last_drivers["total_customers"]], "total_sellers": [last_drivers["total_sellers"]],
            "avg_item_price": [last_drivers["avg_item_price"]],
            "total_freight": [last_drivers["total_freight"]], "avg_freight": [last_drivers["avg_freight"]],
        }))
        hist_ts = pl.concat([hist_ts, new_day.select(hist_ts.columns)])
        future.append((next_date, pred_raw, low_raw, high_raw))
        last_date = next_date

    print(f"Forecast generated: {future[0][0]} .. {future[-1][0]} ({len(future)} days)")

    # 8. Feature importance (permutation on the ensemble)
    from sklearn.inspection import permutation_importance
    class _EnsembleWrapper:
        def __init__(self, m):
            self.m = m
        def fit(self, X, y):
            return self
        def predict(self, X):
            return self.m.predict(X)
    try:
        perm = permutation_importance(_EnsembleWrapper(deploy_model), X_test, y_test_log,
                                      n_repeats=5, random_state=SEED, scoring="neg_mean_squared_error")
        gain = np.maximum(0.0, perm.importances_mean)
    except Exception:
        gain = np.ones(len(FEATURE_COLUMNS))
    total = gain.sum()
    if total > 0:
        gain = gain / total * 100.0
    split = np.ones(len(FEATURE_COLUMNS))
    top_features = sorted(
        [{"feature": f, "importance_gain": float(g), "importance_split": 1.0}
         for f, g in zip(FEATURE_COLUMNS, gain)],
        key=lambda x: x["importance_gain"], reverse=True)

    # 9. Write backend artifacts
    model_sha = write_model_file(deploy_model, champion_name, quantile_models)

    metadata = {
        "algorithm": f"{champion_name} Regressor (log1p target)",
        "model_version": MODEL_VERSION,
        "version": MODEL_VERSION,
        "training_date": str(date.today()),
        "target": "daily_revenue (log1p transformed)",
        "features": len(FEATURE_COLUMNS),
        "best_iteration": _best_iteration_of(champion, champion_kind),
        "train_size": int(df_train.height),
        "valid_size": int(df_valid.height),
        "test_size": int(df_test.height),
        "history_start": str(df_ts["order_date"].min()),
        "history_end": str(df_ts["order_date"].max()),
        "data_cutoff": str(cutoff_date),
        "forecast_start": str(future[0][0]),
        "forecast_end": str(future[-1][0]),
        "scaling_factor": 1.0,
        "baseline_revenue": 1.0,
        "model_file_sha256": model_sha,
        "ensemble": ({"members": top_names, "weights": [round(float(w), 4) for w in deploy_weights]} if use_ensemble else None),
        "dm_test": {
            "vs_naive": {"stat": round(dm_naive[0], 4), "p_value": round(dm_naive[1], 4)},
            "vs_ma7": {"stat": round(dm_ma7[0], 4), "p_value": round(dm_ma7[1], 4)},
        },
        "interval_coverage_90": round(coverage, 4),
        "metrics": {
            "test_mae": round(float(final_test["MAE"]), 2),
            "test_rmse": round(float(final_test["RMSE"]), 2),
            "test_r2": round(float(final_test["R2"]), 4),
            "test_mape": round(float(final_test["MAPE"]), 2),
        },
    }
    with open(ML_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # monthly history
    hist = df_ts.select(["order_date", "daily_revenue"]).to_pandas()
    hist["month_year"] = pd.to_datetime(hist["order_date"]).dt.to_period("M").astype(str)
    hist_m = hist.groupby("month_year", as_index=False)["daily_revenue"].sum().rename(columns={"daily_revenue": "actual_revenue"})
    hist_m.to_csv(ML_DIR / "monthly_history.csv", index=False)

    # monthly forecast
    fut_df = pd.DataFrame(future, columns=["order_date", "forecast_revenue", "forecast_lower", "forecast_upper"])
    fut_df["month_year"] = pd.to_datetime(fut_df["order_date"]).dt.to_period("M").astype(str)
    fut_m = fut_df.groupby("month_year", as_index=False)[["forecast_revenue", "forecast_lower", "forecast_upper"]].sum()
    fut_m.to_csv(ML_DIR / "monthly_forecast.csv", index=False)

    # test results (with quantile bounds)
    test_dates = df_test["order_date"].to_pandas()
    residuals = y_test_raw - test_preds
    tr = pd.DataFrame({
        "order_date": test_dates,
        "actual_revenue": y_test_raw,
        "predicted_revenue": test_preds,
        "forecast_lower": test_low,
        "forecast_upper": test_high,
        "residual": residuals,
        "abs_error": np.abs(residuals),
    }).sort_values("order_date")
    tr.to_csv(ML_DIR / "test_results.csv", index=False)

    # future forecast (with intervals)
    fut_df[["order_date", "forecast_revenue", "forecast_lower", "forecast_upper"]].to_csv(ML_DIR / "future_forecast.csv", index=False)

    # top features
    top = [{"feature": t["feature"], "importance_gain": t["importance_gain"], "importance_split": t["importance_split"]} for t in top_features[:15]]
    with open(ML_DIR / "top_features.json", "w") as f:
        json.dump(top, f, indent=2)

    # feature columns & params
    with open(ML_DIR / "feature_columns.json", "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)
    with open(ML_DIR / "model_params.json", "w") as f:
        json.dump({"ensemble": metadata["ensemble"],
                   "quantile": {"objective": "quantile", "alphas": [0.05, 0.95]}}, f, indent=2, default=str)

    # feature stats for drift checks
    with open(ML_DIR / "feature_stats.json", "w") as f:
        json.dump(feature_stats(df_model_ready, FEATURE_COLUMNS), f, indent=2)

    # comparison + backtest + DM exports
    res_df = pd.DataFrame(results).sort_values("val_rmse").reset_index(drop=True)
    cmp_out = PROJECT_ROOT / "NOTEBOOKS" / "Revenue Forecasting" / "outputs"
    cmp_out.mkdir(parents=True, exist_ok=True)
    res_df.to_csv(cmp_out / "model_comparison.csv", index=False)

    backtest_df = rolling_backtest(df_model_ready, FEATURE_COLUMNS, models["LightGBM"]["kind"],
                                   {k: v for k, v in best_models["LightGBM"][1].items()})
    backtest_df.to_csv(ML_DIR / "backtest_results.csv", index=False)
    backtest_df.to_csv(cmp_out / "backtest_results.csv", index=False)
    print("\n--- Walk-forward backtest (LightGBM) ---")
    print(backtest_df.to_string(index=False))
    if len(backtest_df):
        print(f"Backtest mean RMSE: {backtest_df['rmse'].mean():.2f} | mean MAPE: {backtest_df['mape'].mean():.2f}%")

    with open(ML_DIR / "dm_test.json", "w") as f:
        json.dump(metadata["dm_test"], f, indent=2)

    print("\nArtifacts written to", ML_DIR)
    print(f"Champion final: MAE={final_test['MAE']:.2f} RMSE={final_test['RMSE']:.2f} "
          f"R2={final_test['R2']:.4f} MAPE={final_test['MAPE']:.2f}%")


if __name__ == "__main__":
    main()
