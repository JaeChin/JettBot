import { HistoryList } from "@/components/dashboard/HistoryList";
import { extendedHistory } from "@/lib/mock-data";

export default function HistoryPage() {
  return (
    <div className="flex flex-col gap-6">
      <HistoryList entries={extendedHistory} title="Conversation History" />
    </div>
  );
}
