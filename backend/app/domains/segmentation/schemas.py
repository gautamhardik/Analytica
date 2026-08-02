from pydantic import BaseModel


class ClusterProfile(BaseModel):
    cluster_id: int
    persona: str
    customer_count: int
    total_revenue: float
    avg_revenue: float
    avg_orders: float
    avg_recency_days: float
    revenue_share_pct: float
    avg_confidence: float
    marketing_strategy: str = ""
    discount_strategy: str = ""
    retention_strategy: str = ""


class PersonaDetail(BaseModel):
    persona: str
    description: str
    customer_count: int
    total_revenue: float
    avg_order_value: float
    top_categories: list[str]
    marketing_strategy: str
    retention_strategy: str


class SegmentationOverview(BaseModel):
    total_customers: int
    cluster_count: int
    persona_count: int
    silhouette_score: float
    calinski_harabasz: float
    davies_bouldin: float
    model_version: str
    training_date: str


class ClusterPoint(BaseModel):
    pc1: float
    pc2: float
    cluster_id: int
    persona: str
    confidence: float


class SegmentationResponse(BaseModel):
    overview: SegmentationOverview
    clusters: list[ClusterProfile]
    personas: list[PersonaDetail]
    pca_projection: list[ClusterPoint]
