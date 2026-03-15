"""
NSW Building Orders Monitor — CLI entry point.

Usage (inside Docker):
    python -m src.main crawl          # one-off crawl
    python -m src.main monitor        # continuous monitoring (crawl + schedule)
    python -m src.main dashboard      # start web dashboard only
    python -m src.main run            # crawl + monitor + dashboard (default)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

import typer
from apscheduler.schedulers.background import BackgroundScheduler
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from src.config import settings
from src.crawler import crawl_all_orders
from src.database import BuildingOrder, CrawlLog, get_session, init_db
from src.notifier import send_notification

app = typer.Typer(
    name="building-orders",
    help="NSW Building Commission — Stop Work Orders Monitor",
    add_completion=False,
)
console = Console()


# ── Logging ─────────────────────────────────────────────────────────────────

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


# ── Core crawl-and-store logic ──────────────────────────────────────────────

def _cleanup_stale_crawls() -> None:
    """Mark any 'running' crawl logs as 'interrupted' (from prior crashes)."""
    session = get_session()
    stale = session.query(CrawlLog).filter(CrawlLog.status == "running").all()
    for log in stale:
        log.status = "interrupted"
        log.finished_at = datetime.now(timezone.utc)
    if stale:
        session.commit()
        logger = logging.getLogger(__name__)
        logger.info("Marked %d stale crawl(s) as interrupted", len(stale))
    session.close()


def run_crawl() -> list[BuildingOrder]:
    """Execute a full crawl, store results, and return newly found orders."""
    session = get_session()
    log = CrawlLog()
    session.add(log)
    session.commit()

    new_orders: list[BuildingOrder] = []

    def _on_progress(processed: int, total: int) -> None:
        log.orders_found = processed
        log.orders_total = total
        session.commit()

    try:
        scraped = crawl_all_orders(on_progress=_on_progress)
        log.orders_found = len(scraped)

        for info in scraped:
            existing = (
                session.query(BuildingOrder)
                .filter_by(source_url=info.source_url)
                .first()
            )
            if existing:
                # Update last-seen timestamp
                existing.last_seen = datetime.now(timezone.utc)
                session.add(existing)
            else:
                order = BuildingOrder(
                    title=info.title,
                    order_type=info.order_type,
                    company_name=info.company_name,
                    acn=info.acn,
                    address=info.address,
                    description=info.description,
                    publication_date=info.publication_date,
                    source_url=info.source_url,
                    pdf_url=info.pdf_url,
                )
                session.add(order)
                new_orders.append(order)

        log.new_orders = len(new_orders)
        log.status = "success"
        log.finished_at = datetime.now(timezone.utc)

        session.commit()

        # Refresh so relationships / defaults are populated
        for o in new_orders:
            session.refresh(o)

    except Exception as exc:
        log.status = "error"
        log.error_message = str(exc)
        log.finished_at = datetime.now(timezone.utc)
        session.commit()
        raise
    finally:
        session.close()

    return new_orders


def _display_results(new_orders: list[BuildingOrder]) -> None:
    """Pretty-print crawl results to the terminal."""
    session = get_session()
    total = session.query(BuildingOrder).count()
    stop_work = (
        session.query(BuildingOrder)
        .filter(BuildingOrder.order_type.ilike("%stop work%"))
        .count()
    )
    session.close()

    console.print()
    console.print(
        Panel(
            f"[bold green]Crawl complete[/]\n"
            f"Total orders in DB: [cyan]{total}[/]\n"
            f"Stop work orders:   [red]{stop_work}[/]\n"
            f"New this run:       [yellow]{len(new_orders)}[/]",
            title="Building Orders Monitor",
            border_style="blue",
        )
    )

    if new_orders:
        table = Table(title="Newly Discovered Orders", show_lines=True)
        table.add_column("Type", style="red")
        table.add_column("Company", style="cyan")
        table.add_column("ACN")
        table.add_column("Address", max_width=40)
        table.add_column("Date")

        for o in new_orders:
            table.add_row(
                o.order_type,
                o.company_name or "—",
                o.acn or "—",
                o.address or "—",
                o.publication_date or "—",
            )
        console.print(table)

    # Show stop-work-order summary
    session = get_session()
    swo = (
        session.query(BuildingOrder)
        .filter(BuildingOrder.order_type.ilike("%stop work%"))
        .all()
    )
    session.close()

    if swo:
        table = Table(title="All Stop Work Orders", show_lines=True)
        table.add_column("#", style="dim")
        table.add_column("Company", style="cyan bold")
        table.add_column("ACN")
        table.add_column("Address", max_width=40)
        table.add_column("First Seen")
        table.add_column("URL", style="dim")

        for i, o in enumerate(swo, 1):
            table.add_row(
                str(i),
                o.company_name or "—",
                o.acn or "—",
                o.address or "—",
                o.first_seen.strftime("%Y-%m-%d %H:%M") if o.first_seen else "—",
                o.source_url[:60] + "..." if len(o.source_url) > 60 else o.source_url,
            )
        console.print(table)


# ── CLI commands ────────────────────────────────────────────────────────────

@app.command()
def crawl(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Run a single crawl, store results, and notify on new stop work orders."""
    _setup_logging(verbose)
    init_db()

    console.print("[bold blue]Starting crawl...[/]")
    new_orders = run_crawl()
    _display_results(new_orders)

    # Notify on new stop work orders
    new_swo = [o for o in new_orders if "stop work" in o.order_type.lower()]
    if new_swo:
        send_notification(new_swo)


