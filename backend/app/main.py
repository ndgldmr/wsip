"""
FastAPI application factory.

Registers all routers, CORS middleware, request-ID middleware, and the /health
meta endpoint.  Structured JSON logging is configured at import time.
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import configure_logging
from app.routers import admin, employees, insights, orgs, recommendations, simulations, teams

configure_logging()
logger = logging.getLogger("wsip.request")

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="WSIP — Work Signal Intelligence Platform",
    version="0.9.0",
    description=(
        "Analytics API for work signal insights: underutilization, overload, "
        "disengagement risk, skill utilization, and glue-person detection."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Request-ID middleware
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a short UUID to every request; log method + path + status + duration."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = round((time.perf_counter() - t0) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s → %s (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            ms,
            extra={"request_id": request_id},
        )
        return response


app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(admin.router,           prefix="/admin",           tags=["admin"])
app.include_router(orgs.router,            prefix="/orgs",            tags=["orgs"])
app.include_router(teams.router,           prefix="/teams",           tags=["teams"])
app.include_router(employees.router,       prefix="/employees",       tags=["employees"])
app.include_router(insights.router,        prefix="/insights",        tags=["insights"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(simulations.router,     prefix="/simulations",     tags=["simulations"])


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
