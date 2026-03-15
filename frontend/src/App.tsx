import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import { Header } from "@/components/Header";
import { StatsCards } from "@/components/StatsCards";
import { FilterBar } from "@/components/FilterBar";
import { OrdersTable } from "@/components/OrdersTable";
import { CrawlInfo } from "@/components/CrawlInfo";
import { fetchOrders, fetchStats, triggerCrawl } from "@/api/client";
import type { Order, Stats, CrawlResult } from "@/api/types";

export default function App() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [crawling, setCrawling] = useState(false);
  const [lastResult, setLastResult] = useState<CrawlResult | null>(null);

  const loadData = useCallback(async (orderType?: string) => {
    setLoading(true);
    try {
      const [ordersData, statsData] = await Promise.all([
        fetchOrders(orderType || undefined),
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

  useEffect(() => {
    loadData(filter);
  }, [filter, loadData]);

  const handleCrawl = async () => {
    setCrawling(true);
    setLastResult(null);
    try {
      const result = await triggerCrawl();
      setLastResult(result);
      toast.success(
        `Crawl complete — ${result.new_orders} new order${result.new_orders !== 1 ? "s" : ""} found`,
      );
      await loadData(filter);
    } catch {
      toast.error("Crawl failed");
    } finally {
      setCrawling(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header onCrawl={handleCrawl} crawling={crawling} lastResult={lastResult} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        <StatsCards stats={stats} loading={loading} />
        <CrawlInfo lastCrawl={stats?.last_crawl ?? null} />
        <FilterBar value={filter} onChange={setFilter} />
        <OrdersTable orders={orders} loading={loading} />
      </main>
      <Toaster richColors position="bottom-right" />
    </div>
  );
}
