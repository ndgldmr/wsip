from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, employees, insights, orgs, recommendations, simulations, teams

app = FastAPI(
    title="WSIP — Work Signal Intelligence Platform",
    version="0.1.0",
    description="Analytics API for work signal insights: underutilization, overload, disengagement risk, skill utilization, and glue-person detection.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default dev port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(orgs.router, prefix="/orgs", tags=["orgs"])
app.include_router(teams.router, prefix="/teams", tags=["teams"])
app.include_router(employees.router, prefix="/employees", tags=["employees"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(simulations.router, prefix="/simulations", tags=["simulations"])


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
