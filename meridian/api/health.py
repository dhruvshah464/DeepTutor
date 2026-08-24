"""
Health Check Router
====================

Liveness, readiness, and metrics endpoints for production deployment.
"""

from __future__ import annotations

import os
import platform
import time

from fastapi import APIRouter

router = APIRouter()

_start_time = time.time()


@router.get("/health")
async def health():
    """Liveness probe — returns 200 if the process is alive."""
    return {"status": "ok", "uptime": time.time() - _start_time}


@router.get("/health/ready")
async def readiness():
    """Readiness probe — checks critical dependencies."""
    checks = {}

    # Database
    try:
        from meridian.persistence.engine import get_async_engine
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
    )


@router.get("/health/info")
async def info():
    """System info for debugging."""
    return {
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "python": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "pid": os.getpid(),
        "uptime_seconds": round(time.time() - _start_time, 1),
    }
