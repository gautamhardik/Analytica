"""
Analytica — Reports Schemas
"""

from pydantic import BaseModel


class ReportDefinition(BaseModel):
    """A pre-built report available for viewing/export."""
    id: str
    name: str
    description: str
    source_table: str
    category: str


class ReportsListResponse(BaseModel):
    """List of available reports."""
    reports: list[ReportDefinition]
