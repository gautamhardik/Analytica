"""
Metrics Collector Engine
In-memory structured metrics tracker for logging pipeline execution metrics,
formatting summary dashboards, and exporting report artifacts.
"""

import time
import pandas as pd
from pathlib import Path

class MetricsCollector:
    def __init__(self):
        self.metrics = {}
        self.pipeline_start_time = None
        self.pipeline_end_time = None

    def start_pipeline(self):
        """Mark pipeline start time."""
        self.pipeline_start_time = time.time()

    def end_pipeline(self):
        """Mark pipeline end time."""
        self.pipeline_end_time = time.time()

    def record_stage(self, stage_name: str, rows_extracted: int, rows_loaded: int, duration_sec: float, warnings_count: int = 0, status: str = "PASS"):
        """Record metrics for a specific pipeline stage."""
        self.metrics[stage_name] = {
            "Rows Extracted": rows_extracted,
            "Rows Loaded": rows_loaded,
            "Duration (s)": round(duration_sec, 2),
            "Warnings": warnings_count,
            "Status": status
        }

    def get_total_duration(self) -> float:
        """Calculate total pipeline execution time in seconds."""
        if self.pipeline_start_time and self.pipeline_end_time:
            return round(self.pipeline_end_time - self.pipeline_start_time, 2)
        return 0.0

    def generate_summary_dataframe(self) -> pd.DataFrame:
        """Convert metrics to a Pandas DataFrame for display and export."""
        records = []
        for stage, data in self.metrics.items():
            records.append({
                "Pipeline Stage": stage,
                "Extracted": f"{data['Rows Extracted']:,}",
                "Loaded": f"{data['Rows Loaded']:,}",
                "Duration (s)": f"{data['Duration (s)']:.2f}",
                "Warnings": data["Warnings"],
                "Status": data["Status"]
            })
        return pd.DataFrame(records)

    def export_csv(self, file_path: Path):
        """Export collected metrics to a CSV file."""
        df = self.generate_summary_dataframe()
        df.to_csv(file_path, index=False)
