"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";

import { RankingTable } from "@/components/league/RankingTable";
import { useLeague } from "@/components/league/LeagueContext";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { useLeagueRealtime } from "@/hooks/useLeagueRealtime";
import { ApiError } from "@/lib/api";
import type { Gameweek, RankingRow } from "@/types/api";

export default function RankingPage() {
  const { league } = useLeague();
  const { data: session } = useSession();
  const api = useApi();
  const [season, setSeason] = useState<RankingRow[] | null>(null);
  const [gameweek, setGameweek] = useState<RankingRow[] | null>(null);
  const [gameweekLabel, setGameweekLabel] = useState<string | null>(null);
  const [tab, setTab] = useState("season");

  async function load() {
    const seasonRanking = await api.get<RankingRow[]>(`/leagues/${league.id}/rankings/season`);
    setSeason(seasonRanking);

    try {
      const currentGameweek = await api.get<Gameweek>(`/leagues/${league.id}/gameweeks/current`);
      const gwRanking = await api.get<RankingRow[]>(`/leagues/${league.id}/rankings/${currentGameweek.id}`);
      setGameweek(gwRanking);
      setGameweekLabel(currentGameweek.name);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) throw err;
    }
  }

  useEffect(() => {
    if (api.ready) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready, league.id]);

  useLeagueRealtime(league.id, (event) => {
    if (event.type === "gameweek_settled") load();
  });

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <h1 className="mb-1 text-2xl font-bold">🏆 Ranking</h1>
      <p className="mb-6 text-sm text-muted">{league.name}</p>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="season">Temporada</TabsTrigger>
          <TabsTrigger value="gameweek" disabled={!gameweek}>
            {gameweekLabel ?? "Jornada actual"}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="season">
          {season ? <RankingTable rows={season} youUserId={session?.user?.id} /> : <Spinner />}
        </TabsContent>
        <TabsContent value="gameweek">
          {gameweek ? (
            <RankingTable rows={gameweek} youUserId={session?.user?.id} />
          ) : (
            <p className="text-sm text-muted">No hay una jornada en curso.</p>
          )}
        </TabsContent>
      </Tabs>
    </main>
  );
}
