import csv
import json
from pathlib import Path
from app.domains.forecasting.schemas import (
    ForecastResponse, ForecastMetadata, ForecastMetrics, MonthlyRecord, DailyRecord, FeatureImportance,
)

ML_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "forecasting"

with open(ML_DIR / "metadata.json") as f:
    _meta = json.load(f)

SCALING_FACTOR = _meta.get("scaling_factor", 6.85)
BASELINE_REVENUE = _meta.get("baseline_revenue", 1003308.47)


def _descale(val: float) -> float:
    """Convert model output back to original revenue scale.

    Model was trained on target = revenue / (baseline / scaling_factor).
    CSV data stores raw model output (pre-scaled).  Descale so the API
    returns meaningful R$ values.
    """
    return val * BASELINE_REVENUE / SCALING_FACTOR


_history: list[MonthlyRecord] = []
_csv = ML_DIR / "monthly_history.csv"
if _csv.exists():
    with open(_csv, newline="") as f:
        for r in csv.DictReader(f):
            _history.append(MonthlyRecord(month_year=r["month_year"], actual_revenue=float(r["actual_revenue"])))

_forecast_monthly: list[MonthlyRecord] = []
_csv2 = ML_DIR / "monthly_forecast.csv"
if _csv2.exists():
    with open(_csv2, newline="") as f:
        for r in csv.DictReader(f):
            _forecast_monthly.append(MonthlyRecord(
                month_year=r["month_year"],
                forecast_revenue=_descale(float(r["forecast_revenue"])),
                forecast_lower=_descale(float(r["forecast_lower"])) if r.get("forecast_lower") else None,
                forecast_upper=_descale(float(r["forecast_upper"])) if r.get("forecast_upper") else None,
            ))

_test_results: list[DailyRecord] = []
_csv3 = ML_DIR / "test_results.csv"
if _csv3.exists():
    with open(_csv3, newline="") as f:
        for r in csv.DictReader(f):
            _test_results.append(DailyRecord(
                order_date=r["order_date"],
                actual_revenue=float(r["actual_revenue"]),
                predicted_revenue=float(r["predicted_revenue"]),
                forecast_lower=_descale(float(r["forecast_lower"])) if r.get("forecast_lower") else None,
                forecast_upper=_descale(float(r["forecast_upper"])) if r.get("forecast_upper") else None,
                residual=float(r["residual"]),
                abs_error=float(r["abs_error"]),
            ))

_future: list[DailyRecord] = []
_csv4 = ML_DIR / "future_forecast.csv"
if _csv4.exists():
    with open(_csv4, newline="") as f:
        for r in csv.DictReader(f):
            _future.append(DailyRecord(
                order_date=r["order_date"],
                forecast_revenue=_descale(float(r["forecast_revenue"])),
                forecast_lower=_descale(float(r["forecast_lower"])) if r.get("forecast_lower") else None,
                forecast_upper=_descale(float(r["forecast_upper"])) if r.get("forecast_upper") else None,
            ))

_top_features: list[FeatureImportance] = []
with open(ML_DIR / "top_features.json") as f:
    for item in json.load(f):
        _top_features.append(FeatureImportance(**item))

# Merge history + forecast into one monthly list
_all_months = {r.month_year: r for r in _history}
for r in _forecast_monthly:
    if r.month_year in _all_months:
        _all_months[r.month_year].forecast_revenue = r.forecast_revenue
    else:
        _all_months[r.month_year] = r

_monthly_sorted = sorted(_all_months.values(), key=lambda x: x.month_year)


from app.core.cache import get_cache, set_cache, make_cache_key


async def get_forecast() -> ForecastResponse:
    cache_key = make_cache_key("forecasting_data", {})
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    response = ForecastResponse(
        metadata=ForecastMetadata(
            algorithm=_meta["algorithm"],
            version=_meta["version"],
            training_date=_meta["training_date"],
            features=_meta["features"],
            best_iteration=_meta["best_iteration"],
            history_start=_meta["history_start"],
            history_end=_meta["history_end"],
            forecast_start=_meta["forecast_start"],
            forecast_end=_meta["forecast_end"],
            scaling_factor=SCALING_FACTOR,
            baseline_revenue=BASELINE_REVENUE,
            metrics=ForecastMetrics(**_meta["metrics"]),
            model_version=_meta.get("model_version"),
            data_cutoff=_meta.get("data_cutoff"),
            model_file_sha256=_meta.get("model_file_sha256"),
            interval_coverage_90=_meta.get("interval_coverage_90"),
            dm_test=_meta.get("dm_test"),
            ensemble=_meta.get("ensemble"),
        ),
        monthly=_monthly_sorted,
        daily_test=_test_results,
        daily_forecast=_future,
        top_features=_top_features,
    )
    set_cache(cache_key, response, ttl_seconds=300)
    return response

