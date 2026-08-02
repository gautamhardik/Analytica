from pydantic import BaseModel


class ForecastMetrics(BaseModel):
    test_mae: float
    test_rmse: float
    test_r2: float
    test_mape: float


class ForecastMetadata(BaseModel):
    algorithm: str
    version: str
    training_date: str
    features: int
    best_iteration: int | None = None
    history_start: str
    history_end: str
    forecast_start: str
    forecast_end: str
    scaling_factor: float = 6.85
    baseline_revenue: float = 1003308.47
    metrics: ForecastMetrics
    model_version: str | None = None
    data_cutoff: str | None = None
    model_file_sha256: str | None = None
    interval_coverage_90: float | None = None
    dm_test: dict[str, dict[str, float]] | None = None
    ensemble: dict | None = None


class MonthlyRecord(BaseModel):
    month_year: str
    actual_revenue: float | None = None
    forecast_revenue: float | None = None
    forecast_lower: float | None = None
    forecast_upper: float | None = None


class DailyRecord(BaseModel):
    order_date: str
    actual_revenue: float | None = None
    predicted_revenue: float | None = None
    forecast_revenue: float | None = None
    forecast_lower: float | None = None
    forecast_upper: float | None = None
    residual: float | None = None
    abs_error: float | None = None


class FeatureImportance(BaseModel):
    feature: str
    importance_gain: float
    importance_split: float


class DriftFeature(BaseModel):
    feature: str
    train_mean: float
    recent_mean: float
    train_std: float
    recent_std: float
    z_score: float


class DriftWindow(BaseModel):
    end: str | None = None
    days: int


class DriftReport(BaseModel):
    status: str
    score: float
    n_features: int
    n_watch: int
    n_drifted: int
    watch_threshold: float
    drift_threshold: float
    trained_on: str | None = None
    training_rows: int | None = None
    window: DriftWindow | None = None
    message: str
    drifted_features: list[DriftFeature]


class ForecastResponse(BaseModel):
    metadata: ForecastMetadata
    monthly: list[MonthlyRecord]
    daily_test: list[DailyRecord]
    daily_forecast: list[DailyRecord]
    top_features: list[FeatureImportance]
