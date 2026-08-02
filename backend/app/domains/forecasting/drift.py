"""Feature-drift check for the forecasting model.

Compares the distribution of the most recent data window against the training
distribution recorded in ``feature_stats.json`` (per-feature mean/std at
training time).  Purely calendar-derived features are excluded because they are
expected to shift as time advances; only business-driver features (lags,
rolling aggregates, seller/freight volumes) are scored.
"""

import json
from pathlib import Path

import polars as pl
from sqlalchemy import create_engine

from app.core.config import settings
from app.ml.forecasting.features import build_features, build_ts, detect_data_cutoff, extract_daily

ML_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "forecasting"

RECENT_WINDOW = 60
Z_WATCH = 2.0
Z_DRIFT = 3.0

_CALENDAR_ONLY = {
    "year", "quarter", "month", "week_of_year", "day_of_month", "day_of_week",
    "day_of_year", "weekend_flag", "month_start", "month_end", "quarter_start",
    "quarter_end", "day_sin", "day_cos", "month_sin", "month_cos",
    "black_friday_week", "christmas_season", "new_year_day", "mothers_day",
    "fathers_day", "time_index",
}


def _is_calendar_feature(name: str) -> bool:
    return name in _CALENDAR_ONLY or name.startswith("fourier_")


def _load_training_stats():
    stats_path = ML_DIR / "feature_stats.json"
    if not stats_path.exists():
        return None
    with open(stats_path) as f:
        return json.load(f)


def _compute_recent_stats(engine, feature_names):
    df_raw = extract_daily(engine)
    if df_raw.is_empty():
        return None, None
    df_ts = build_ts(df_raw)
    cutoff = detect_data_cutoff(df_ts)
    if cutoff is None:
        return None, None
    df_ts = df_ts.filter(pl.col("order_date") <= cutoff)
    df_feat = build_features(df_ts)
    recent = df_feat.tail(RECENT_WINDOW)
    present = [c for c in feature_names if c in df_feat.columns and c in recent.columns]
    stats = {}
    for c in present:
        s = recent[c].drop_nulls()
        if s.is_empty():
            continue
        stats[c] = {"mean": float(s.mean()), "std": float(s.std())}
    return stats, df_ts


def compute_drift() -> dict:
    """Return a drift report comparing the recent window vs training stats."""
    stats = _load_training_stats()
    if not stats:
        return {
            "status": "unavailable",
            "message": "Training feature statistics (feature_stats.json) not found.",
            "drifted_features": [],
        }

    train_features = stats.get("features", {})
    if not train_features:
        return {"status": "unavailable", "message": "feature_stats.json is empty.", "drifted_features": []}

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    try:
        recent_stats, df_ts = _compute_recent_stats(engine, list(train_features.keys()))
    finally:
        engine.dispose()

    if recent_stats is None:
        return {"status": "unavailable", "message": "No daily sales data available for drift comparison.", "drifted_features": []}

    rows = []
    for feat, train in train_features.items():
        if feat not in recent_stats or _is_calendar_feature(feat):
            continue
        rec = recent_stats[feat]
        train_std = train.get("std") or 0.0
        denom = train_std if train_std > 0 else abs(train.get("mean")) * 0.01 or 1.0
        z = (rec["mean"] - train["mean"]) / denom
        rows.append({
            "feature": feat,
            "train_mean": round(float(train["mean"]), 4),
            "recent_mean": round(float(rec["mean"]), 4),
            "train_std": round(float(train_std), 4),
            "recent_std": round(float(rec["std"]), 4),
            "z_score": round(float(z), 2),
        })

    rows.sort(key=lambda r: abs(r["z_score"]), reverse=True)
    total = len(rows)
    n_watch = sum(1 for r in rows if abs(r["z_score"]) >= Z_WATCH)
    n_drift = sum(1 for r in rows if abs(r["z_score"]) >= Z_DRIFT)
    max_z = max((abs(r["z_score"]) for r in rows), default=0.0)

    watch_ratio = n_watch / total if total else 0.0
    drift_ratio = n_drift / total if total else 0.0
    if drift_ratio >= 0.15 or watch_ratio >= 0.40:
        status = "drifted"
    elif watch_ratio >= 0.10:
        status = "watch"
    else:
        status = "healthy"

    window = {"end": str(df_ts["order_date"].max()) if df_ts is not None else None,
              "days": RECENT_WINDOW}
    return {
        "status": status,
        "score": round(max_z, 2),
        "n_features": total,
        "n_watch": n_watch,
        "n_drifted": n_drift,
        "watch_threshold": Z_WATCH,
        "drift_threshold": Z_DRIFT,
        "trained_on": stats.get("captured_at"),
        "training_rows": stats.get("n_rows"),
        "window": window,
        "message": _status_message(status),
        "drifted_features": rows[:10],
    }


def _status_message(status: str) -> str:
    if status == "healthy":
        return "Recent data is consistent with the training distribution."
    if status == "watch":
        return "Some features are drifting from the training distribution; monitor closely."
    return "Significant feature drift detected — consider retraining the model."
