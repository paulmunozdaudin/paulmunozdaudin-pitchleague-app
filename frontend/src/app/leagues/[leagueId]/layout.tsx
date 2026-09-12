"use client";

import { use } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { TopNav } from "@/components/layout/TopNav";
import { LeagueProvider } from "@/components/league/LeagueContext";
import { LeagueBottomNav, LeagueSidebar } from "@/components/league/LeagueNav";

export default function LeagueLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ leagueId: string }>;
}) {
  const { leagueId } = use(params);

  return (
    <RequireAuth>
      <LeagueProvider leagueId={leagueId}>
        <div className="lg:flex lg:min-h-screen">
          <LeagueSidebar />
          <div className="min-w-0 flex-1">
            <div className="lg:hidden">
              <TopNav />
            </div>
            <div className="pb-16 lg:pb-0">{children}</div>
          </div>
        </div>
        <LeagueBottomNav />
      </LeagueProvider>
    </RequireAuth>
  );
}
