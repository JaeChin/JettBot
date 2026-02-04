"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RotateCw } from "lucide-react";
import { containers, type ContainerInfo } from "@/lib/mock-data";

const statusBadge: Record<ContainerInfo["status"], { label: string; className: string }> = {
  running: { label: "Running", className: "bg-green-500/15 text-green-400 border-green-500/30" },
  stopped: { label: "Stopped", className: "bg-red-500/15 text-red-400 border-red-500/30" },
  error: { label: "Error", className: "bg-red-500/15 text-red-400 border-red-500/30" },
};

export function ContainerTable() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Containers
        </CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full" role="table">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
              <th className="pb-3 pr-4" scope="col">Container</th>
              <th className="pb-3 pr-4" scope="col">Status</th>
              <th className="pb-3 pr-4" scope="col">CPU</th>
              <th className="pb-3 pr-4" scope="col">Memory</th>
              <th className="pb-3 text-right" scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {containers.map((container) => {
              const badge = statusBadge[container.status];
              return (
                <tr
                  key={container.name}
                  className="border-b border-border last:border-0"
                >
                  <td className="py-3 pr-4 text-sm font-medium text-foreground">
                    {container.name}
                  </td>
                  <td className="py-3 pr-4">
                    <Badge
                      variant="outline"
                      className={badge.className}
                    >
                      {badge.label}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 font-mono text-sm text-muted-foreground">
                    {container.cpu}%
                  </td>
                  <td className="py-3 pr-4 font-mono text-sm text-muted-foreground">
                    {container.memory} MB
                  </td>
                  <td className="py-3 text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      disabled
                      aria-label={`Restart ${container.name}`}
                    >
                      <RotateCw className="size-4" />
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
