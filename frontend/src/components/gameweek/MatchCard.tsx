"use client";

import { motion } from "framer-motion";
import { Lock, Sparkles } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { selectionLabel } from "@/lib/markets";
import { cn, formatOdds } from "@/lib/utils";
import type { Match, MatchInsight, Selection } from "@/types/api";

function kickoffLabel(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("es-ES", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function MatchCard({
  leagueId,
  match,
  onPick,
}: {
  leagueId: string;
  match: Match;
  onPick: (selection: Selection) => void;
}) {
  const api = useApi();
  const [insight, setInsight] = useState<string | null>(null);
  const [loadingInsight, setLoadingInsight] = useState(false);

  const winnerOdds = match.odds.filter((o) => o.market === "winner");
  const mySelection = match.my_prediction?.selection;

  async function loadInsight() {
    if (insight || loadingInsight) return;
    setLoadingInsight(true);
    try {
      const result = await api.get<MatchInsight>(`/leagues/${leagueId}/matches/${match.id}/insight`);
      setInsight(result.summary);
    } catch {
      setInsight("No se pudo cargar el análisis.");
    } finally {
      setLoadingInsight(false);
    }
  }

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between text-xs text-muted">
        <span>{match.competition}</span>
        <span className="flex items-center gap-1.5">
          {match.is_locked && <Lock className="h-3 w-3" />}
          {kickoffLabel(match.kickoff_at)}
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-base font-semibold">{match.home_team}</p>
        <span className="text-xs font-medium text-muted">vs</span>
        <p className="text-right text-base font-semibold">{match.away_team}</p>
      </div>

      {match.my_prediction && (
        <div className="mt-3">
          <Badge variant={match.my_prediction.status === "pending" ? "default" : match.my_prediction.status === "won" ? "success" : match.my_prediction.status === "lost" ? "danger" : "outline"}>
            {selectionLabel(match.my_prediction.selection, match.home_team, match.away_team, match.my_prediction.line)} ·{" "}
            {match.my_prediction.stake.toLocaleString("es-ES")} cr
          </Badge>
        </div>
      )}

      <div className="mt-4 grid grid-cols-3 gap-2">
        {winnerOdds.map((odds) => (
          <motion.button
            key={odds.selection}
            whileTap={{ scale: 0.96 }}
            disabled={match.is_locked}
            onClick={() => onPick(odds.selection)}
            className={cn(
              "flex flex-col items-center gap-1 rounded-xl border px-2 py-3 transition-colors disabled:cursor-not-allowed disabled:opacity-50",
              mySelection === odds.selection
                ? "border-primary bg-primary/10"
                : "border-border bg-surface-raised/60 hover:border-primary/40"
            )}
          >
            <span className="text-[11px] text-muted">
              {selectionLabel(odds.selection, match.home_team, match.away_team)}
            </span>
            <span className="text-base font-bold tabular-nums">{formatOdds(odds.price)}</span>
          </motion.button>
        ))}
      </div>

      <button
        onClick={loadInsight}
        className="mt-3 flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
      >
        <Sparkles className="h-3 w-3" /> Ver análisis IA
      </button>
      {loadingInsight && <Spinner className="mt-2 h-4 w-4" />}
      {insight && <p className="mt-2 rounded-lg bg-surface-raised p-3 text-xs text-muted">{insight}</p>}
    </Card>
  );
}
