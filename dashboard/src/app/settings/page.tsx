import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Mic, Brain, Server, KeyRound } from "lucide-react";

const settingsSections = [
  {
    title: "Voice Settings",
    description: "Wake word, VAD sensitivity, STT model configuration",
    icon: Mic,
  },
  {
    title: "LLM Configuration",
    description: "Local model selection, cloud routing threshold, temperature",
    icon: Brain,
  },
  {
    title: "VPS Connection",
    description: "WireGuard tunnel status, container management endpoints",
    icon: Server,
  },
  {
    title: "API Keys",
    description: "Claude API, calendar integrations, external services",
    icon: KeyRound,
  },
];

export default function SettingsPage() {
  return (
    <div className="grid grid-cols-2 gap-6">
      {settingsSections.map((section) => (
        <Card key={section.title}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-secondary">
                <section.icon className="size-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-base">{section.title}</CardTitle>
                <CardDescription>{section.description}</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Configuration options will appear here.
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
