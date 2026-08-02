"""
Custom Exception Classes for the ETL Package
"""

class ETLError(Exception):
    """Base exception class for all ETL pipeline errors."""
    pass

class ExtractionError(ETLError):
    """Raised when data extraction from raw CSV or database fails."""
    pass

class TransformationError(ETLError):
    """Raised when data transformation, join, or measure calculation fails."""
    pass

class ValidationError(ETLError):
    """Raised when a data quality, schema, or referential integrity check fails."""
    pass

class LoadError(ETLError):
    """Raised when loading data into MySQL database fails."""
    pass
