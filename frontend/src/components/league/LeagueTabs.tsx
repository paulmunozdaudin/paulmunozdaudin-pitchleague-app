"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { useLeague } from "./LeagueContext";

export function LeagueTabs() {
  const { league } = useLeague();
  const pathname = usePathname();
  const base = `/leagues/${league.id}`;

  const tabs = [
    { href: `${base}/gameweek`, label: "Jornada" },
    { href: `${base}/ranking`, label: "Ranking" },
    ...(league.is_admin ? [{ href: `${base}/admin`, label: "Admin" }] : []),
  ];

  return (
    <div className="border-b border-border">
      <div className="mx-auto flex max-w-3xl items-center gap-1 overflow-x-auto px-4 py-3 scrollbar-none sm:px-6">
        <span className="mr-3 shrink-0 font-semibold">{league.name}</span>
        {tabs.map((tab) => {
          const active = pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                active ? "bg-primary text-primary-foreground" : "text-muted hover:bg-surface-raised"
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
