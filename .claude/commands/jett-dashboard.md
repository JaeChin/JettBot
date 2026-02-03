# Jett Dashboard

Activate Dashboard Agent for the web control panel.

## Agent Identity

You are working on **Jett's dashboard** — the visual interface for monitoring and control.

Your goal: **Real-time metrics, clean design, accessibility-first.**

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Framework | Next.js 14 (App Router) | React + SSR + API routes |
| Styling | Tailwind CSS | Utility-first, fast iteration |
| Components | shadcn/ui | Accessible, copy-paste components |
| Charts | Tremor | Analytics-focused, dashboard-ready |
| Voice Viz | react-voice-visualizer | Real-time waveforms |
| Icons | lucide-react | Consistent, tree-shakeable |

## Dashboard Sections

### 1. System Status (Header)
```
┌──────────────────────────────────────────────────────────┐
│  🟢 Jett Online    GPU: 62%    Latency: 340ms    Cache: 78%  │
└──────────────────────────────────────────────────────────┘
```

### 2. Voice Visualization (Hero)
```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│            ▂▄▆█▆▄▂  [Listening...]                      │
│                                                          │
│   "What's on my schedule tomorrow?"                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 3. Metrics Grid
```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Queries   │ │   Local %   │ │  Cache Hit  │ │  API Cost   │
│    1,247    │ │    72%      │ │    78%      │ │   $4.32     │
│   today     │ │   target:70%│ │  target:70% │ │  this month │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### 4. Container Status
```
┌──────────────────────────────────────────────────────────┐
│ Container      Status     CPU      Memory    Actions     │
├──────────────────────────────────────────────────────────┤
│ n8n           🟢 Running  12%      256MB     [Restart]   │
│ postgres      🟢 Running   3%      128MB     [Restart]   │
│ qdrant        🟢 Running   8%      512MB     [Restart]   │
└──────────────────────────────────────────────────────────┘
```

### 5. Conversation History
```
┌──────────────────────────────────────────────────────────┐
│ 10:30 AM  "What's the weather?"              [Local] 180ms│
│ 10:32 AM  "Turn off the lights"              [Local] 95ms │
│ 10:45 AM  "Explain the AWS shared resp..."   [Cloud] 2.1s │
│ 11:00 AM  "Set a timer for 5 minutes"        [Cache] 12ms │
└──────────────────────────────────────────────────────────┘
```

## Component Structure

```
app/
├── layout.tsx              # Root layout with sidebar
├── page.tsx                # Dashboard home (status + metrics)
├── containers/
│   └── page.tsx            # Container management
├── history/
│   └── page.tsx            # Conversation history
├── calendar/
│   └── page.tsx            # Calendar integration
└── settings/
    └── page.tsx            # Configuration

components/
├── ui/                     # shadcn/ui components
│   ├── button.tsx
│   ├── card.tsx
│   └── ...
├── dashboard/
│   ├── StatusBar.tsx       # Top status indicators
│   ├── VoiceVisualizer.tsx # Waveform display
│   ├── MetricCard.tsx      # KPI cards
│   ├── ContainerTable.tsx  # Container status
│   └── HistoryList.tsx     # Conversation log
└── layout/
    ├── Sidebar.tsx
    └── Header.tsx
```

## Real-Time Data Flow

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   Backend   │ ──────────────────▶│  Dashboard  │
│   (FastAPI) │                    │  (Next.js)  │
└─────────────┘                    └─────────────┘
      │
      │ Events:
      │ - voice_state (idle/listening/processing/speaking)
      │ - metrics_update (gpu, latency, cache)
      │ - query_completed (route, duration, response)
      │ - container_status (name, state, resources)
```

## Implementation Checklist

### Phase 1: Scaffold
- [ ] Create Next.js 14 app with App Router
- [ ] Install Tailwind CSS
- [ ] Set up shadcn/ui
- [ ] Create basic layout with sidebar

### Phase 2: Status Display
- [ ] StatusBar component with live indicators
- [ ] WebSocket connection to backend
- [ ] GPU/latency/cache metric display

### Phase 3: Voice Visualization
- [ ] Integrate react-voice-visualizer
- [ ] State management (idle → listening → processing → speaking)
- [ ] Transcript display

### Phase 4: Metrics
- [ ] MetricCard component with Tremor
- [ ] Historical charts (queries over time)
- [ ] Cost tracking display

### Phase 5: Container Management
- [ ] ContainerTable with status
- [ ] Action buttons (restart only — no delete!)
- [ ] Confirm dialogs for actions

### Phase 6: Calendar Integration
- [ ] Google Calendar OAuth
- [ ] Event list display
- [ ] Natural language event creation

## Accessibility Requirements

Every component must have:
- [ ] Semantic HTML (no `<div>` buttons)
- [ ] Keyboard navigation
- [ ] Focus indicators
- [ ] Color contrast ≥ 4.5:1
- [ ] ARIA labels where needed
- [ ] Screen reader tested

## Color States

| State | Color | Tailwind |
|-------|-------|----------|
| Idle | Gray | `text-gray-400` |
| Listening | Blue (pulsing) | `text-blue-500 animate-pulse` |
| Processing | Orange | `text-orange-500` |
| Speaking | Purple | `text-purple-500` |
| Error | Red | `text-red-500` |
| Success | Green | `text-green-500` |

## Example Component

```tsx
// components/dashboard/MetricCard.tsx
import { Card, Metric, Text, ProgressBar } from "@tremor/react";

interface MetricCardProps {
  title: string;
  value: string | number;
  target?: number;
  current?: number;
}

export function MetricCard({ title, value, target, current }: MetricCardProps) {
  const progress = target && current ? (current / target) * 100 : undefined;
  
  return (
    <Card className="max-w-xs">
      <Text>{title}</Text>
      <Metric>{value}</Metric>
      {progress !== undefined && (
        <ProgressBar value={progress} className="mt-2" />
      )}
    </Card>
  );
}
```

## Security Notes

- Dashboard runs locally (not exposed to internet)
- Container actions go through the secure API wrapper
- No direct Docker socket access from frontend
- WebSocket connection is localhost only

## Interview Framing

> "The dashboard demonstrates full-stack capability — Next.js with real-time WebSocket updates, Tremor analytics components, and proper accessibility. But the interesting part is what it doesn't do: container actions go through a secure API wrapper with rate limiting and audit logging. The frontend can only trigger pre-approved operations."

## Next Step

After dashboard basics work: `/jett-security` to ensure all actions are properly gated
