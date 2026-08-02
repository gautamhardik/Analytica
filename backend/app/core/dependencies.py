"""
Analytica — Shared FastAPI Dependencies
Reusable dependency injection callables.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency for route handlers."""
    async for session in get_session():
        yield session
