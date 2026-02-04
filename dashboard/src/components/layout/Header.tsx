"use client";

import { usePathname } from "next/navigation";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/containers": "Container Management",
  "/history": "Conversation History",
  "/settings": "Settings",
};

export function Header() {
  const pathname = usePathname();
  const title = pageTitles[pathname] ?? "Dashboard";

  return (
    <header className="flex h-14 items-center border-b border-border bg-card px-6">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
    </header>
  );
}
