import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type HistoryEntry } from "@/lib/mock-data";

const routeBadge: Record<HistoryEntry["route"], { label: string; className: string }> = {
  local: { label: "Local", className: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30" },
  cloud: { label: "Cloud", className: "bg-purple-500/15 text-purple-400 border-purple-500/30" },
  cache: { label: "Cache", className: "bg-green-500/15 text-green-400 border-green-500/30" },
};

function formatLatency(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

interface HistoryListProps {
  entries: HistoryEntry[];
  title?: string;
}

export function HistoryList({ entries, title = "Recent Conversations" }: HistoryListProps) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {entries.map((entry) => {
          const badge = routeBadge[entry.route];
          return (
            <div
              key={entry.id}
              className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-secondary"
            >
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {entry.timestamp}
              </span>
              <span className="flex-1 truncate text-sm text-foreground">
                {entry.query}
              </span>
              <Badge variant="outline" className={badge.className}>
                {badge.label}
              </Badge>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {formatLatency(entry.latency)}
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
