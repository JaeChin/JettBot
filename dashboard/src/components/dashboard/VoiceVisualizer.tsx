"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type VoiceState = "idle" | "listening" | "processing" | "speaking";

const stateConfig: Record<VoiceState, { label: string; color: string; barColor: string }> = {
  idle: { label: "Idle", color: "text-muted-foreground", barColor: "bg-muted-foreground" },
  listening: { label: "Listening...", color: "text-cyan-400", barColor: "bg-cyan-400" },
  processing: { label: "Processing...", color: "text-orange-400", barColor: "bg-orange-400" },
  speaking: { label: "Speaking...", color: "text-purple-400", barColor: "bg-purple-400" },
};

export function VoiceVisualizer() {
  const [state] = useState<VoiceState>("idle");
  const config = stateConfig[state];

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Voice Pipeline
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col items-center justify-center gap-4 py-8">
        {/* Waveform placeholder */}
        <div className="flex items-end gap-1" aria-hidden="true">
          {Array.from({ length: 24 }).map((_, i) => {
            const height = state === "idle"
              ? 4
              : Math.random() * 28 + 4;
            return (
              <div
                key={i}
                className={`w-1 rounded-full transition-all duration-150 ${config.barColor}`}
                style={{ height: `${height}px`, opacity: state === "idle" ? 0.3 : 0.8 }}
              />
            );
          })}
        </div>

        {/* State label */}
        <span className={`text-sm font-medium ${config.color}`}>
          {config.label}
        </span>

        {/* Transcript placeholder */}
        <p className="text-center text-xs text-muted-foreground">
          {state === "idle"
            ? "Waiting for wake word..."
            : "\"What's on my schedule tomorrow?\""}
        </p>
      </CardContent>
    </Card>
  );
}
