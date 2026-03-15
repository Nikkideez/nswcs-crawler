import type { Order, Stats, CrawlResult } from "./types";

export async function fetchOrders(orderType?: string): Promise<Order[]> {
  const params = orderType
    ? `?order_type=${encodeURIComponent(orderType)}`
    : "";
  const res = await fetch(`/api/orders${params}`);
  if (!res.ok) throw new Error("Failed to fetch orders");
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch("/api/stats");
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function triggerCrawl(): Promise<CrawlResult> {
  const res = await fetch("/api/crawl", { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger crawl");
  return res.json();
}
