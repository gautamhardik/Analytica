#!/usr/bin/env python
"""
Customer Segmentation Model Comparison & Deployment Trainer
==========================================================
Compares K-Means across K values (2..8) and two scaling strategies
(log1p+StandardScaler vs log1p+RobustScaler) on RFM-style features,
selects the best configuration by silhouette/stability, fits the final
model, and writes all artifacts consumed by the backend segmentation
service under backend/app/ml/segmentation, plus updates the
customer_segment_ml table.

Usage:
    python ml/train_segmentation.py
"""
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import RobustScaler, StandardScaler
from sqlalchemy import text

warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ETL.config import get_db_engine

N_CLUSTERS_RANGE = range(2, 9)
MIN_ACTIONABLE_SEGMENTS = 4  # require >=4 segments so each persona gets a differentiated strategy
RFM_REFERENCE_DATE = date(2018, 9, 5)
STABILITY_SEEDS = [42, 100, 2024, 777, 999]

ML_DIR = PROJECT_ROOT / "backend" / "app" / "ml" / "segmentation"
ML_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data extraction & feature engineering
# ---------------------------------------------------------------------------
def extract_customers():
    engine = get_db_engine()
    SQL_QUERY = """
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT f.order_id) AS number_of_orders,
        SUM(f.total_sales_amount) AS total_revenue,
        AVG(f.total_sales_amount) AS average_order_value,
        SUM(f.quantity) AS total_items_purchased,
        COUNT(DISTINCT f.product_key) AS unique_products,
        COUNT(DISTINCT p.product_category_name_english) AS unique_categories,
        AVG(f.freight_value) AS avg_freight,
        MIN(d.full_date) AS first_purchase_date,
        MAX(d.full_date) AS last_purchase_date,
        COALESCE(MAX(g.state_code), 'UNKNOWN') AS customer_state
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_date d ON f.purchase_date_key = d.date_key
    JOIN dim_product p ON f.product_key = p.product_key
    LEFT JOIN dim_geography g ON c.geography_key = g.geography_key
    GROUP BY c.customer_unique_id;
    """
    with engine.connect() as conn:
        pandas_raw = pd.read_sql(SQL_QUERY, conn)
    return pl.from_pandas(pandas_raw).with_columns([
        pl.col("first_purchase_date").cast(pl.Date),
        pl.col("last_purchase_date").cast(pl.Date),
        pl.col("total_revenue").cast(pl.Float64),
        pl.col("average_order_value").cast(pl.Float64),
        pl.col("number_of_orders").cast(pl.Int64),
        pl.col("total_items_purchased").cast(pl.Int64),
        pl.col("unique_products").cast(pl.Int64),
        pl.col("unique_categories").cast(pl.Int64),
        pl.col("avg_freight").cast(pl.Float64),
    ])


def build_customer_features(df_raw):
    df_cust = df_raw.with_columns([
        (pl.lit(RFM_REFERENCE_DATE) - pl.col("last_purchase_date")).dt.total_days().alias("recency_days"),
        (pl.col("last_purchase_date") - pl.col("first_purchase_date")).dt.total_days().alias("customer_tenure_days"),
        (pl.col("total_items_purchased") / pl.col("number_of_orders")).alias("items_per_order"),
    ])

    df_adv = df_cust.with_columns([
        (pl.col("unique_categories") / pl.col("total_items_purchased")).alias("category_diversity_ratio"),
        (pl.col("unique_products") / pl.col("total_items_purchased")).alias("product_diversity_ratio"),
        (pl.col("avg_freight") / pl.col("average_order_value").clip(lower_bound=1.0)).alias("freight_revenue_ratio"),
        (pl.col("customer_tenure_days") / pl.col("number_of_orders").clip(lower_bound=1.0)).alias("avg_purchase_interval_days"),
    ])

    CLUSTERING_FEATURES = [
        "recency_days", "number_of_orders", "total_revenue", "average_order_value",
        "total_items_purchased", "unique_categories", "avg_freight",
        "items_per_order", "category_diversity_ratio", "freight_revenue_ratio", "customer_tenure_days",
    ]
    return df_adv, CLUSTERING_FEATURES


