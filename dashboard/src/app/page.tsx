import { StatusBar } from "@/components/dashboard/StatusBar";
import { MetricsGrid } from "@/components/dashboard/MetricsGrid";
import { VoiceVisualizer } from "@/components/dashboard/VoiceVisualizer";
import { HistoryList } from "@/components/dashboard/HistoryList";
import { recentHistory } from "@/lib/mock-data";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <StatusBar />
      <MetricsGrid />
      <div className="grid grid-cols-2 gap-6">
        <VoiceVisualizer />
        <HistoryList entries={recentHistory} />
      </div>
    </div>
  );
}
