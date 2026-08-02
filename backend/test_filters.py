"""
Comprehensive filter audit script — runs raw SQL against the live database
to cross-check every filter combination for correctness.
"""

import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.core.database import async_session_factory
from app.shared.query_builder import build_dimensional_query, _clean_param

async def run_query(session, sql, params=None):
    result = await session.execute(text(sql), params or {})
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def audit():
    async with async_session_factory() as session:
        # ── 1. Schema check: does fact_sales_denormalized exist and what columns? ──
        print("=" * 70)
        print("1. SCHEMA CHECK: fact_sales_denormalized")
        print("=" * 70)
        cols = await run_query(session, """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'fact_sales_denormalized'
            ORDER BY ORDINAL_POSITION
        """)
        for c in cols:
            print(f"  {c['COLUMN_NAME']:40s} {c['DATA_TYPE']}")
        if not cols:
            print("  ** TABLE DOES NOT EXIST **")

        # ── 2. Row count + distinct values ──
        print("\n" + "=" * 70)
        print("2. ROW COUNT & DISTINCT DIMENSIONS in fact_sales_denormalized")
        print("=" * 70)
        stats = await run_query(session, """
            SELECT
                COUNT(*) AS total_rows,
                COUNT(DISTINCT order_id) AS distinct_orders,
                COUNT(DISTINCT customer_unique_id) AS distinct_customers,
                COUNT(DISTINCT month_year) AS distinct_months,
                COUNT(DISTINCT state_code) AS distinct_states,
                COUNT(DISTINCT product_category_name_english) AS distinct_categories,
                COUNT(DISTINCT segment) AS distinct_segments,
                COUNT(DISTINCT seller_id) AS distinct_sellers
            FROM fact_sales_denormalized
        """)
        for k, v in stats[0].items():
            print(f"  {k:40s} {v}")

        # ── 3. Month filter test ──
        print("\n" + "=" * 70)
        print("3. MONTH FILTER TEST: month=2017-10")
        print("=" * 70)
        for label, sql_params in [
            ("KPI query (month only)", {
                "sql": """
                    SELECT
                        SUM(fs.total_sales_amount) AS total_revenue,
                        COUNT(DISTINCT fs.order_id) AS total_orders,
                        COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
                        CASE WHEN COUNT(DISTINCT fs.order_id) > 0
                             THEN SUM(fs.total_sales_amount) / COUNT(DISTINCT fs.order_id)
                             ELSE 0 END AS average_order_value
                    FROM fact_sales_denormalized fs
                    WHERE fs.month_year = :month
                """,
                "params": {"month": "2017-10"}
            }),
            ("KPI query (no filter)", {
                "sql": """
                    SELECT
                        SUM(fs.total_sales_amount) AS total_revenue,
                        COUNT(DISTINCT fs.order_id) AS total_orders,
                        COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
                        CASE WHEN COUNT(DISTINCT fs.order_id) > 0
                             THEN SUM(fs.total_sales_amount) / COUNT(DISTINCT fs.order_id)
                             ELSE 0 END AS average_order_value
                    FROM fact_sales_denormalized fs
                """,
                "params": {}
            }),
        ]:
            rows = await run_query(session, sql_params["sql"], sql_params["params"])
            print(f"\n  [{label}]")
            if rows:
                for k, v in rows[0].items():
                    print(f"    {k:40s} {v}")
            else:
                print("    ** NO ROWS RETURNED **")

        # ── 4. Customer snapshot test (month filter) ──
        print("\n" + "=" * 70)
        print("4. CUSTOMER SNAPSHOT TEST: month=2017-10")
        print("=" * 70)
        sub_sql, sub_params = build_dimensional_query(
            base_select="fs.customer_unique_id, COUNT(DISTINCT fs.order_id) as order_count",
            group_by="fs.customer_unique_id",
            month="2017-10"
        )
        print(f"\n  Generated sub-query:\n    {sub_sql}")
        print(f"  Params: {sub_params}")
        full_query = f"""
            SELECT
                SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
                SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END) AS one_time_customers,
                COUNT(*) AS total_customers
            FROM ({sub_sql}) AS customer_orders
        """
        rows = await run_query(session, full_query, sub_params)
        print(f"\n  [Customer Snapshot Result]")
        if rows:
            for k, v in rows[0].items():
                print(f"    {k:40s} {v}")
        else:
            print("    ** NO ROWS RETURNED **")

        # ── 5. Reporting table comparison ──
        print("\n" + "=" * 70)
        print("5. REPORTING TABLE vs DIMENSIONAL (month=2017-10)")
        print("=" * 70)
        for label, sql, params in [
            ("reporting_sales_summary (2017-10)", """
                SELECT total_revenue, total_orders, total_customers
                FROM reporting_sales_summary
                WHERE order_month = :month
            """, {"month": "2017-10"}),
            ("reporting_customer_overview", """
                SELECT repeat_customers, one_time_customers, total_customers
                FROM reporting_customer_overview LIMIT 1
            """, {}),
            ("reporting_customer_overview (segment/state only)", """
                SELECT *
                FROM reporting_filter_customer_orders
                WHERE state_code = 'SP'
                LIMIT 5
            """, {}),
        ]:
            rows = await run_query(session, sql, params)
            print(f"\n  [{label}]")
            if rows:
                for r in rows:
                    print(f"    {r}")
            else:
                print("    ** NO ROWS **")

        # ── 6. State filter test ──
        print("\n" + "=" * 70)
        print("6. STATE FILTER TEST: state=SP")
        print("=" * 70)
        q, p = build_dimensional_query(
            base_select="""
                SUM(fs.total_sales_amount) AS total_revenue,
                COUNT(DISTINCT fs.order_id) AS total_orders,
                COUNT(DISTINCT fs.customer_unique_id) AS total_customers
            """,
            state="SP"
        )
        print(f"\n  Query: {q}")
        print(f"  Params: {p}")
        rows = await run_query(session, q, p)
        if rows:
            for k, v in rows[0].items():
                print(f"    {k:40s} {v}")

        # ── 7. Multi-filter test ──
        print("\n" + "=" * 70)
        print("7. MULTI-FILTER TEST: month=2017-10 + state=SP")
        print("=" * 70)
        q, p = build_dimensional_query(
            base_select="""
                SUM(fs.total_sales_amount) AS total_revenue,
                COUNT(DISTINCT fs.order_id) AS total_orders,
                COUNT(DISTINCT fs.customer_unique_id) AS total_customers
            """,
            month="2017-10", state="SP"
        )
        print(f"\n  Query: {q}")
        print(f"  Params: {p}")
        rows = await run_query(session, q, p)
        if rows:
            for k, v in rows[0].items():
                print(f"    {k:40s} {v}")

        # ── 8. Category filter test ──
        print("\n" + "=" * 70)
        print("8. CATEGORY FILTER TEST: category=health_beauty")
        print("=" * 70)
        q, p = build_dimensional_query(
            base_select="""
                SUM(fs.total_sales_amount) AS total_revenue,
                COUNT(DISTINCT fs.order_id) AS total_orders,
                COUNT(DISTINCT fs.customer_unique_id) AS total_customers
            """,
            category="health_beauty"
        )
        print(f"\n  Query: {q}")
        print(f"  Params: {p}")
        rows = await run_query(session, q, p)
        if rows:
            for k, v in rows[0].items():
                print(f"    {k:40s} {v}")

        # ── 9. Segment filter test ──
        print("\n" + "=" * 70)
        print("9. SEGMENT FILTER TEST")
        print("=" * 70)
        for seg in ["vip", "new", "repeat"]:
            q, p = build_dimensional_query(
                base_select="""
                    SUM(fs.total_sales_amount) AS total_revenue,
                    COUNT(DISTINCT fs.order_id) AS total_orders,
                    COUNT(DISTINCT fs.customer_unique_id) AS total_customers
                """,
                segment=seg
            )
            rows = await run_query(session, q, p)
            if rows:
                r = rows[0]
                rev = r['total_revenue'] or 0
                ord = r['total_orders'] or 0
                cust = r['total_customers'] or 0
                print(f"  segment={seg:20s}  rev={rev:>14.2f}  orders={ord:>8}  cust={cust:>8}")

        # ── 10. Seller filter test ──
        print("\n" + "=" * 70)
        print("10. SELLER FILTER TEST")
        print("=" * 70)
        sample = await run_query(session, "SELECT DISTINCT seller_id FROM fact_sales_denormalized LIMIT 3")
        for s in sample:
            sid = s["seller_id"]
            q, p = build_dimensional_query(
                base_select="""
                    SUM(fs.total_sales_amount) AS total_revenue,
                    COUNT(DISTINCT fs.order_id) AS total_orders,
                    COUNT(DISTINCT fs.customer_unique_id) AS total_customers
                """,
                seller=sid
            )
            rows = await run_query(session, q, p)
            if rows:
                r = rows[0]
                print(f"  seller={sid:40s}  rev={r['total_revenue']:>12.2f}  orders={r['total_orders']:>6}  cust={r['total_customers']:>6}")

        # ── 11. All 5 filters combined ──
        print("\n" + "=" * 70)
        print("11. ALL 5 FILTERS: month=2017-10 + state=SP + category=health_beauty + segment=VIP + seller=<first>")
        print("=" * 70)
        seller_id = sample[0]["seller_id"] if sample else "none"
        q, p = build_dimensional_query(
            base_select="""
                SUM(fs.total_sales_amount) AS total_revenue,
                COUNT(DISTINCT fs.order_id) AS total_orders,
                COUNT(DISTINCT fs.customer_unique_id) AS total_customers
            """,
            month="2017-10", state="SP", category="health_beauty", segment="VIP", seller=seller_id
        )
        print(f"\n  Query:\n    {q}")
        print(f"  Params: {p}")
        rows = await run_query(session, q, p)
        if rows:
            for k, v in rows[0].items():
                print(f"    {k:40s} {v}")

        # ── 12. Monthly trend test ──
        print("\n" + "=" * 70)
        print("12. MONTHLY TREND: month=2017-10 (should show only Oct 2017)")
        print("=" * 70)
        q, p = build_dimensional_query(
            base_select="""
                dd.month_year AS order_month,
                dd.year_number,
                dd.month_number,
                SUM(fs.total_sales_amount) AS total_revenue,
                COUNT(DISTINCT fs.order_id) AS total_orders,
                COUNT(DISTINCT fs.customer_unique_id) AS total_customers
            """,
            group_by="dd.month_year, dd.year_number, dd.month_number",
            order_by="dd.year_number, dd.month_number",
            month="2017-10"
        )
        print(f"\n  Query:\n    {q}")
        print(f"  Params: {p}")
        rows = await run_query(session, q, p)
        for r in rows:
            print(f"    {r}")

        # ── 13. Geography test (state filter ignored) ──
        print("\n" + "=" * 70)
        print("13. GEOGRAPHY: state filter should be ignored")
        print("=" * 70)
        q, p = build_dimensional_query(
            base_select="""
                dg.state_code,
                SUM(fs.total_sales_amount) AS total_revenue,
                COUNT(DISTINCT fs.order_id) AS total_orders,
                COUNT(DISTINCT fs.customer_unique_id) AS total_customers
            """,
            group_by="dg.state_code",
            order_by="total_revenue DESC",
            limit=5,
            state="SP"
        )
        print(f"\n  Query:\n    {q}")
        print(f"  Params: {p}")
        rows = await run_query(session, q, p)
        for r in rows:
            print(f"    {r}")

        # ── 14. Customer snapshot for all filter combos ──
        print("\n" + "=" * 70)
        print("14. CUSTOMER SNAPSHOT: all filter combos")
        print("=" * 70)
        combos = [
            ("no filter", {}),
            ("month=2017-10", {"month": "2017-10"}),
            ("state=SP", {"state": "SP"}),
            ("category=health_beauty", {"category": "health_beauty"}),
            ("segment=VIP", {"segment": "VIP"}),
            ("month+state", {"month": "2017-10", "state": "SP"}),
            ("month+category", {"month": "2017-10", "category": "health_beauty"}),
            ("month+state+category", {"month": "2017-10", "state": "SP", "category": "health_beauty"}),
        ]
        for label, filters in combos:
            has_filter = any(_clean_param(v) is not None for v in filters.values())
            if not has_filter:
                rows = await run_query(session, """
                    SELECT repeat_customers, one_time_customers, total_customers
                    FROM reporting_customer_overview LIMIT 1
                """)
            else:
                # Check if only segment/state
                only_seg_state = set(filters.keys()).issubset({"segment", "state"})
                if only_seg_state:
                    col_map = {"segment": "segment", "state": "state_code"}
                    where = " AND ".join(f"{col_map.get(k, k)} = :{k}" for k in filters)
                    rows = await run_query(session, f"""
                        SELECT
                            COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
                            COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS one_time_customers,
                            COUNT(*) AS total_customers
                        FROM reporting_filter_customer_orders
                        WHERE {where}
                    """, filters)
                else:
                    sub_q, sub_p = build_dimensional_query(
                        base_select="fs.customer_unique_id, COUNT(DISTINCT fs.order_id) as order_count",
                        group_by="fs.customer_unique_id",
                        **filters
                    )
                    rows = await run_query(session, f"""
                        SELECT
                            SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
                            SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END) AS one_time_customers,
                            COUNT(*) AS total_customers
                        FROM ({sub_q}) AS customer_orders
                    """, sub_p)
            r = rows[0] if rows else {}
            print(f"  {label:30s}  repeat={r.get('repeat_customers',0):>8}  one_time={r.get('one_time_customers',0):>8}  total={r.get('total_customers',0):>8}")

        # ── 15. Compare executive KPI endpoint vs direct query ──
        print("\n" + "=" * 70)
        print("15. EXECUTIVE KPI ENDPOINT vs DIRECT QUERY (month=2017-10)")
        print("=" * 70)
        from app.domains.executive.repository import get_overall_kpis, get_customer_snapshot
        kpis = await get_overall_kpis(session, month="2017-10")
        print(f"  get_overall_kpis(month=2017-10): {kpis}")
        snap = await get_customer_snapshot(session, month="2017-10")
        print(f"  get_customer_snapshot(month=2017-10): {snap}")

        print("\n\nDone.")


if __name__ == "__main__":
    asyncio.run(audit())