@app.command()
def monitor(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Run crawls on a schedule (interval from CRAWL_INTERVAL_MINUTES)."""
    _setup_logging(verbose)
    init_db()

    console.print(
        f"[bold blue]Starting scheduled monitor "
        f"(every {settings.crawl_interval_minutes} min)...[/]"
    )

    def _scheduled_crawl() -> None:
        console.print(f"\n[dim]Scheduled crawl at {datetime.now(timezone.utc).isoformat()}[/]")
        new_orders = run_crawl()
        _display_results(new_orders)
        new_swo = [o for o in new_orders if "stop work" in o.order_type.lower()]
        if new_swo:
            send_notification(new_swo)

    # Run once immediately
    _scheduled_crawl()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _scheduled_crawl,
        "interval",
        minutes=settings.crawl_interval_minutes,
    )
    scheduler.start()

    console.print("[green]Scheduler running. Press Ctrl+C to stop.[/]")
    try:
        scheduler.print_jobs()
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        console.print("\n[yellow]Scheduler stopped.[/]")


@app.command()
def dashboard(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Start the web dashboard."""
    _setup_logging(verbose)
    init_db()

    import uvicorn
    from src.dashboard import create_app

    web_app = create_app()
    console.print(f"[bold blue]Dashboard at http://0.0.0.0:{settings.dashboard_port}[/]")
    uvicorn.run(web_app, host="0.0.0.0", port=settings.dashboard_port)


@app.command()
def run(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Run initial crawl, then start scheduler + dashboard together."""
    _setup_logging(verbose)
    init_db()

    console.print("[bold blue]Building Orders Monitor — starting up...[/]")
    _cleanup_stale_crawls()

    def _do_crawl() -> None:
        new_orders = run_crawl()
        _display_results(new_orders)
        new_swo = [o for o in new_orders if "stop work" in o.order_type.lower()]
        if new_swo:
            send_notification(new_swo)

    # Schedule crawls (initial + recurring)
    scheduler = BackgroundScheduler()
    # Run initial crawl in background so the dashboard is available immediately
    scheduler.add_job(_do_crawl, "date")
    scheduler.add_job(
        _do_crawl,
        "interval",
        minutes=settings.crawl_interval_minutes,
    )
    scheduler.start()

    # Start dashboard (blocks)
    import uvicorn
    from src.dashboard import create_app

    web_app = create_app()
    console.print(
        f"[bold green]Dashboard:[/] http://0.0.0.0:{settings.dashboard_port}\n"
        f"[bold green]Next crawl:[/] in {settings.crawl_interval_minutes} minutes\n"
    )

    try:
        uvicorn.run(web_app, host="0.0.0.0", port=settings.dashboard_port)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Default: run the full stack (crawl + monitor + dashboard)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


if __name__ == "__main__":
    app()
