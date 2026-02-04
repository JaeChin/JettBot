import { MetricCard } from "./MetricCard";
import { metrics } from "@/lib/mock-data";

export function MetricsGrid() {
  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard
        title="Queries Today"
        value={metrics.queriesToday.toLocaleString()}
        subtitle="since midnight"
      />
      <MetricCard
        title="Local Routing"
        value={`${metrics.localRouting}%`}
        subtitle="target: 70%"
        progress={metrics.localRouting}
      />
      <MetricCard
        title="Cache Hit Rate"
        value={`${metrics.cacheHitRate}%`}
        subtitle="target: 70%"
        progress={metrics.cacheHitRate}
      />
      <MetricCard
        title="API Cost (MTD)"
        value={`$${metrics.apiCostMtd.toFixed(2)}`}
        subtitle="this month"
      />
    </div>
  );
}
