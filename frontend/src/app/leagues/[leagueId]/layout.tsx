"use client";

import { use } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { TopNav } from "@/components/layout/TopNav";
import { LeagueProvider } from "@/components/league/LeagueContext";
import { LeagueTabs } from "@/components/league/LeagueTabs";

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
      <TopNav />
      <LeagueProvider leagueId={leagueId}>
        <LeagueTabs />
        {children}
      </LeagueProvider>
    </RequireAuth>
  );
}
