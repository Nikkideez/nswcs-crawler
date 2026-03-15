"""
Web crawler for the NSW Building Commission Register of Building Work Orders.

Strategy:
  1. PRIMARY  – Use the site's internal ElasticSearch API to fetch structured
     order data (fastest, most reliable).
  2. FALLBACK – Render the JavaScript-heavy page with Playwright and parse
     the visible search results from the DOM.

For each order found the crawler visits the detail page to extract full
metadata (company name, ACN, address, PDF link, etc.).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.config import settings

logger = logging.getLogger(__name__)

# ── Data container ──────────────────────────────────────────────────────────

@dataclass
class OrderInfo:
    """Scraped metadata for a single building order."""

    title: str = ""
    order_type: str = ""
    company_name: str = ""
    acn: str = ""
    address: str = ""
    description: str = ""
    publication_date: str = ""
    source_url: str = ""
    pdf_url: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────

_ORDER_TYPE_KEYWORDS = {
    "stop work order": "Stop work order",
    "prohibition order": "Prohibition order",
    "building work rectification order": "Building work rectification order",
    "rectification order": "Rectification order",
}


def _classify_order(title: str) -> str:
    """Determine the order type from its title."""
    lower = title.lower()
    for keyword, label in _ORDER_TYPE_KEYWORDS.items():
        if keyword in lower:
            return label
    return "Unknown"


def _extract_acn(text: str) -> str:
    """Pull an ACN (Australian Company Number) out of free text."""
    m = re.search(r"ACN[\s:]*(\d[\d\s]{7,}\d)", text, re.IGNORECASE)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())
    return ""


def _extract_address(description: str, page_text: str) -> str:
    """Try to find a street address from the meta description or page body."""
    # The meta description often *is* the address
    if description and re.search(r"\d+.*(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|parade|pde|way|crescent|cres|boulevard|blvd|place|pl|court|ct|highway|hwy|terrace|tce)",
                                  description, re.IGNORECASE):
        return description.strip()
    # Fallback: find NSW addresses in the page text
    m = re.search(
        r"(\d+[\w\s,/-]+(?:NSW|New South Wales)\s*\d{4})", page_text, re.IGNORECASE
    )
    if m:
        return m.group(1).strip()
    return description.strip() if description else ""


# ── Detail page scraper ────────────────────────────────────────────────────

def scrape_order_detail(url: str) -> OrderInfo:
    """Fetch a single order detail page and extract metadata."""
    logger.debug("Scraping detail page: %s", url)
    info = OrderInfo(source_url=url)

    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return info

    soup = BeautifulSoup(resp.text, "lxml")

    # Title
    h1 = soup.find("h1")
    info.title = h1.get_text(strip=True) if h1 else ""
    info.order_type = _classify_order(info.title)

    # Company name from title  e.g. "Stop Work Order for Acme Pty Ltd"
    m = re.search(r"(?:for|–|-)\s+(.+)", info.title, re.IGNORECASE)
    info.company_name = m.group(1).strip() if m else info.title

    # Meta description (often the address)
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_content = meta_desc["content"] if meta_desc and meta_desc.get("content") else ""

    # Full page text for extraction
    page_text = soup.get_text(" ", strip=True)

    info.acn = _extract_acn(page_text)
    info.address = _extract_address(desc_content, page_text)

    # Publication / last-updated date
    import json

    for json_ld in soup.find_all("script", type="application/ld+json"):
        try:
            raw = json_ld.string or json_ld.get_text()
            if not raw:
                continue
            ld = json.loads(raw)
            # Handle both single object and array of objects
            items = ld if isinstance(ld, list) else [ld]
            for item in items:
                if isinstance(item, dict) and item.get("datePublished"):
                    info.publication_date = item["datePublished"]
                    break
            if info.publication_date:
                break
        except (json.JSONDecodeError, TypeError):
            continue

    if not info.publication_date:
        time_tag = soup.find("time")
        if time_tag:
            info.publication_date = time_tag.get("datetime", time_tag.get_text(strip=True))

    # Fallback: look for "Last updated" / "File last updated on" in page text
    if not info.publication_date:
        date_match = re.search(
            r"(?:last updated|updated|published)[\w\s]*?[:\s]+(\d{1,2}\s+\w+\s+\d{4})",
            page_text,
            re.IGNORECASE,
        )
        if date_match:
            info.publication_date = date_match.group(1)
        else:
            # Look for any standalone date like "17 February 2026"
            date_match = re.search(
                r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|"
                r"August|September|October|November|December)\s+\d{4})",
                page_text,
                re.IGNORECASE,
            )
            if date_match:
                info.publication_date = date_match.group(1)

    # Fallback: meta article:published_time or article:modified_time
    if not info.publication_date:
        for meta_name in ("article:published_time", "article:modified_time", "dcterms.date"):
            meta = soup.find("meta", attrs={"property": meta_name}) or soup.find(
                "meta", attrs={"name": meta_name}
            )
            if meta and meta.get("content"):
                info.publication_date = meta["content"][:10]  # YYYY-MM-DD
                break

    # Description / summary
    article = soup.find("article") or soup.find("div", class_=re.compile(r"field--body|content"))
    if article:
        paragraphs = article.find_all("p")
        info.description = " ".join(p.get_text(strip=True) for p in paragraphs[:3])

    # PDF download link
    pdf_link = soup.find("a", href=re.compile(r"\.pdf", re.IGNORECASE))
    if pdf_link:
        info.pdf_url = urljoin(url, pdf_link["href"])

    return info


# ── Strategy 1: Elasticsearch API ──────────────────────────────────────────

_ES_SEARCH_URL = (
    "https://www.nsw.gov.au/api/v1/elasticsearch/prod_content/_search"
)
_ES_PAGE_SIZE = 100


def _try_api_listing() -> list[str]:
    """
    Discover order URLs via the nsw.gov.au Elasticsearch API.

    The site's register page loads results client-side from an Elasticsearch
    index.  We query the same endpoint directly, paginating with ``from`` /
    ``size`` until every order URL has been collected.
    """
    logger.info("Trying Elasticsearch API listing...")
    urls: list[str] = []
    offset = 0

    try:
        while True:
            params = {
                "q": (
                    'agency_name:"Building Commission NSW"'
                    " AND url:*register-of-building-work-orders*"
                ),
                "size": _ES_PAGE_SIZE,
                "from": offset,
                "sort": "resource_date:desc",
                "_source": "url",
            }
            resp = httpx.get(
                _ES_SEARCH_URL,
                params=params,
                follow_redirects=True,
                timeout=30,
            )
            if resp.status_code != 200:
                logger.debug("Elasticsearch returned %d", resp.status_code)
                break

            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                break

            for hit in hits:
                path_list = hit.get("_source", {}).get("url", [])
                path = path_list[0] if path_list else ""
                if path:
                    full_url = f"https://www.nsw.gov.au{path}"
                    if full_url not in urls:
                        urls.append(full_url)

            total = data["hits"]["total"]["value"]
            offset += len(hits)
            logger.info(
                "Elasticsearch page: got %d URLs so far (total %d)",
                len(urls),
                total,
            )

            if offset >= total:
                break

    except Exception as exc:
        logger.debug("Elasticsearch listing failed: %s", exc)

    if urls:
        logger.info("Elasticsearch API returned %d order URLs", len(urls))
    return urls


# ── Strategy 2: Playwright rendering ──────────────────────────────────────

def _playwright_listing() -> list[str]:
    """
    Render the register page in a headless browser, wait for the search
    results to appear, and click through every pagination page to collect
    all order links.
    """
    logger.info("Using Playwright to render the register page...")
    urls: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        })

        try:
            page.goto(settings.base_url, wait_until="networkidle", timeout=60_000)

            # Wait for the result list to appear
            page.wait_for_selector(
                "a[href*='register-of-building-work-orders/']",
                timeout=30_000,
            )

            def _collect_links() -> None:
                """Gather order links visible on the current page."""
                for link in page.query_selector_all(
                    "a[href*='register-of-building-work-orders/']"
                ):
                    href = link.get_attribute("href")
                    if (
                        href
                        and href != settings.base_url
                        and "/about-orders" not in href
                    ):
                        full_url = urljoin("https://www.nsw.gov.au", href)
                        if full_url not in urls:
                            urls.append(full_url)

            # Collect from first page
            _collect_links()

            # Click through all pagination pages
            for _ in range(50):
                next_btn = page.query_selector(
                    "a[aria-label='Next page'], "
                    "a:has-text('Next'), "
                    "button:has-text('Next'), "
                    "button:has-text('Load more'), "
                    "button:has-text('Show more')"
                )
                if not next_btn or not next_btn.is_visible():
                    break
                next_btn.click()
                page.wait_for_timeout(2000)
                # Wait for new results to render
                page.wait_for_selector(
                    "a[href*='register-of-building-work-orders/']",
                    timeout=10_000,
                )
                prev_count = len(urls)
                _collect_links()
                logger.info(
                    "Playwright pagination: %d URLs collected", len(urls)
                )
                if len(urls) == prev_count:
                    break  # no new links found

        except Exception as exc:
            logger.error("Playwright scraping failed: %s", exc)
        finally:
            browser.close()

    logger.info("Playwright found %d order URLs", len(urls))
    return urls


# ── Strategy 3: Static HTML fallback ──────────────────────────────────────

def _static_listing() -> list[str]:
    """
    Simple requests+BS4 scrape.  Works if the page server-renders links.
    """
    logger.info("Trying static HTML listing...")
    urls: list[str] = []

    try:
        resp = httpx.get(settings.base_url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=re.compile(r"register-of-building-work-orders/.+")):
            href = a["href"]
            if "/about-orders" in href:
                continue
            full_url = urljoin("https://www.nsw.gov.au", href)
            if full_url not in urls:
                urls.append(full_url)
    except Exception as exc:
        logger.debug("Static listing failed: %s", exc)

    logger.info("Static HTML found %d order URLs", len(urls))
    return urls


# ── Public interface ───────────────────────────────────────────────────────

def discover_order_urls() -> list[str]:
    """
    Get all order detail page URLs from the register, trying multiple
    strategies in order of preference.
    """
    # Strategy 1: API
    urls = _try_api_listing()
    if urls:
        return urls

    # Strategy 2: Playwright (JS rendering)
    urls = _playwright_listing()
    if urls:
        return urls

    # Strategy 3: Static HTML
    urls = _static_listing()
    return urls


def crawl_all_orders() -> list[OrderInfo]:
    """
    Full crawl: discover order URLs then scrape each detail page.
    Returns a list of OrderInfo for all found orders.
    """
    urls = discover_order_urls()
    logger.info("Scraping %d order detail pages...", len(urls))

    orders: list[OrderInfo] = []
    for url in urls:
        info = scrape_order_detail(url)
        if info.title:
            orders.append(info)
            logger.info(
                "  [%s] %s", info.order_type, info.company_name or info.title
            )

    return orders


def crawl_stop_work_orders() -> list[OrderInfo]:
    """Convenience: crawl and return only Stop Work Orders."""
    return [o for o in crawl_all_orders() if "stop work" in o.order_type.lower()]
