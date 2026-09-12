"use client";

import { motion } from "framer-motion";
import { ChevronDown, Lock, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import { useBetSlip } from "@/components/gameweek/BetSlipContext";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { MARKET_LABELS, selectionLabel } from "@/lib/markets";
import { cn, formatOdds } from "@/lib/utils";
import type { Market, MatchInsight, Match, Odds } from "@/types/api";

function kickoffLabel(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("es-ES", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

const STATUS_VARIANT: Record<string, "default" | "success" | "danger" | "outline"> = {
  pending: "default",
  won: "success",
  lost: "danger",
  void: "outline",
};

export function MatchCard({ leagueId, match }: { leagueId: string; match: Match }) {
  const api = useApi();
  const { legs, addOrReplaceLeg } = useBetSlip();
  const [insight, setInsight] = useState<MatchInsight | null>(null);
  const [loadingInsight, setLoadingInsight] = useState(false);
  const [showMoreMarkets, setShowMoreMarkets] = useState(false);

  const marketsPresent = useMemo(
    () => Array.from(new Set(match.odds.map((o) => o.market))) as Market[],
    [match.odds]
  );
  const winnerOdds = match.odds.filter((o) => o.market === "winner");
  const otherMarkets = marketsPresent.filter((m) => m !== "winner");
  const slipLeg = legs.find((l) => l.match.id === match.id);

  async function loadInsight() {
    if (insight || loadingInsight) return;
    setLoadingInsight(true);
    try {
      const result = await api.get<MatchInsight>(`/leagues/${leagueId}/matches/${match.id}/insight`);
      setInsight(result);
    } catch {
      setInsight({ match_id: match.id, summary: "No se pudo cargar el análisis.", provider: "none", model: { home: 0, draw: 0, away: 0, source: "market" } });
    } finally {
      setLoadingInsight(false);
    }
  }

  function pick(odds: Odds) {
    if (match.is_locked) return;
    addOrReplaceLeg({ match, market: odds.market, selection: odds.selection, line: odds.line, price: odds.price });
  }

  function OddsButton({ odds }: { odds: Odds }) {
    const isSelected = slipLeg?.market === odds.market && slipLeg?.selection === odds.selection && slipLeg?.line === odds.line;
    return (
      <motion.button
        whileTap={{ scale: 0.96 }}
        disabled={match.is_locked}
        onClick={() => pick(odds)}
        className={cn(
          "flex flex-col items-center gap-1 rounded-xl border px-2 py-3 transition-colors disabled:cursor-not-allowed disabled:opacity-50",
          isSelected ? "border-primary bg-primary/10" : "border-border bg-surface-raised/60 hover:border-primary/40"
        )}
      >
        <span className="text-[11px] text-muted">{selectionLabel(odds.selection, match.home_team, match.away_team, odds.line)}</span>
        <span className="text-base font-bold tabular-nums">{formatOdds(odds.price)}</span>
      </motion.button>
    );
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

      {match.my_legs.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {match.my_legs.map((leg, i) => (
            <Badge key={i} variant={STATUS_VARIANT[leg.status] ?? "outline"}>
              {selectionLabel(leg.selection, match.home_team, match.away_team, leg.line)} @{" "}
              {formatOdds(leg.odds_price_at_pick)}
            </Badge>
          ))}
        </div>
      )}

      <div className="mt-4 grid grid-cols-3 gap-2">
        {winnerOdds.map((odds) => (
          <OddsButton key={odds.selection} odds={odds} />
        ))}
      </div>

      {otherMarkets.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setShowMoreMarkets((v) => !v)}
            className="flex items-center gap-1 text-xs font-medium text-muted hover:text-foreground"
          >
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", showMoreMarkets && "rotate-180")} />
            Más mercados
          </button>
          {showMoreMarkets && (
            <div className="mt-2 flex flex-col gap-3">
              {otherMarkets.map((m) => (
                <div key={m}>
                  <p className="mb-1.5 text-[11px] uppercase tracking-wide text-muted">{MARKET_LABELS[m]}</p>
                  <div className="grid grid-cols-2 gap-2">
                    {match.odds
                      .filter((o) => o.market === m)
                      .map((odds) => (
                        <OddsButton key={`${odds.market}-${odds.selection}-${odds.line ?? ""}`} odds={odds} />
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <button
        onClick={loadInsight}
        className="mt-3 flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
      >
        <Sparkles className="h-3 w-3" /> Ver análisis IA
      </button>
      {loadingInsight && <Spinner className="mt-2 h-4 w-4" />}
      {insight && (
        <div className="mt-2 rounded-lg bg-surface-raised p-3 text-xs text-muted">
          <p>{insight.summary}</p>
          {insight.model.source !== "none" && (
            <p className="mt-1.5 flex items-center gap-2 tabular-nums text-[11px]">
              <span className="text-foreground/70">Modelo ({insight.model.source}):</span>
              <span>{Math.round(insight.model.home * 100)}%</span>
              <span>{Math.round(insight.model.draw * 100)}%</span>
              <span>{Math.round(insight.model.away * 100)}%</span>
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
