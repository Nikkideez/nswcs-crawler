# NSW Building Orders Monitor

A web scraper and notification system that monitors building work orders on the
[NSW Building Commission Register of Building Work Orders](https://www.nsw.gov.au/departments-and-agencies/building-commission/register-of-building-work-orders).

## Features

- **Multi-strategy web crawler** — queries the site's Elasticsearch API with
  full pagination, falls back to headless-browser rendering (Playwright), then
  to static HTML parsing.
- **PostgreSQL storage** — all orders are persisted with deduplication and
  first-seen / last-seen tracking.
- **Email notifications** — sends an HTML email whenever new stop work orders
  are detected.
- **Scheduled monitoring** — configurable interval for continuous crawling
  (default: every 60 minutes).
- **React SPA dashboard** — a React + Tailwind CSS + shadcn/ui frontend served
  by FastAPI, with stats cards, type filters, and a manual "Crawl Now" button.
- **Rich CLI** — pretty terminal output with tables and colour.
- **Dockerised** — multi-stage build (Node + Python); one command to spin up.

## Architecture

```
┌────────────────────────────────────┐
│        NSW Gov Website             │
│  (Elasticsearch API / JS-rendered) │
└──────────────┬─────────────────────┘
               │  HTTP / Playwright
┌──────────────▼─────────────────────┐
│          Crawler (Python)          │
│  Strategy 1: Elasticsearch API     │
│  Strategy 2: Playwright + BS4      │
│  Strategy 3: Static HTML + BS4     │
└──────┬───────────────┬─────────────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────┐
│ PostgreSQL  │  │ Email (SMTP)   │
│ Database    │  │ Notifications  │
└──────┬──────┘  └────────────────┘
       │
┌──────▼──────────────────────────┐
│  FastAPI API :8080               │
│  React SPA (Vite) :5173          │
└─────────────────────────────────┘
```

The frontend is built at Docker image time in a Node stage and served as static
files from FastAPI — no extra Node container is needed at runtime.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### 1. Clone and configure

```bash
cd nswcs-project
cp .env.example .env
```

Edit `.env` with your settings. At minimum:

```env
DATABASE_URL=postgresql://crawler:crawler@db:5432/building_orders
```

For email notifications, fill in the SMTP settings (e.g. Gmail app password):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=you@gmail.com
EMAIL_TO=recipient@example.com
```

### 2. Build and run

```bash
# Build the Docker image (includes frontend compilation)
docker compose build

# Run a single crawl (good for testing)
docker compose run --rm app crawl

# Start the full stack (crawl + scheduler + dashboard)
docker compose up
```

The API will be available at **http://localhost:8080**. For frontend
development, see section 4 below — the Vite dev server runs at
**http://localhost:5173**.

### 3. CLI commands

| Command | Description |
|---------|-------------|
| `crawl` | One-off crawl, store results, send notifications |
| `monitor` | Continuous crawling on a schedule |
| `dashboard` | Start only the web dashboard |
| `run` | Full stack: initial crawl + scheduler + dashboard (default) |

Add `--verbose` / `-v` for debug logging.

Examples inside Docker:

```bash
# Single crawl
docker compose run --rm app crawl -v

# Just the dashboard (assumes data already exists)
docker compose run --rm -p 8080:8080 app dashboard
```

### 4. Frontend development

The React frontend uses Vite with a proxy to the FastAPI backend:

```bash
# Start the FastAPI backend
docker compose up db        # or run PostgreSQL locally
python -m src.main dashboard

# In another terminal, start the Vite dev server
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxies /api → :8080)
```

### 5. Running without Docker

```bash
# Start a PostgreSQL instance
docker run -d --name pg -e POSTGRES_USER=crawler -e POSTGRES_PASSWORD=crawler \
  -e POSTGRES_DB=building_orders -p 5432:5432 postgres:16-alpine

# Install Python dependencies
pip install -r requirements.txt
playwright install chromium

# Set DATABASE_URL for local access
export DATABASE_URL=postgresql://crawler:crawler@localhost:5432/building_orders

# Run
python -m src.main crawl
```

## Project Structure

```
├── docker-compose.yml        # Docker services (app + postgres)
├── Dockerfile                # Multi-stage build (Node → Python)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── src/
│   ├── config.py             # Settings (from env vars)
│   ├── database.py           # SQLAlchemy models + session
│   ├── crawler.py            # Multi-strategy web scraper
│   ├── notifier.py           # Email notification system
│   ├── dashboard.py          # FastAPI: API endpoints + static serving
│   └── main.py               # CLI entry point (Typer)
├── frontend/
│   ├── package.json          # Node dependencies
│   ├── vite.config.ts        # Vite config (Tailwind, alias, proxy)
│   ├── index.html            # Vite entry HTML
│   ├── components.json       # shadcn/ui config
│   └── src/
│       ├── main.tsx          # React DOM entry
│       ├── App.tsx           # Root component
│       ├── index.css         # Tailwind + NSW theme CSS vars
│       ├── api/              # TS types + fetch helpers
│       ├── components/       # Header, StatsCards, FilterBar, OrdersTable, etc.
│       └── components/ui/    # shadcn primitives (button, card, badge, table…)
└── tests/
    └── test_crawler.py       # Unit tests
```

## How It Works

1. **Discovery** — The crawler queries the NSW Gov Elasticsearch API
   (`/api/v1/elasticsearch/prod_content/_search`) with `from`/`size` pagination
   to collect all order URLs. Falls back to Playwright or static HTML if needed.
2. **Detail extraction** — Each order page is fetched and parsed for company
   name, ACN, address, publication date, and PDF link.
3. **Storage** — Orders are upserted into PostgreSQL; duplicates are detected
   by source URL. First-seen and last-seen timestamps are tracked.
4. **Notification** — If any *new* stop work orders are found, an HTML email
   is sent to the configured recipient.
5. **Dashboard** — A React SPA shows all orders with stats cards, type filters,
   and a "Crawl Now" button. FastAPI serves the API and the built frontend.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/stats` | Order counts + last crawl info |
| `GET` | `/api/orders?order_type=…&sort=…` | List orders (optional type filter + sort) |
| `GET` | `/api/crawl/status` | Check if a crawl is in progress (with progress) |
| `POST` | `/api/crawl` | Trigger a crawl, returns new orders found |
| `GET` | `/*` | SPA catch-all (serves React app) |

## Testing

```bash
# Inside Docker
docker compose run --rm app python -m pytest tests/ -v

# Locally
pytest tests/ -v
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://crawler:crawler@db:5432/building_orders` | PostgreSQL connection string |
| `BASE_URL` | *(NSW Gov register URL)* | Target page to scrape |
| `CRAWL_INTERVAL_MINUTES` | `60` | Minutes between scheduled crawls |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | | SMTP login |
| `SMTP_PASSWORD` | | SMTP password |
| `EMAIL_FROM` | | Sender address |
| `EMAIL_TO` | | Recipient address |
| `DASHBOARD_PORT` | `8080` | Web dashboard port |
