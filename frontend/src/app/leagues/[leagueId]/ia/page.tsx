"use client";

import { Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useLeague } from "@/components/league/LeagueContext";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { ApiError } from "@/lib/api";
import type { Gameweek, Match, MatchInsight } from "@/types/api";

const SOURCE_LABELS: Record<string, string> = {
  elo: "Elo",
  poisson: "Poisson",
  dixon_coles: "Dixon-Coles",
  logistic_regression: "Regresión logística",
  gradient_boosting: "Gradient boosting",
  market: "Cuotas del mercado",
};

function ProbabilityBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex h-16 w-6 items-end overflow-hidden rounded-full bg-surface-raised">
        <div className={color} style={{ height: `${Math.round(value * 100)}%`, width: "100%" }} />
      </div>
      <span className="text-[11px] font-semibold tabular-nums">{Math.round(value * 100)}%</span>
      <span className="text-[10px] text-muted">{label}</span>
    </div>
  );
}

function MatchInsightCard({ leagueId, match }: { leagueId: string; match: Match }) {
  const api = useApi();
  const [insight, setInsight] = useState<MatchInsight | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    if (insight || loading) return;
    setLoading(true);
    setError(false);
    try {
      setInsight(await api.get<MatchInsight>(`/leagues/${leagueId}/matches/${match.id}/insight`));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, leagueId, match.id]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between text-xs text-muted">
        <span>{match.competition}</span>
      </div>
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-base font-semibold">{match.home_team}</p>
        <span className="text-xs font-medium text-muted">vs</span>
        <p className="text-right text-base font-semibold">{match.away_team}</p>
      </div>

      {loading && (
        <div className="mt-4 flex justify-center">
          <Spinner className="h-5 w-5" />
        </div>
      )}
      {error && <p className="mt-3 text-xs text-danger">No se pudo cargar el análisis.</p>}
      {insight && (
        <>
          <div className="mt-4 flex items-center justify-center gap-4">
            <ProbabilityBar label={match.home_team.split(" ")[0]} value={insight.model.home} color="bg-primary" />
            <ProbabilityBar label="Empate" value={insight.model.draw} color="bg-muted/50" />
            <ProbabilityBar label={match.away_team.split(" ")[0]} value={insight.model.away} color="bg-accent" />
          </div>
          <p className="mt-3 text-center text-[11px] text-muted">
            Modelo: {SOURCE_LABELS[insight.model.source] ?? insight.model.source}
          </p>
          <p className="mt-3 rounded-lg bg-surface-raised p-3 text-xs text-muted">{insight.summary}</p>
        </>
      )}
    </Card>
  );
}

export default function LeagueAiPage() {
  const { league } = useLeague();
  const api = useApi();
  const [gameweek, setGameweek] = useState<Gameweek | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!api.ready) return;
    api
      .get<Gameweek>(`/leagues/${league.id}/gameweeks/current`)
      .then(setGameweek)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready, league.id]);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-primary" />
        <h1 className="text-xl font-bold">Análisis IA</h1>
      </div>
      <p className="mb-6 text-sm text-muted">
        Probabilidades calculadas por nuestro motor estadístico (Elo, Poisson, Dixon-Coles y modelos de aprendizaje
        automático, validados por rendimiento real), no inventadas.
      </p>

      {notFound && <Card className="p-6 text-center text-sm text-muted">No hay una jornada abierta ahora mismo.</Card>}
      {!notFound && !gameweek && (
        <div className="flex justify-center py-10">
          <Spinner className="h-6 w-6" />
        </div>
      )}
      {gameweek && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {gameweek.matches.map((match) => (
            <MatchInsightCard key={match.id} leagueId={league.id} match={match} />
          ))}
        </div>
      )}
    </main>
  );
}
