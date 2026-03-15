"""FastAPI web dashboard for the Building Orders Monitor."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.database import BuildingOrder, CrawlLog, get_session

DIST_DIR = Path(__file__).resolve().parent.parent / "dist"


def create_app() -> FastAPI:
    web = FastAPI(title="Building Orders Monitor")

    @web.get("/api/stats")
    async def api_stats():
        session = get_session()
        orders = session.query(BuildingOrder).all()
        stop_work = sum(
            1 for o in orders if "stop work" in o.order_type.lower()
        )
        rectification = sum(
            1 for o in orders if "rectification" in o.order_type.lower()
        )
        prohibition = sum(
            1 for o in orders if "prohibition" in o.order_type.lower()
        )
        last_crawl = (
            session.query(CrawlLog)
            .order_by(CrawlLog.started_at.desc())
            .first()
        )
        session.close()

        return {
            "total": len(orders),
            "stop_work": stop_work,
            "rectification": rectification,
            "prohibition": prohibition,
            "last_crawl": {
                "started_at": last_crawl.started_at.isoformat(),
                "finished_at": (
                    last_crawl.finished_at.isoformat()
                    if last_crawl.finished_at
                    else None
                ),
                "orders_found": last_crawl.orders_found,
                "new_orders": last_crawl.new_orders,
                "status": last_crawl.status,
            }
            if last_crawl
            else None,
        }

    @web.get("/api/crawl/status")
    async def crawl_status():
        session = get_session()
        running = (
            session.query(CrawlLog)
            .filter(CrawlLog.status == "running")
            .first()
        )
        session.close()
        if running:
            return {
                "crawling": True,
                "orders_found": running.orders_found,
                "orders_total": running.orders_total,
                "started_at": running.started_at.isoformat(),
            }
        return {"crawling": False}

    @web.get("/api/orders")
    async def api_orders(order_type: str | None = None, sort: str | None = None):
        session = get_session()
        q = session.query(BuildingOrder)
        if order_type:
            q = q.filter(BuildingOrder.order_type.ilike(f"%{order_type}%"))
        if sort == "date_asc":
            q = q.order_by(BuildingOrder.publication_date.asc())
        elif sort == "date_desc":
            q = q.order_by(BuildingOrder.publication_date.desc())
        else:
            q = q.order_by(BuildingOrder.first_seen.desc())
        orders = q.all()
        session.close()
        return [
            {
                "id": o.id,
                "title": o.title,
                "order_type": o.order_type,
                "company_name": o.company_name,
                "acn": o.acn,
                "address": o.address,
                "publication_date": o.publication_date,
                "source_url": o.source_url,
                "pdf_url": o.pdf_url,
                "first_seen": o.first_seen.isoformat() if o.first_seen else None,
            }
            for o in orders
        ]

    @web.post("/api/crawl")
    async def trigger_crawl():
        import asyncio
        from src.main import run_crawl
        new = await asyncio.to_thread(run_crawl)
        return {
            "status": "ok",
            "new_orders": len(new),
            "new": [
                {"title": o.title, "company_name": o.company_name}
                for o in new
            ],
        }

    # Serve built frontend (production)
    if DIST_DIR.is_dir():
        assets_dir = DIST_DIR / "assets"
        if assets_dir.is_dir():
            web.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="assets",
            )

        @web.get("/{path:path}")
        async def spa_catch_all(path: str):
            file_path = DIST_DIR / path
            if path and file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(DIST_DIR / "index.html"))

    return web
