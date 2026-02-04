"use client";

import { Badge } from "@/components/ui/badge";
import { Cpu, Gauge, Zap, Database } from "lucide-react";
import { systemStatus } from "@/lib/mock-data";

export function StatusBar() {
  const { online, gpu, latency, cacheHitRate } = systemStatus;

  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-3">
      {/* Online status */}
      <div className="flex items-center gap-2">
        <span
          className={`inline-block size-2.5 rounded-full ${
            online ? "bg-green-500" : "bg-red-500"
          }`}
          aria-label={online ? "System online" : "System offline"}
        />
        <span className="text-sm font-medium text-foreground">
          {online ? "Jett Online" : "Offline"}
        </span>
      </div>

      <div className="h-4 w-px bg-border" role="separator" />

      {/* GPU */}
      <div className="flex items-center gap-1.5">
        <Cpu className="size-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">GPU:</span>
        <Badge variant="secondary" className="font-mono text-xs">
          {gpu}%
        </Badge>
      </div>

      <div className="h-4 w-px bg-border" role="separator" />

      {/* Latency */}
      <div className="flex items-center gap-1.5">
        <Gauge className="size-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Latency:</span>
        <Badge variant="secondary" className="font-mono text-xs">
          {latency}ms
        </Badge>
      </div>

      <div className="h-4 w-px bg-border" role="separator" />

      {/* Cache hit rate */}
      <div className="flex items-center gap-1.5">
        <Database className="size-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Cache:</span>
        <Badge variant="secondary" className="font-mono text-xs">
          {cacheHitRate}%
        </Badge>
      </div>
    </div>
  );
}
