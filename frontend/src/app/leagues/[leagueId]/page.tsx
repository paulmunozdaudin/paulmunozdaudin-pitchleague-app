"use client";

import { useSession } from "next-auth/react";
import Link from "next/link";
import { ArrowRight, Award, Flame, Sparkles, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useLeague } from "@/components/league/LeagueContext";
import { RankingTable } from "@/components/league/RankingTable";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { useLeagueRealtime } from "@/hooks/useLeagueRealtime";
import { ApiError } from "@/lib/api";
import type { Gameweek, LeagueActivity, RankingRow } from "@/types/api";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

function ActivityRow({ item }: { item: LeagueActivity }) {
  if (item.type === "bet_placed") {
    const legCount = Number(item.data.leg_count ?? 1);
    const combinedOdds = String(item.data.combined_odds ?? "");
    return (
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <TrendingUp className="h-4 w-4" />
        </span>
        <p className="text-sm">
          <span className="font-semibold">{item.user.name}</span> ha hecho{" "}
          {legCount > 1 ? `una combinada de ${legCount} selecciones` : "una predicción"} a cuota{" "}
          <span className="font-semibold text-primary">{combinedOdds}</span>
        </p>
      </div>
    );
  }

  if (item.type === "badge_earned") {
    const icon = String(item.data.icon ?? "🏅");
    const name = String(item.data.name ?? "");
    return (
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-warning/10 text-warning">
          <Award className="h-4 w-4" />
        </span>
        <p className="text-sm">
          <span className="font-semibold">{item.user.name}</span> ha desbloqueado el logro{" "}
          <span className="font-semibold">
            {icon} {name}
          </span>
        </p>
      </div>
    );
  }

  if (item.type === "streak_milestone") {
    return (
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-danger/10 text-danger">
          <Flame className="h-4 w-4" />
        </span>
        <p className="text-sm">
          <span className="font-semibold">{item.user.name}</span> está en racha
        </p>
      </div>
    );
  }

  const gameweekName = String(item.data.gameweek_name ?? "");
  const top3 = Array.isArray(item.data.top3) ? (item.data.top3 as { name: string; net_change: number }[]) : [];
  const leader = top3[0];
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-success/10 text-success">
        <Sparkles className="h-4 w-4" />
      </span>
      <p className="text-sm">
        <span className="font-semibold">{gameweekName}</span> ha terminado.{" "}
        {leader && (
          <>
            <span className="font-semibold">{leader.name}</span> lidera con{" "}
            <span className="font-semibold text-success">
              {leader.net_change >= 0 ? "+" : ""}
              {leader.net_change}
            </span>
          </>
        )}
      </p>
    </div>
  );
}

export default function LeagueHomePage() {
  const { league } = useLeague();
  const { data: session } = useSession();
  const api = useApi();
  const [activity, setActivity] = useState<LeagueActivity[] | null>(null);
  const [ranking, setRanking] = useState<RankingRow[] | null>(null);
  const [gameweek, setGameweek] = useState<Gameweek | null>(null);

  const load = useCallback(async () => {
    const [activityData, rankingData] = await Promise.all([
      api.get<LeagueActivity[]>(`/leagues/${league.id}/activity`),
      api.get<RankingRow[]>(`/leagues/${league.id}/rankings/season`),
    ]);
    setActivity(activityData);
    setRanking(rankingData);
    try {
      setGameweek(await api.get<Gameweek>(`/leagues/${league.id}/gameweeks/current`));
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) throw err;
      setGameweek(null);
    }
  }, [api, league.id]);

  useEffect(() => {
    if (api.ready) load();
  }, [api.ready, load]);

  useLeagueRealtime(league.id, (event) => {
    if (event.type === "gameweek_settled") load();
  });

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-surface-raised text-2xl">
          {league.avatar_emoji}
        </span>
        <div>
          <h1 className="text-xl font-bold">{league.name}</h1>
          <p className="text-sm text-muted">{league.member_count} jugadores</p>
        </div>
      </div>

      {gameweek && (
        <Link href={`/leagues/${league.id}/gameweek`}>
          <Card className="mb-6 flex items-center justify-between p-4 transition-colors hover:border-primary/40">
            <div>
              <p className="text-xs text-muted">
                {gameweek.status === "open" ? "Jornada abierta" : gameweek.status === "locked" ? "Jornada bloqueada" : gameweek.name}
              </p>
              <p className="text-sm font-semibold">{gameweek.name} · {gameweek.matches.length} partidos</p>
            </div>
            <ArrowRight className="h-4 w-4 text-muted" />
          </Card>
        </Link>
      )}

      {ranking && ranking.length > 0 && (
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted">Top de la liga</h2>
            <Link href={`/leagues/${league.id}/ranking`} className="text-xs font-medium text-primary hover:underline">
              Ver todo
            </Link>
          </div>
          <RankingTable rows={ranking.slice(0, 3)} youUserId={session?.user?.id} />
        </div>
      )}

      <h2 className="mb-2 text-sm font-semibold text-muted">Actividad reciente</h2>
      {activity === null && (
        <div className="flex justify-center py-10">
          <Spinner className="h-6 w-6" />
        </div>
      )}
      {activity && activity.length === 0 && (
        <Card className="p-6 text-center text-sm text-muted">
          Todavía no hay actividad. ¡Sé el primero en predecir!
        </Card>
      )}
      {activity && activity.length > 0 && (
        <div className="flex flex-col gap-3">
          {activity.map((item) => (
            <Card key={item.id} className="p-4">
              <ActivityRow item={item} />
              <p className="mt-1.5 pl-11 text-xs text-muted">{timeAgo(item.created_at)}</p>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
