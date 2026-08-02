"""
Analytica — Executive Summary Schemas
"""

from pydantic import BaseModel


class ReportSection(BaseModel):
    title: str
    summary: str
    sentiment: str
    metrics: list[str]
    recommendation: str


class ExecutiveReport(BaseModel):
    generated_at: str = ""
    executive_summary: str
    sections: list[ReportSection]
    key_risks: list[str]
    opportunities: list[str]
    overall_sentiment: str
