"""
Analytica — Shared Query Builder Module
Enterprise-grade dynamic dimensional query builder with parameter sanitization,
type safety, and performance-optimized SQL query generation.
"""

from typing import Dict, Any, Tuple, Optional, List


def _clean_param(val: Optional[str]) -> Optional[str]:
    """Sanitize input string parameters, turning default placeholders into None."""
    if not val:
        return None
    cleaned = str(val).strip()
    if cleaned.lower() in ("all", "all_time", "none", "null", "undefined", ""):
        return None
    return cleaned


def has_active_filters(filters: dict, keys: set[str]) -> bool:
    """Return True when filters contain at least one meaningful value for the given keys."""
    if not filters:
        return False
    return any(_clean_param(filters.get(key)) is not None for key in keys)


EXEC_CUBE_KEYS = {"segment", "state", "month"}


def can_use_exec_cube(filters: dict, ignore: set[str] | None = None) -> bool:
    """Return True when every active filter maps onto the precomputed exec cubes
    (rpt_exec_orders / rpt_cube_ssc / rpt_cube_seller).

    Filters that a specific query already consumes as its grouping dimension can
    be passed via ``ignore`` (e.g. 'category' for a per-category report) so they
    do not disqualify the cube path.
    """
    ignored = ignore or set()
    return all(
        _clean_param(value) is None or (key in EXEC_CUBE_KEYS or key in ignored)
        for key, value in filters.items()
    )


def build_exec_cube_where(filters: dict, table_prefix: str = "") -> tuple[str, dict]:
    """Build a WHERE clause + params for the exec cubes from segment/state/month filters.

    Column names in the cubes match the denormalized fact table, so the same
    filter keys apply directly.
    """
    clauses: list[str] = []
    params: dict[str, Any] = {}
    seg = _clean_param(filters.get("segment"))
    st = _clean_param(filters.get("state"))
    mo = _clean_param(filters.get("month"))
    if seg:
        clauses.append(f"{table_prefix}segment = :csegment")
        params["csegment"] = seg
    if st:
        clauses.append(f"{table_prefix}state_code = :cstate")
        params["cstate"] = st.upper()
    if mo:
        clauses.append(f"{table_prefix}month_year = :cmonth")
        params["cmonth"] = mo
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def build_dimensional_query(
    base_select: str,
    base_table: str = "fact_sales fs",
    month: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    segment: Optional[str] = None,
    seller: Optional[str] = None,
    group_by: Optional[str] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Dynamically assemble parameterized SQL query.
    Routes queries with active filters to fact_sales_denormalized for optimal index utilization.
    """
    clean_month = _clean_param(month)
    clean_state = _clean_param(state)
    clean_category = _clean_param(category)
    clean_segment = _clean_param(segment)
    clean_seller = _clean_param(seller)

    params: Dict[str, Any] = {}
    has_filters = any(v is not None for v in [clean_month, clean_state, clean_category, clean_segment, clean_seller])

    if has_filters:
        where_clauses: List[str] = []
        if clean_month:
            where_clauses.append("fs.month_year = :month")
            params["month"] = clean_month
        if clean_state:
            where_clauses.append("fs.state_code = :state")
            params["state"] = clean_state.upper()
        if clean_category:
            where_clauses.append("fs.product_category_name_english = :category")
            params["category"] = clean_category
        if clean_segment:
            where_clauses.append("fs.segment = :segment")
            params["segment"] = clean_segment
        if clean_seller:
            where_clauses.append("fs.seller_id = :seller")
            params["seller"] = clean_seller

        bs = _rewrite_cols(base_select)
        gb = _rewrite_cols(group_by) if group_by else None
        ob = _rewrite_cols(order_by) if order_by else None

        q = f"SELECT {bs} \nFROM fact_sales_denormalized fs"
        if where_clauses:
            q += "\nWHERE " + " AND ".join(where_clauses)
        if gb:
            q += f"\nGROUP BY {gb}"
        if ob:
            q += f"\nORDER BY {ob}"
        if limit and limit > 0:
            q += f"\nLIMIT {limit}"
        return q, params

    joins: List[str] = []
    required_aliases = set()
    for alias in ["dp", "dg", "dd", "dc", "ds"]:
        if (f"{alias}." in base_select) or \
           (group_by and f"{alias}." in group_by) or \
           (order_by and f"{alias}." in order_by):
            required_aliases.add(alias)

    if "dp" in required_aliases:
        joins.append("JOIN dim_product dp ON fs.product_key = dp.product_key")
    if "dd" in required_aliases:
        joins.append("JOIN dim_date dd ON fs.purchase_date_key = dd.date_key")
    if "dc" in required_aliases:
        joins.append("JOIN dim_customer dc ON fs.customer_key = dc.customer_key")
    if "dg" in required_aliases:
        if "dc" not in required_aliases:
            joins.append("JOIN dim_customer dc ON fs.customer_key = dc.customer_key")
        joins.append("JOIN dim_geography dg ON dc.geography_key = dg.geography_key")
    if "ds" in required_aliases:
        joins.append("JOIN dim_seller ds ON fs.seller_key = ds.seller_key")

    q = f"SELECT {base_select} \nFROM {base_table}"
    joins.sort(key=lambda x: 1 if "dim_customer" in x and "dim_geography" not in x else (2 if "dim_geography" in x else 3))
    for join in joins:
        q += f"\n{join}"
    if group_by:
        q += f"\nGROUP BY {group_by}"
    if order_by:
        q += f"\nORDER BY {order_by}"
    if limit and limit > 0:
        q += f"\nLIMIT {limit}"
    return q, params


def _rewrite_cols(sql: str) -> str:
    """Rewrite dimension aliases to match denormalized table structure."""
    for alias in ["dd.", "dp.", "dg.", "dcs.", "dc.", "ds."]:
        sql = sql.replace(alias, "fs.")
    return sql
