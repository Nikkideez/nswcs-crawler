import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { CrawlResult } from "@/api/types";
import type { CrawlStatus } from "@/api/client";

interface HeaderProps {
  onCrawl: () => void;
  crawling: boolean;
  lastResult: CrawlResult | null;
  crawlProgress: CrawlStatus | null;
}

export function Header({ onCrawl, crawling, lastResult, crawlProgress }: HeaderProps) {
  const progressText = crawlProgress?.orders_total
    ? `Crawling... ${crawlProgress.orders_found} / ${crawlProgress.orders_total}`
    : "Crawling...";

  return (
    <header className="bg-primary text-primary-foreground py-4 px-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Building Orders Monitor</h1>
          <p className="text-sm opacity-80">
            NSW Building Commission — Register of Building Work Orders
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastResult && !crawling && (
            <span className="text-sm opacity-80">
              Done — {lastResult.new_orders} new order(s)
            </span>
          )}
          {crawling && (
            <span className="text-sm opacity-80 flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              {progressText}
            </span>
          )}
          <Button
            variant="secondary"
            onClick={onCrawl}
            disabled={crawling}
            className="shrink-0"
          >
            Crawl Now
          </Button>
        </div>
      </div>
    </header>
  );
}
