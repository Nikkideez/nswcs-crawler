import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import { Header } from "@/components/Header";
import { StatsCards } from "@/components/StatsCards";
import { FilterBar } from "@/components/FilterBar";
import { OrdersTable } from "@/components/OrdersTable";
import { CrawlInfo } from "@/components/CrawlInfo";
import { Loader2 } from "lucide-react";
import { fetchOrders, fetchStats, fetchCrawlStatus, triggerCrawl } from "@/api/client";
import type { CrawlStatus } from "@/api/client";
import type { Order, Stats, CrawlResult } from "@/api/types";

export default function App() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [crawling, setCrawling] = useState(false);
  const [lastResult, setLastResult] = useState<CrawlResult | null>(null);
  const [sort, setSort] = useState("");
  const [crawlProgress, setCrawlProgress] = useState<CrawlStatus | null>(null);

  const loadData = useCallback(async (orderType?: string, sortBy?: string) => {
    setLoading(true);
    try {
      const [ordersData, statsData] = await Promise.all([
        fetchOrders(orderType || undefined, sortBy || undefined),
        fetchStats(),
      ]);
      setOrders(ordersData);
      setStats(statsData);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll backend crawl status every 3 seconds
  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const status = await fetchCrawlStatus();
        if (!active) return;
        setCrawling(status.crawling);
        setCrawlProgress(status.crawling ? status : null);
        if (!status.crawling && crawling) {
          // Crawl just finished — reload data
          await loadData(filter, sort);
        }
      } catch {
        // Backend not ready yet, ignore
      }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => { active = false; clearInterval(id); };
  }, [crawling, filter, loadData]);

  useEffect(() => {
    loadData(filter, sort);
  }, [filter, sort, loadData]);

  const handleCrawl = async () => {
    setCrawling(true);
    setLastResult(null);
    try {
      const result = await triggerCrawl();
      setLastResult(result);
      toast.success(
        `Crawl complete — ${result.new_orders} new order${result.new_orders !== 1 ? "s" : ""} found`,
      );
      await loadData(filter, sort);
    } catch {
      toast.error("Crawl failed");
    } finally {
      setCrawling(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header onCrawl={handleCrawl} crawling={crawling} lastResult={lastResult} crawlProgress={crawlProgress} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {crawling && !stats?.total && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-muted-foreground text-sm">
              Crawling NSW Building Commission register...
            </p>
            {crawlProgress && !!crawlProgress.orders_total && (
              <div className="w-64 space-y-1">
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-500"
                    style={{ width: `${Math.round((crawlProgress.orders_found! / crawlProgress.orders_total) * 100)}%` }}
                  />
                </div>
                <p className="text-muted-foreground text-xs text-center">
                  {crawlProgress.orders_found} / {crawlProgress.orders_total} orders
                </p>
              </div>
            )}
          </div>
        )}
        {(!crawling || !!stats?.total) && (
          <>
            <StatsCards stats={stats} loading={loading} />
            <CrawlInfo lastCrawl={stats?.last_crawl ?? null} />
            <FilterBar value={filter} onChange={setFilter} />
            <OrdersTable orders={orders} loading={loading} sort={sort} onSortChange={setSort} />
          </>
        )}
      </main>
      <Toaster richColors position="bottom-right" />
    </div>
  );
}
