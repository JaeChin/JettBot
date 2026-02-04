export const systemStatus = {
  online: true,
  gpu: 62,
  latency: 340,
  cacheHitRate: 78,
};

export const metrics = {
  queriesToday: 147,
  localRouting: 72,
  cacheHitRate: 78,
  apiCostMtd: 4.32,
};

export type ContainerInfo = {
  name: string;
  status: "running" | "stopped" | "error";
  cpu: number;
  memory: number;
};

export const containers: ContainerInfo[] = [
  { name: "n8n", status: "running", cpu: 12, memory: 256 },
  { name: "postgres", status: "running", cpu: 3, memory: 128 },
  { name: "qdrant", status: "running", cpu: 8, memory: 512 },
];

export type HistoryEntry = {
  id: number;
  timestamp: string;
  query: string;
  route: "local" | "cloud" | "cache";
  latency: number;
};

export const recentHistory: HistoryEntry[] = [
  { id: 1, timestamp: "10:30 AM", query: "What's the weather?", route: "local", latency: 180 },
  { id: 2, timestamp: "10:32 AM", query: "Turn off the lights", route: "local", latency: 95 },
  { id: 3, timestamp: "10:45 AM", query: "Explain the AWS shared responsibility model", route: "cloud", latency: 2100 },
  { id: 4, timestamp: "11:00 AM", query: "Set a timer for 5 minutes", route: "cache", latency: 12 },
  { id: 5, timestamp: "11:15 AM", query: "What's on my calendar tomorrow?", route: "local", latency: 230 },
];

export const extendedHistory: HistoryEntry[] = [
  ...recentHistory,
  { id: 6, timestamp: "11:30 AM", query: "Remind me to call the dentist", route: "local", latency: 145 },
  { id: 7, timestamp: "11:45 AM", query: "What are the best practices for Docker security?", route: "cloud", latency: 1890 },
  { id: 8, timestamp: "12:00 PM", query: "Play some music", route: "local", latency: 78 },
  { id: 9, timestamp: "12:15 PM", query: "What's the weather?", route: "cache", latency: 8 },
  { id: 10, timestamp: "12:30 PM", query: "Summarize my unread emails", route: "cloud", latency: 2450 },
];
