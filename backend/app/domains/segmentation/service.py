import csv
import json
import random
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.segmentation import repository
from app.domains.segmentation.schemas import (
    SegmentationOverview, SegmentationResponse, ClusterProfile, PersonaDetail,
    ClusterPoint,
)

ML_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "segmentation"

with open(ML_DIR / "metadata.json") as f:
    _metadata = json.load(f)

with open(ML_DIR / "feature_columns.json") as f:
    _feature_columns = json.load(f)

# Load pre-computed cluster profiles
with open(ML_DIR / "cluster_profiles.json") as f:
    _cluster_data = json.load(f)

# Load pre-computed persona details
with open(ML_DIR / "persona_details.json") as f:
    _persona_data = json.load(f)

# Load pre-computed top categories per persona
with open(ML_DIR / "persona_top_categories.json") as f:
    _persona_cats = json.load(f)

# Load PCA projection (sampled to 2000 points)
_pca_projection: list[ClusterPoint] = []
_pca_csv = ML_DIR / "pca_projection.csv"
if _pca_csv.exists():
    with open(_pca_csv, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            _pca_projection.append(ClusterPoint(
                pc1=float(r["PC1"]),
                pc2=float(r["PC2"]),
                cluster_id=0,
                persona=r["Cluster"],
                confidence=1.0,
            ))
    _pca_projection = random.sample(_pca_projection, min(1000, len(_pca_projection)))

_strategy_map = {
    "VIP Loyalists": {
        "description": "Highest-value customers with strong loyalty and revenue.",
        "marketing_strategy": "Exclusive early product access & VIP tier rewards.",
        "discount_strategy": "Surprise loyalty gifts and flash sales for VIPs.",
        "retention_strategy": "Dedicated account management, priority support, and annual appreciation event.",
    },
    "High-Value Spenders": {
        "description": "Strong revenue contributors with consistent purchasing behavior.",
        "marketing_strategy": "Curated recommendations based on past purchases.",
        "discount_strategy": "Bundled discounts for complementary categories.",
        "retention_strategy": "Subscription to restock alerts for frequently purchased items.",
    },
    "Churned High-Value": {
        "description": "High-value customers who have lapsed. Highest-priority win-back targets given historical spend.",
        "marketing_strategy": "Personalized reactivation campaigns referencing past purchases.",
        "discount_strategy": "Tiered win-back offers capped at first repurchase.",
        "retention_strategy": "Priority re-engagement emails and membership return incentives.",
    },
    "Dormant / Inactive": {
        "description": "Long-dormant, lower-value customers. Low-cost re-engagement only.",
        "marketing_strategy": "Broad win-back emails with general offers.",
        "discount_strategy": "Free shipping on next order to reduce friction.",
        "retention_strategy": "Periodic newsletter nudges; no heavy investment.",
    },
    "Standard / Bargain Shoppers": {
        "description": "Active, lower-value customers who shop on price or occasions.",
        "marketing_strategy": "Deal-focused campaigns and category promotions.",
        "discount_strategy": "Moderate discounts on high-frequency categories.",
        "retention_strategy": "Price-drop alerts and bundle deals.",
    },
    "At-Risk / Inactive Buyers": {
        "description": "Customers with declining or no recent activity. Require re-engagement.",
        "marketing_strategy": "Win-back campaigns with limited-time discounts.",
        "discount_strategy": "Free shipping on next order to reduce friction.",
        "retention_strategy": "Email sequence highlighting new arrivals and personalized picks.",
    },
}


from app.core.cache import get_cache, set_cache, make_cache_key


async def get_segmentation_data(session: AsyncSession) -> SegmentationResponse:
    cache_key = make_cache_key("segmentation_data", {})
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    overview = await repository.get_segmentation_overview(session)

    total_revenue_all = sum(r.get("total_revenue", 0) for r in _cluster_data) or 1

    clusters = []
    for r in _cluster_data:
        cid = r["cluster_id"]
        persona = r["persona"]
        rev = r["total_revenue"]
        strategy = _strategy_map.get(persona, {})
        clusters.append(ClusterProfile(
            cluster_id=cid,
            persona=persona,
            customer_count=r["customer_count"],
            total_revenue=rev,
            avg_revenue=r["avg_revenue"],
            avg_orders=r["avg_orders"],
            avg_recency_days=r["avg_recency_days"],
            revenue_share_pct=round(rev / total_revenue_all * 100, 2),
            avg_confidence=r["avg_confidence"],
            marketing_strategy=strategy.get("marketing_strategy", ""),
            discount_strategy=strategy.get("discount_strategy", ""),
            retention_strategy=strategy.get("retention_strategy", ""),
        ))

    personas = []
    for p in _persona_data:
        pname = p["persona"]
        strategy = _strategy_map.get(pname, {})
        personas.append(PersonaDetail(
            persona=pname,
            description=strategy.get("description", ""),
            customer_count=p["customer_count"],
            total_revenue=p["total_revenue"],
            avg_order_value=p["avg_order_value"],
            top_categories=_persona_cats.get(pname, []),
            marketing_strategy=strategy.get("marketing_strategy", ""),
            retention_strategy=strategy.get("retention_strategy", ""),
        ))

    response = SegmentationResponse(
        overview=SegmentationOverview(
            total_customers=overview.get("total_customers", 0),
            cluster_count=overview.get("cluster_count", 0),
            persona_count=overview.get("persona_count", 0),
            silhouette_score=_metadata.get("silhouette_score", 0),
            calinski_harabasz=_metadata.get("calinski_harabasz", 0),
            davies_bouldin=_metadata.get("davies_bouldin", 0),
            model_version=_metadata.get("model_version", ""),
            training_date=_metadata.get("training_date", ""),
        ),
        clusters=clusters,
        personas=personas,
        pca_projection=_pca_projection,
    )
    set_cache(cache_key, response, ttl_seconds=60)
    return response

