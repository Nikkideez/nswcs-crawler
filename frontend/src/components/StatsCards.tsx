import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Stats } from "@/api/types";

interface StatsCardsProps {
  stats: Stats | null;
  loading: boolean;
}

const cards = [
  { key: "total" as const, label: "TOTAL ORDERS", color: "text-foreground" },
  {
    key: "stop_work" as const,
    label: "STOP WORK ORDERS",
    color: "text-primary",
  },
  {
    key: "rectification" as const,
    label: "RECTIFICATION ORDERS",
    color: "text-[#f3631b]",
  },
  {
    key: "prohibition" as const,
    label: "PROHIBITION ORDERS",
    color: "text-primary",
  },
];

export function StatsCards({ stats, loading }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <Card key={c.key}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium tracking-wide text-muted-foreground">
              {c.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-10 w-16" />
            ) : (
              <p className={`text-4xl font-bold ${c.color}`}>
                {stats?.[c.key] ?? 0}
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
