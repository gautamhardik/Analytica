"""Segmentation algorithm experiment: KMeans vs GMM vs Agglomerative.

Reuses the deployed trainer's extraction + feature engineering, then compares
algorithms across K on PCA space (same 20K sample) by silhouette, CH, DB.
Writes a results table for review. Does NOT modify any deployed artifacts.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
np.random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import RobustScaler, StandardScaler

from ml.train_segmentation import build_customer_features, extract_customers

df_raw = extract_customers()
df_adv, CLUSTERING_FEATURES = build_customer_features(df_raw)
print(f"customers={len(df_adv):,} features={len(CLUSTERING_FEATURES)}")

X = df_adv.select(CLUSTERING_FEATURES).to_pandas()
X_log = np.log1p(np.maximum(0.0, X))

results = []
for scaler_name, sc in [("StandardScaler", StandardScaler()), ("RobustScaler", RobustScaler())]:
    Xs = sc.fit_transform(X_log)
    pca = PCA(n_components=0.85, random_state=42)
    Xp = pca.fit_transform(Xs)
    rng = np.random.RandomState(42)
    sample = rng.choice(len(Xp), size=min(20000, len(Xp)), replace=False)
    Xs_ = Xp[sample]
    for k in [3, 4, 5, 6, 7, 8]:
        for algo in ["kmeans", "gmm", "agglomerative"]:
            if algo == "kmeans":
                labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(Xs_)
            elif algo == "gmm":
                labels = GaussianMixture(n_components=k, random_state=42, covariance_type="full").fit_predict(Xs_)
            else:
                labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Xs_)
            sil = silhouette_score(Xs_, labels)
            ch = calinski_harabasz_score(Xs_, labels)
            db = davies_bouldin_score(Xs_, labels)
            results.append({"scaler": scaler_name, "k": k, "algo": algo,
                            "silhouette": round(sil, 4), "ch": round(ch, 1), "db": round(db, 4)})
            print(f"  {scaler_name:<14} {algo:<13} K={k}  Sil={sil:.4f}  CH={ch:>9.1f}  DB={db:.4f}")

df = pd.DataFrame(results)
print("\n=== TOP 10 BY SILHOUETTE ===")
print(df.sort_values("silhouette", ascending=False).head(10).to_string(index=False))
print("\n=== BEST PER ALGO (any K, any scaler) ===")
for a in ["kmeans", "gmm", "agglomerative"]:
    best = df[df["algo"] == a].sort_values("silhouette", ascending=False).iloc[0]
    print(f"  {a:<13} K={int(best['k'])} {best['scaler']}  Sil={best['silhouette']}  DB={best['db']}")

out = PROJECT_ROOT / "NOTEBOOKS" / "06_customer_segmentation_outputs" / "outputs"
out.mkdir(parents=True, exist_ok=True)
df.to_csv(out / "algorithm_experiment_results.csv", index=False)
print("saved", out / "algorithm_experiment_results.csv")
