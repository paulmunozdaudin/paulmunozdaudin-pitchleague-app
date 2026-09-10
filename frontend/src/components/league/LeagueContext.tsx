"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import type { LeagueDetail } from "@/types/api";

interface LeagueContextValue {
  league: LeagueDetail;
  refresh: () => Promise<void>;
}

const LeagueContext = createContext<LeagueContextValue | null>(null);

export function useLeague(): LeagueContextValue {
  const ctx = useContext(LeagueContext);
  if (!ctx) throw new Error("useLeague must be used within LeagueProvider");
  return ctx;
}

export function LeagueProvider({ leagueId, children }: { leagueId: string; children: ReactNode }) {
  const api = useApi();
  const [league, setLeague] = useState<LeagueDetail | null>(null);

  const refresh = useCallback(async () => {
    const data = await api.get<LeagueDetail>(`/leagues/${leagueId}`);
    setLeague(data);
  }, [api, leagueId]);

  useEffect(() => {
    if (api.ready) refresh();
  }, [api.ready, refresh]);

  if (!league) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return <LeagueContext.Provider value={{ league, refresh }}>{children}</LeagueContext.Provider>;
}
