export interface Order {
  id: number;
  title: string;
  order_type: string;
  company_name: string;
  acn: string;
  address: string;
  publication_date: string;
  source_url: string;
  pdf_url: string | null;
  first_seen: string | null;
}

export interface Stats {
  total: number;
  stop_work: number;
  rectification: number;
  prohibition: number;
  last_crawl: {
    started_at: string;
    finished_at: string | null;
    orders_found: number;
    new_orders: number;
    status: string;
  } | null;
}

export interface CrawlResult {
  status: string;
  new_orders: number;
  new: { title: string; company_name: string }[];
}
