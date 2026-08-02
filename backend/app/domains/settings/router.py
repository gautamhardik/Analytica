from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, constr
from app.core.config import settings
from app.core.database import async_session_factory
from sqlalchemy import text

router = APIRouter()

ALLOWED_THEMES = {"olist", "midnight", "emerald"}


def require_admin(request: Request):
    """Gate mutations behind the configured admin token.

    Accepts the token via either `X-Admin-Token` header or
    `Authorization: Bearer <token>` so it works with the router-level
    auth dependency and the frontend client.
    """
    if not settings.admin_token:
        # No admin token configured -> open for demo convenience
        return True
    x_admin = request.headers.get("X-Admin-Token")
    authz = request.headers.get("Authorization", "")
    bearer = authz.split(" ", 1)[1] if authz.lower().startswith("bearer ") else None
    provided = x_admin or bearer
    if not provided or provided != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class ThemePayload(BaseModel):
    theme: constr(min_length=1, max_length=64)


@router.get("/user/theme")
async def read_theme():
    """Return the currently stored theme (demo)."""
    try:
        async with async_session_factory() as session:
            res = await session.execute(text("SELECT `value` FROM preferences WHERE `key` = 'theme' LIMIT 1"))
            row = res.fetchone()
            theme = row[0] if row else "olist"
        return {"theme": theme}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read theme")


@router.post("/user/theme")
async def write_theme(payload: ThemePayload, _admin: bool = Depends(require_admin)):
    """Persist a theme choice (demo, requires admin token if configured)."""
    if payload.theme not in ALLOWED_THEMES:
        raise HTTPException(status_code=400, detail="Invalid theme id")
    try:
        async with async_session_factory() as session:
            # Portable upsert (MySQL + SQLite)
            if settings.db_type == "sqlite":
                upsert = text(
                    "INSERT INTO preferences (`key`, `value`) VALUES ('theme', :val) "
                    "ON CONFLICT (`key`) DO UPDATE SET `value` = :val"
                )
            else:
                upsert = text(
                    "INSERT INTO preferences (`key`, `value`) VALUES ('theme', :val) "
                    "ON DUPLICATE KEY UPDATE `value` = :val"
                )
            await session.execute(upsert, {"val": payload.theme})
            await session.commit()
        return {"theme": payload.theme, "saved": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to write theme")
