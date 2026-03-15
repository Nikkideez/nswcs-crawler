import { FileSearch } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <FileSearch className="h-12 w-12 mb-4" />
      <p className="text-lg font-medium">No orders found</p>
      <p className="text-sm">Try a different filter or trigger a new crawl.</p>
    </div>
  );
}
