"""
Analytica — Reports Router
GET /api/v1/reports — List and access pre-built reports.
"""

import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.shared.schemas import APIResponse, PaginatedResponse, PaginationMeta
from app.domains.reports.schemas import ReportsListResponse
from app.domains.reports.service import get_report_list, get_report_by_id, get_report_data

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=APIResponse[ReportsListResponse])
async def list_reports():
    """List all available pre-built reports."""
    data = get_report_list()
    return APIResponse(data=data)


@router.get("/{report_id}/data")
async def report_data(
    report_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
):
    """Fetch paginated data for a specific report."""
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    rows, total = await get_report_data(session, report.source_table, page, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedResponse(
        data=rows,
        pagination=PaginationMeta(
            page=page, page_size=page_size,
            total_items=total, total_pages=total_pages,
        ),
    )


@router.get("/{report_id}/export")
async def export_report_csv(
    report_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Export all records for a report as CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    rows, _ = await get_report_data(session, report.source_table, page=1, page_size=10000)
    if not rows:
        output = io.StringIO()
        output.write("No data available\n")
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={report_id}.csv"})

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_id}.csv"},
    )

