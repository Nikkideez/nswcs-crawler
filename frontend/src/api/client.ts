import type { Order, Stats, CrawlResult } from "./types";

export async function fetchOrders(orderType?: string, sort?: string): Promise<Order[]> {
  const params = new URLSearchParams();
  if (orderType) params.set("order_type", orderType);
  if (sort) params.set("sort", sort);
  const qs = params.toString();
  const res = await fetch(`/api/orders${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error("Failed to fetch orders");
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch("/api/stats");
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export interface CrawlStatus {
  crawling: boolean;
  orders_found?: number;
  orders_total?: number;
}

export async function fetchCrawlStatus(): Promise<CrawlStatus> {
  const res = await fetch("/api/crawl/status");
  if (!res.ok) throw new Error("Failed to fetch crawl status");
  return res.json();
}

export async function triggerCrawl(): Promise<CrawlResult> {
  const res = await fetch("/api/crawl", { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger crawl");
  return res.json();
}
