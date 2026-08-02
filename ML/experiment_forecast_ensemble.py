"""Forecast quality experiment: ensemble size & weighting schemes vs deployed recipe.

Replicates the deployed trainer's tuning (same splits, same Optuna budget, fixed seed)
and evaluates competing ensemble constructions on the holdout TEST window:
  - best single model
  - top-2 / top-3 / top-4 by validation RMSE, inverse-RMSE weights (deployed = top-3)
  - top-3 equal weights
  - all-models blend
Selection would be made on VALIDATION (matching the deploy rule); TEST metrics are
reported to confirm the choice generalizes. Does NOT write any deployment artifacts.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import optuna
import polars as pl

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.train_forecast import (
    SEED, TRAIN_END_DATE, VALID_START_DATE, VALID_END_DATE, TEST_START_DATE,
    WeightedEnsemble, build_features, build_objective, build_ts, calc_metrics,
    detect_data_cutoff, extract_daily, get_feature_columns, make_models, train_model,
)

optuna.logging.set_verbosity(optuna.logging.WARNING)

# --- 1. Data + split (identical to trainer) ---
df_raw = extract_daily()
df_ts = build_ts(df_raw)
cutoff_date = detect_data_cutoff(df_ts)
df_ts = df_ts.filter(pl.col("order_date") <= cutoff_date)
df_model_ready = build_features(df_ts)
FEATURE_COLUMNS = get_feature_columns(df_model_ready)
print(f"Feature matrix: {df_model_ready.shape} | {len(FEATURE_COLUMNS)} features | cutoff={cutoff_date}")

df_train = df_model_ready.filter(pl.col("order_date") <= TRAIN_END_DATE)
df_valid = df_model_ready.filter((pl.col("order_date") >= VALID_START_DATE) & (pl.col("order_date") <= VALID_END_DATE))
df_test = df_model_ready.filter(pl.col("order_date") >= TEST_START_DATE)

X_train = df_train.select(FEATURE_COLUMNS).to_pandas()
y_train_log = df_train["log_daily_revenue"].to_pandas()
X_valid = df_valid.select(FEATURE_COLUMNS).to_pandas()
y_valid_raw = df_valid["daily_revenue"].to_numpy()
X_test = df_test.select(FEATURE_COLUMNS).to_pandas()
y_test_raw = df_test["daily_revenue"].to_numpy()


def fit_tuned(spec):
    obj = build_objective(spec["class"], spec["kind"], spec["params"], X_train, y_train_log,
                          X_valid, y_valid_raw, spec["early_stopping"])
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(obj, n_trials=12, show_progress_bar=False)
    return train_model(spec["class"], spec["kind"], study.best_params, X_train, y_train_log,
                       X_valid, y_valid_raw, spec["early_stopping"])


# --- 2. Tune + fit each model (same budget + seed as trainer) ---
models = make_models()
fitted = {name: fit_tuned(spec) for name, spec in models.items()}

val_rmse = {}
test_metrics = {}
for name, model in fitted.items():
    val_rmse[name] = calc_metrics(y_valid_raw, np.expm1(model.predict(X_valid)))["RMSE"]
    test_metrics[name] = calc_metrics(y_test_raw, np.expm1(model.predict(X_test)))
    print(f"  {name:<12} val_RMSE={val_rmse[name]:>10.2f}  test_MAE={test_metrics[name]['MAE']:>9.2f}  "
          f"R2={test_metrics[name]['R2']:.4f}  MAPE={test_metrics[name]['MAPE']:.1f}%")

ranked = sorted(val_rmse.items(), key=lambda kv: kv[1])
print("\nRanking by VALIDATION RMSE:", " < ".join(f"{n}({v:.2f})" for n, v in ranked))
names = [n for n, _ in ranked]
ivr = {n: 1.0 / v for n, v in val_rmse.items()}


def ivr_w(members):
    w = np.array([ivr[n] for n in members], dtype=float)
    return w / w.sum()


def variant(label, members, weights):
    ens = WeightedEnsemble([fitted[n] for n in members], np.asarray(weights, dtype=float), members)
    v = calc_metrics(y_valid_raw, np.expm1(ens.predict(X_valid)))
    t = calc_metrics(y_test_raw, np.expm1(ens.predict(X_test)))
    print(f"  {label:<38} val_RMSE={v['RMSE']:>10.2f}  test_MAE={t['MAE']:>9.2f}  R2={t['R2']:.4f}  MAPE={t['MAPE']:.1f}%")
    return {"label": label, "val_rmse": v["RMSE"], "test_mae": t["MAE"],
            "test_rmse": t["RMSE"], "test_r2": t["R2"], "test_mape": t["MAPE"]}


rows = [{"label": "Best single", "val_rmse": val_rmse[names[0]], "test_mae": test_metrics[names[0]]["MAE"],
         "test_rmse": test_metrics[names[0]]["RMSE"], "test_r2": test_metrics[names[0]]["R2"],
         "test_mape": test_metrics[names[0]]["MAPE"]}]
print("\n=== ENSEMBLE VARIANTS ===")
rows.append(variant("Top-2 (inverse-val-RMSE)", names[:2], ivr_w(names[:2])))
rows.append(variant("Top-3 (inverse-val-RMSE) [DEPLOYED]", names[:3], ivr_w(names[:3])))
rows.append(variant("Top-4 (inverse-val-RMSE)", names[:4], ivr_w(names[:4])))
rows.append(variant("Top-3 (equal weights)", names[:3], [1 / 3, 1 / 3, 1 / 3]))
rows.append(variant("All 4 (inverse-val-RMSE)", names[:4], ivr_w(names[:4])))
rows.append(variant("Top-2 (equal weights)", names[:2], [0.5, 0.5]))

import pandas as pd

df = pd.DataFrame(rows)
print("\n=== RANKED BY VALIDATION RMSE ===")
print(df.sort_values("val_rmse").to_string(index=False))
print("\n=== RANKED BY TEST RMSE ===")
print(df.sort_values("test_rmse").to_string(index=False))

out = PROJECT_ROOT / "NOTEBOOKS" / "05_revenue_forecasting_outputs" / "outputs"
out.mkdir(parents=True, exist_ok=True)
df.to_csv(out / "ensemble_experiment_results.csv", index=False)
print("saved", out / "ensemble_experiment_results.csv")
