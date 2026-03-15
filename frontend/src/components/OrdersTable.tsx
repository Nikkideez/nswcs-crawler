import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { Order } from "@/api/types";
import { EmptyState } from "./EmptyState";

interface OrdersTableProps {
  orders: Order[];
  loading: boolean;
}

function badgeLabel(type: string): string {
  const t = type.toLowerCase();
  if (t.includes("stop work")) return "STOP WORK";
  if (t.includes("rectification")) return "RECTIFICATION";
  if (t.includes("prohibition")) return "PROHIBITION";
  return type.toUpperCase();
}

function orderBadgeVariant(type: string) {
  const t = type.toLowerCase();
  if (t.includes("stop work")) return "destructive" as const;
  if (t.includes("rectification")) return "outline" as const;
  if (t.includes("prohibition")) return "secondary" as const;
  return "default" as const;
}

function orderBadgeClass(type: string) {
  const t = type.toLowerCase();
  if (t.includes("rectification"))
    return "border-[#f3631b] text-[#f3631b] bg-transparent";
  if (t.includes("prohibition"))
    return "bg-[#2e5299] text-white border-transparent";
  return "";
}

export function OrdersTable({ orders, loading }: OrdersTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (orders.length === 0) return <EmptyState />;

  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="uppercase text-xs tracking-wider">Type</TableHead>
            <TableHead className="uppercase text-xs tracking-wider">Company</TableHead>
            <TableHead className="uppercase text-xs tracking-wider">ACN</TableHead>
            <TableHead className="uppercase text-xs tracking-wider">Address</TableHead>
            <TableHead className="uppercase text-xs tracking-wider">Date</TableHead>
            <TableHead className="uppercase text-xs tracking-wider">Links</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map((order) => (
            <TableRow key={order.id}>
              <TableCell>
                <Badge
                  variant={orderBadgeVariant(order.order_type)}
                  className={`text-[10px] tracking-wide ${orderBadgeClass(order.order_type)}`}
                >
                  {badgeLabel(order.order_type)}
                </Badge>
              </TableCell>
              <TableCell className="font-medium">
                {order.company_name}
              </TableCell>
              <TableCell className="font-mono text-sm">
                {order.acn || "—"}
              </TableCell>
              <TableCell>{order.address}</TableCell>
              <TableCell className="whitespace-nowrap">
                {order.publication_date}
              </TableCell>
              <TableCell>
                <span className="whitespace-nowrap">
                  <a
                    href={order.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-sm"
                  >
                    Details
                  </a>
                  {order.pdf_url && (
                    <>
                      {" · "}
                      <a
                        href={order.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline text-sm"
                      >
                        PDF
                      </a>
                    </>
                  )}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
