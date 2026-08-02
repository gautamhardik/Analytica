from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str | None:
    if not settings.admin_token:
        return None
    if not credentials or credentials.credentials != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authorization token",
        )
    return credentials.credentials