def assign_persona(cluster_profiles):
    """Map each cluster to a distinct, actionable persona.

    Personas are derived from a cluster's aggregate RFM profile along two
    axes: value (avg revenue vs the portfolio average, plus repeat rate) and
    engagement risk (recency vs the median cluster recency).  This replaces
    the previous rule, which let several very different clusters collapse
    into a single 'At-Risk / Inactive Buyers' bucket (e.g. a R$61 dormant
    cluster vs a R$238 churned high-value cluster).
    """
    portfolio_avg_rev = cluster_profiles["total_segment_revenue"].sum() / cluster_profiles["customer_count"].sum()
    rec_med = cluster_profiles["avg_recency"].median()
    repeat_threshold = cluster_profiles["avg_orders"].median() + 0.5

    def _base_name(row):
        high_value = row["avg_revenue"] >= portfolio_avg_rev
        repeat = row["avg_orders"] > repeat_threshold
        high_recency = row["avg_recency"] > rec_med

        if repeat and high_value:
            return "VIP Loyalists"
        if high_value and high_recency:
            return "Churned High-Value"
        if high_value:
            return "High-Value Spenders"
        if high_recency:
            return "Dormant / Inactive"
        return "Standard / Bargain Shoppers"

    cluster_profiles["persona_name"] = cluster_profiles.apply(_base_name, axis=1)

    # Guarantee a unique persona per cluster.  If two clusters land in the
    # same bucket, differentiate them by how long they have lapsed.
    name_counts = cluster_profiles["persona_name"].value_counts().to_dict()
    for name, cnt in name_counts.items():
        if cnt > 1:
            dup = cluster_profiles[cluster_profiles["persona_name"] == name].sort_values(
                "avg_recency", ascending=False)
            for j, idx in enumerate(dup.index):
                cluster_profiles.at[idx, "persona_name"] = (
                    name if j == 0 else f"{name} (Long-Term)" if name != "VIP Loyalists" else f"{name} (Core)")
    return cluster_profiles


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("CUSTOMER SEGMENTATION MODEL COMPARISON & DEPLOYMENT")
    print("=" * 70)

    df_raw = extract_customers()
    df_adv, CLUSTERING_FEATURES = build_customer_features(df_raw)
    print(f"Extracted {len(df_adv):,} customers | {len(CLUSTERING_FEATURES)} clustering features")

    X_features = df_adv.select(CLUSTERING_FEATURES).to_pandas()
    X_log = np.log1p(np.maximum(0.0, X_features))

    # ---- scaling strategy comparison ----
    scalers = {"StandardScaler": StandardScaler(), "RobustScaler": RobustScaler()}
    scaled = {name: sc.fit_transform(X_log) for name, sc in scalers.items()}

    # PCA per scaling strategy (0.85 variance)
    pca_models = {}
    X_pca_set = {}
    for name, X_scaled in scaled.items():
        pca = PCA(n_components=0.85, random_state=SEED)
        X_pca_set[name] = pca.fit_transform(X_scaled)
        pca_models[name] = pca

    # ---- optimal K selection per strategy (silhouette on sample) ----
    np.random.seed(SEED)
    sample_idx = np.random.choice(len(X_pca_set["StandardScaler"]),
                                  size=min(20000, len(X_pca_set["StandardScaler"])), replace=False)

    best_config = None
    for scaler_name in scalers:
        X_pca = X_pca_set[scaler_name]
        X_pca_sample = X_pca[sample_idx]
        for k in N_CLUSTERS_RANGE:
            km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
            labels = km.fit_predict(X_pca_sample)
            sil = silhouette_score(X_pca_sample, labels)
            ch = calinski_harabasz_score(X_pca_sample, labels)
            db = davies_bouldin_score(X_pca_sample, labels)
            print(f"  {scaler_name:<14} K={k}  Silhouette={sil:.4f}  CH={ch:>10.2f}  DB={db:.4f}")
            # Select best silhouette among configurations with >=4 segments,
            # so persona strategies stay actionable (avoid 2-3 mega-clusters).
            if k < MIN_ACTIONABLE_SEGMENTS:
                continue
            score = sil
            if best_config is None or score > best_config["score"]:
                best_config = {
                    "score": score, "scaler_name": scaler_name, "k": k,
                    "silhouette": sil, "ch": ch, "db": db,
                }

    print(f"\n>>> BEST CONFIG: {best_config['scaler_name']}, K={best_config['k']} "
          f"(silhouette {best_config['silhouette']:.4f}, min {MIN_ACTIONABLE_SEGMENTS} segments)")

    # ---- final model on best config ----
    scaler_name = best_config["scaler_name"]
    OPTIMAL_K = best_config["k"]
    scaler = scalers[scaler_name]
    pca = pca_models[scaler_name]
    X_scaled = scaled[scaler_name]
    X_pca = X_pca_set[scaler_name]
    X_pca_sample = X_pca[sample_idx]

    kmeans = KMeans(n_clusters=OPTIMAL_K, random_state=SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(X_pca)
    df_adv = df_adv.with_columns(pl.Series("cluster_id", cluster_labels))

    # ---- multi-seed stability ----
    base_labels_sample = cluster_labels[sample_idx]
    stability_results = []
    for s in STABILITY_SEEDS:
        km_s = KMeans(n_clusters=OPTIMAL_K, random_state=s, n_init=10)
        lbl_s = km_s.fit_predict(X_pca_sample)
        ari = adjusted_rand_score(base_labels_sample, lbl_s)
        stability_results.append({"Seed": s, "ARI_vs_Base": ari})
    df_stability = pd.DataFrame(stability_results)
    mean_ari = df_stability["ARI_vs_Base"].mean()
    print(f"Mean stability ARI across seeds: {mean_ari:.4f}")

    final_sil = silhouette_score(X_pca_sample, cluster_labels[sample_idx])
    final_ch = calinski_harabasz_score(X_pca_sample, cluster_labels[sample_idx])
    final_db = davies_bouldin_score(X_pca_sample, cluster_labels[sample_idx])

    # ---- profiling & personas ----
    total_portfolio_revenue = df_adv["total_revenue"].sum()
    total_portfolio_customers = len(df_adv)

    cluster_profiles = df_adv.group_by("cluster_id").agg([
        pl.count("customer_unique_id").alias("customer_count"),
        pl.col("total_revenue").sum().alias("total_segment_revenue"),
        pl.col("recency_days").mean().alias("avg_recency"),
        pl.col("number_of_orders").mean().alias("avg_orders"),
        pl.col("total_revenue").mean().alias("avg_revenue"),
        pl.col("average_order_value").mean().alias("avg_aov"),
        pl.col("total_items_purchased").mean().alias("avg_items"),
        pl.col("unique_categories").mean().alias("avg_categories"),
        pl.col("avg_freight").mean().alias("avg_freight"),
    ]).sort("cluster_id").to_pandas()
    cluster_profiles["pct_customers"] = cluster_profiles["customer_count"] / total_portfolio_customers * 100
    cluster_profiles["revenue_share_pct"] = cluster_profiles["total_segment_revenue"] / total_portfolio_revenue * 100
    cluster_profiles = assign_persona(cluster_profiles)
    persona_map = dict(zip(cluster_profiles["cluster_id"], cluster_profiles["persona_name"]))
    df_adv = df_adv.with_columns(
        pl.col("cluster_id").map_elements(lambda cid: persona_map[cid], return_dtype=pl.Utf8).alias("persona_name")
    )

    print("\n--- Final Segment Quality Table ---")
    for _, r in cluster_profiles.iterrows():
        print(f"  Cluster {r['cluster_id']} [{r['persona_name']}]: {r['customer_count']:,} customers, "
              f"share={r['pct_customers']:.1f}%, rev_share={r['revenue_share_pct']:.1f}%")

    # ---- write backend artifacts ----
    print("\nWriting artifacts to", ML_DIR)

    # cluster profiles (backend format)
    backend_clusters = []
    for _, r in cluster_profiles.iterrows():
        backend_clusters.append({
            "cluster_id": int(r["cluster_id"]),
            "persona": r["persona_name"],
            "customer_count": int(r["customer_count"]),
            "total_revenue": round(float(r["total_segment_revenue"]), 2),
            "avg_revenue": round(float(r["avg_revenue"]), 2),
            "avg_orders": round(float(r["avg_orders"]), 2),
            "avg_recency_days": round(float(r["avg_recency"]), 2),
            "avg_confidence": 1.0,
        })
    with open(ML_DIR / "cluster_profiles.json", "w") as f:
        json.dump(backend_clusters, f, indent=2)

    # persona details
    persona_agg = df_adv.group_by("persona_name").agg([
        pl.count("customer_unique_id").alias("customer_count"),
        pl.col("total_revenue").sum().alias("total_revenue"),
        pl.col("average_order_value").mean().alias("avg_order_value"),
    ]).to_pandas()
    persona_details = [{
        "persona": r["persona_name"],
        "customer_count": int(r["customer_count"]),
        "total_revenue": round(float(r["total_revenue"]), 2),
        "avg_order_value": round(float(r["avg_order_value"]), 2),
    } for _, r in persona_agg.iterrows()]
    with open(ML_DIR / "persona_details.json", "w") as f:
        json.dump(persona_details, f, indent=2)

    # top categories per persona
    persona_cats = _top_categories_per_persona(df_adv, CLUSTERING_FEATURES)
    with open(ML_DIR / "persona_top_categories.json", "w") as f:
        json.dump(persona_cats, f, indent=2)

    # metadata
    metadata = {
        "model_version": "v1.2",
        "k": OPTIMAL_K,
        "training_date": str(date.today()),
        "silhouette_score": round(float(final_sil), 4),
        "calinski_harabasz": round(float(final_ch), 2),
        "davies_bouldin": round(float(final_db), 4),
        "stability_mean_ari": round(float(mean_ari), 4),
        "total_customers": len(df_adv),
        "pca_components": int(X_pca.shape[1]),
        "scaler": scaler_name,
        "personas": {str(k): v for k, v in persona_map.items()},
    }
    with open(ML_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # feature columns
    with open(ML_DIR / "feature_columns.json", "w") as f:
        json.dump(CLUSTERING_FEATURES, f, indent=2)

    # PCA projection for frontend scatter
    pca_2d = PCA(n_components=2, random_state=SEED).fit_transform(X_scaled)
    df_pca_viz = pd.DataFrame({
        "PC1": pca_2d[:, 0],
        "PC2": pca_2d[:, 1],
        "Cluster": df_adv["persona_name"].to_pandas(),
    })
    df_pca_viz.to_csv(ML_DIR / "pca_projection.csv", index=False)

    # model pickles
    import joblib
    joblib.dump(kmeans, ML_DIR / "kmeans_v1.2.pkl")
    joblib.dump(scaler, ML_DIR / "scaler_v1.2.pkl")
    joblib.dump(pca, ML_DIR / "pca_v1.2.pkl")

    # ---- database write (customer_segment_ml) ----
    _write_db(df_adv, CLUSTERING_FEATURES, kmeans, X_pca, cluster_labels)

    # ---- CSV exports for notebook reference ----
    output_dir = PROJECT_ROOT / "NOTEBOOKS" / "06_customer_segmentation_outputs" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    df_adv.select(["customer_unique_id", "cluster_id", "persona_name"] + CLUSTERING_FEATURES).to_pandas().to_csv(
        output_dir / "customer_segments.csv", index=False)
    cluster_profiles.to_csv(output_dir / "cluster_profiles.csv", index=False)
    df_stability.to_csv(output_dir / "cluster_stability_results.csv", index=False)
    pd.DataFrame([{
        "Optimal_K": OPTIMAL_K,
        "Silhouette_Score": final_sil,
        "Calinski_Harabasz_Index": final_ch,
        "Davies_Bouldin_Index": final_db,
        "Mean_Stability_ARI": mean_ari,
        "Scaler": scaler_name,
    }]).to_csv(output_dir / "evaluation_metrics.csv", index=False)

    print("Done. DB rows:", len(df_adv))


def _top_categories_per_persona(df_adv, _features):
    engine = get_db_engine()
    ids = df_adv.select(["customer_unique_id", "persona_name"]).to_pandas()
    with engine.connect() as conn:
        table = pd.read_sql("""
            SELECT c.customer_unique_id, p.product_category_name_english AS category
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_key = c.customer_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE p.product_category_name_english IS NOT NULL
        """, conn)
    merged = table.merge(ids, on="customer_unique_id", how="inner")
    merged = merged.drop_duplicates(["customer_unique_id", "persona_name", "category"])
    result = {}
    for persona in sorted(merged["persona_name"].dropna().unique()):
        sub = merged[merged["persona_name"] == persona]
        top = sub["category"].value_counts().head(5).index.tolist()
        result[persona] = top
    return result


def _write_db(df_adv, CLUSTERING_FEATURES, kmeans, X_pca, cluster_labels):
    engine = get_db_engine()
    MODEL_VERSION = "v1.2"
    distances = kmeans.transform(X_pca)
    own = distances[np.arange(len(distances)), cluster_labels]
    # Distance to the nearest OTHER cluster center (assignment margin).
    mask = np.ones_like(distances, dtype=bool)
    mask[np.arange(len(distances)), cluster_labels] = False
    second = np.where(mask, distances, np.inf).min(axis=1)
    # Confidence from assignment margin: 1.0 = very close to own center relative
    # to the runner-up, 0.0 = centers are equidistant.
    confidence_scores = 1.0 - (own / np.maximum(second, 1e-10))
    confidence_scores = np.clip(confidence_scores, 0.0, 1.0)

    df_db = df_adv.select(["customer_unique_id", "cluster_id", "persona_name"]).to_pandas()
    df_db["distance_to_center"] = distances[np.arange(len(distances)), cluster_labels]
    df_db["confidence_score"] = confidence_scores
    df_db["model_version"] = MODEL_VERSION

    # One row per customer_unique_id (dim_customer has multiple rows per unique id,
    # so keying the ML persona table by customer_key inflated counts and broke 1:1).
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE customer_segment_ml"))
        for _, row in df_db.iterrows():
            conn.execute(
                text("""
                    INSERT INTO customer_segment_ml
                        (customer_unique_id, cluster_id, persona, distance_to_center, confidence_score, model_version)
                    VALUES (:cuid, :cl, :pn, :dc, :cs, :mv)
                """),
                {
                    "cuid": str(row["customer_unique_id"]),
                    "cl": int(row["cluster_id"]),
                    "pn": str(row["persona_name"]),
                    "dc": float(row["distance_to_center"]),
                    "cs": float(row["confidence_score"]),
                    "mv": MODEL_VERSION,
                },
            )
    print(f"DB: {len(df_db)} rows written to customer_segment_ml ({MODEL_VERSION})")

if __name__ == "__main__":
    main()
