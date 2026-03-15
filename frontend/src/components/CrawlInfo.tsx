import type { Stats } from "@/api/types";

interface CrawlInfoProps {
  lastCrawl: Stats["last_crawl"];
}

export function CrawlInfo({ lastCrawl }: CrawlInfoProps) {
  if (!lastCrawl) return null;

  const time = lastCrawl.finished_at
    ? new Date(lastCrawl.finished_at).toISOString().replace("T", " ").slice(0, 19) + " UTC"
    : new Date(lastCrawl.started_at).toISOString().replace("T", " ").slice(0, 19) + " UTC";

  return (
    <p className="text-sm text-muted-foreground">
      Last crawl: {time} — {lastCrawl.orders_found} orders found,{" "}
      {lastCrawl.new_orders} new — Status:{" "}
      <span className="font-semibold">{lastCrawl.status}</span>
    </p>
  );
}
