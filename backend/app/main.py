"""
Analytica — FastAPI Application Entry Point
Enterprise Analytics Platform powered by the Brazilian Olist e-commerce Data Warehouse.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from fastapi import Depends
from app.core.config import settings
from app.core.database import engine
from app.core.schema import ensure_schema
from app.middleware.cors import setup_cors
from app.middleware.auth import verify_token
from app.middleware.ratelimit import RateLimitMiddleware
from app.middleware.logging import RequestLogMiddleware
from app.middleware.security import SecurityHeadersMiddleware

# Domain routers
from app.domains.executive.router import router as executive_router
from app.domains.sales.router import router as sales_router
from app.domains.customers.router import router as customers_router
from app.domains.products.router import router as products_router
from app.domains.geography.router import router as geography_router
from app.domains.reports.router import router as reports_router
from app.domains.insights.router import router as insights_router
from app.domains.segmentation.router import router as segmentation_router
from app.domains.forecasting.router import router as forecasting_router
from app.domains.exec_summary.router import router as exec_summary_router
from app.domains.settings.router import router as settings_router


import json
import logging
import time
from fastapi import Request

# Structured JSON Logger
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

logger = logging.getLogger("analytica")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: verify DB connection on startup, dispose on shutdown."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await ensure_schema(conn)
        logger.info(f"Analytica connected to database successfully: {settings.db_name}@{settings.db_host}")

        if settings.db_user == "root":
            logger.warning("SECURITY: Using 'root' database user. Create a restricted application user in production.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    yield
    await engine.dispose()
    logger.info("Database connection pool disposed.")



# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "Analytica — A modern enterprise analytics platform "
        "demonstrated using the Brazilian Olist e-commerce dataset."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
setup_cors(app)

# Rate limiting (100 req/min per IP)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# Production security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request logging
app.add_middleware(RequestLogMiddleware)

# ---------------------------------------------------------------------------
# Mount Domain Routers
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"
AUTH = [Depends(verify_token)]

app.include_router(executive_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(sales_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(customers_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(products_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(geography_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(reports_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(insights_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(segmentation_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(forecasting_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(exec_summary_router, prefix=API_PREFIX, dependencies=AUTH)
app.include_router(settings_router, prefix=API_PREFIX, dependencies=AUTH)


# ---------------------------------------------------------------------------
# Root & Health
# ---------------------------------------------------------------------------

@app.get("/", tags=["System"])
async def root():
    """API root — platform info."""
    return {
        "name": "Analytica",
        "version": settings.api_version,
        "description": "Enterprise Analytics Platform",
        "docs": "/docs",
    }


@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    db_status = "healthy"
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return {"status": "ok", "database": db_status, "version": settings.api_version}


# ---------------------------------------------------------------------------
# Filters Endpoint (used by frontend dropdowns)
# ---------------------------------------------------------------------------

@app.get("/api/v1/filters", tags=["Filters"])
async def get_filter_options():
    """Return all available filter values for frontend dropdowns."""
    from app.core.database import async_session_factory

    categories = []
    states = []
    months = []
    sellers = []

    try:
        async with async_session_factory() as session:
            cat_result = await session.execute(
                text("SELECT DISTINCT product_category_name_english FROM dim_product WHERE product_category_name_english IS NOT NULL ORDER BY product_category_name_english")
            )
            categories = [row[0] for row in cat_result.fetchall()]

            state_result = await session.execute(
                text("SELECT DISTINCT state_code FROM dim_geography WHERE state_code IS NOT NULL ORDER BY state_code")
            )
            states = [row[0] for row in state_result.fetchall()]

            month_result = await session.execute(
                text("SELECT DISTINCT month_year FROM dim_date WHERE month_year IS NOT NULL ORDER BY month_year")
            )
            months = [row[0] for row in month_result.fetchall()]

            seller_result = await session.execute(
                text("SELECT seller_id FROM reporting_seller_summary ORDER BY total_revenue_generated DESC LIMIT 100")
            )
            sellers = [row[0] for row in seller_result.fetchall()]
    except Exception as e:
        print(f"[WARN] Filters endpoint DB error: {e}")

    return {"categories": categories, "states": states, "months": months, "sellers": sellers}


@app.get("/api/v1/search", tags=["Search"])
async def global_search(q: str = ""):
    """Global search across metrics, categories, states, and modules."""
    if not q or len(q.strip()) < 2:
        return {"results": []}

    query = q.strip().lower()
    results = []

    # System modules
    modules = [
        {"title": "Executive Summary", "category": "Navigation", "href": "/"},
        {"title": "Sales Analytics", "category": "Navigation", "href": "/sales"},
        {"title": "Customer Insights", "category": "Navigation", "href": "/customers"},
        {"title": "Product & Seller Analytics", "category": "Navigation", "href": "/products"},
        {"title": "Geographic Performance", "category": "Navigation", "href": "/geography"},
        {"title": "Business Insights", "category": "Navigation", "href": "/insights"},
        {"title": "Customer Segmentation", "category": "Navigation", "href": "/segmentation"},
        {"title": "Revenue Forecasting", "category": "Navigation", "href": "/forecasting"},
        {"title": "Executive Summary", "category": "Navigation", "href": "/executive-summary"},
        {"title": "Data Reports Explorer", "category": "Navigation", "href": "/reports"},
        {"title": "Platform Settings", "category": "Navigation", "href": "/settings"},
    ]

    for m in modules:
        if query in m["title"].lower() or query in m["category"].lower():
            results.append(m)

    from app.core.database import async_session_factory
    try:
        async with async_session_factory() as session:
            # Match categories
            cat_res = await session.execute(
                text("SELECT DISTINCT product_category FROM reporting_category_summary WHERE LOWER(product_category) LIKE :q LIMIT 5"),
                {"q": f"%{query}%"}
            )
            for row in cat_res.fetchall():
                results.append({"title": f"Category: {row[0]}", "category": "Product Category", "href": "/products"})

            # Match states
            state_res = await session.execute(
                text("SELECT DISTINCT state_code FROM reporting_state_summary WHERE LOWER(state_code) LIKE :q LIMIT 3"),
                {"q": f"%{query}%"}
            )
            for row in state_res.fetchall():
                results.append({"title": f"State: {row[0]}", "category": "Geography", "href": "/geography"})
    except Exception as e:
        print(f"[WARN] Search endpoint DB error: {e}")

    return {"results": results}


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "data": None, "message": "Invalid request parameter format."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fail-secure unhandled exception handler to prevent internal trace exposure."""
    logger.error(f"[SECURITY UNHANDLED EXCEPTION] Path: {request.url.path} | Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "message": "An internal server error occurred. Please try again later."},
    )

