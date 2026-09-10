"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/useApi";
import { ApiError } from "@/lib/api";
import { MARKET_LABELS, selectionLabel } from "@/lib/markets";
import { cn, formatOdds } from "@/lib/utils";
import type { Market, Match, Prediction, Selection } from "@/types/api";

const QUICK_FRACTIONS = [0.25, 0.5, 1];
const STEP = 100;

export function PredictionDialog({
  open,
  onOpenChange,
  leagueId,
  gameweekId,
  match,
  availableBudget,
  initialMarket,
  initialSelection,
  onConfirmed,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leagueId: string;
  gameweekId: string;
  match: Match;
  availableBudget: number;
  initialMarket: Market;
  initialSelection: Selection;
  onConfirmed: (prediction: Prediction) => void;
}) {
  const api = useApi();
  const [market, setMarket] = useState<Market>(initialMarket);
  const [selection, setSelection] = useState<Selection>(initialSelection);
  const [stake, setStake] = useState(Math.min(1000, availableBudget));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setMarket(initialMarket);
      setSelection(initialSelection);
      setStake(Math.min(1000, availableBudget));
      setError(null);
    }
  }, [open, initialMarket, initialSelection, availableBudget]);

  const marketsPresent = useMemo(
    () => Array.from(new Set(match.odds.map((o) => o.market))) as Market[],
    [match.odds]
  );
  const optionsForMarket = match.odds.filter((o) => o.market === market);
  const chosenOdds = optionsForMarket.find((o) => o.selection === selection);
  const potentialPayout = chosenOdds ? Math.round(stake * Number(chosenOdds.price)) : 0;

  async function handleConfirm() {
    if (!chosenOdds || stake <= 0) return;
    setLoading(true);
    setError(null);
    try {
      const prediction = await api.post<Prediction>(`/leagues/${leagueId}/gameweeks/${gameweekId}/predictions`, {
        match_id: match.id,
        market,
        selection,
        line: chosenOdds.line,
        stake,
      });
      onConfirmed(prediction);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo confirmar la predicción.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle>
          {match.home_team} vs {match.away_team}
        </DialogTitle>
        <DialogDescription>Elige mercado, selección y cuánto quieres invertir.</DialogDescription>

        <Tabs value={market} onValueChange={(v) => setMarket(v as Market)} className="mt-4">
          <TabsList className="w-full flex-wrap">
            {marketsPresent.map((m) => (
              <TabsTrigger key={m} value={m} className="flex-1">
                {MARKET_LABELS[m]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <div className="mt-4 grid grid-cols-2 gap-2">
          {optionsForMarket.map((odds) => (
            <button
              key={`${odds.market}-${odds.selection}-${odds.line ?? ""}`}
              onClick={() => setSelection(odds.selection)}
              className={cn(
                "flex flex-col items-start rounded-xl border px-4 py-3 text-left transition-colors",
                selection === odds.selection
                  ? "border-primary bg-primary/10"
                  : "border-border bg-surface hover:border-primary/40"
              )}
            >
              <span className="text-sm text-muted">
                {selectionLabel(odds.selection, match.home_team, match.away_team, odds.line)}
              </span>
              <span className="text-lg font-bold tabular-nums">{formatOdds(odds.price)}</span>
            </button>
          ))}
        </div>

        <div className="mt-6">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted">Invertir</span>
            <span className="font-semibold tabular-nums">{stake.toLocaleString("es-ES")} créditos</span>
          </div>
          <Slider
            className="mt-3"
            min={0}
            max={Math.max(availableBudget, STEP)}
            step={STEP}
            value={[stake]}
            onValueChange={([v]) => setStake(Math.min(v, availableBudget))}
          />
          <div className="mt-2 flex gap-2">
            {QUICK_FRACTIONS.map((fraction) => (
              <Button
                key={fraction}
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setStake(Math.round((availableBudget * fraction) / STEP) * STEP)}
              >
                {fraction === 1 ? "Máximo" : `${fraction * 100}%`}
              </Button>
            ))}
          </div>
        </div>

        <div className="mt-6 flex items-center justify-between rounded-xl bg-surface-raised px-4 py-3">
          <span className="text-sm text-muted">Ganancia potencial</span>
          <span className="text-lg font-bold text-success tabular-nums">
            +{potentialPayout.toLocaleString("es-ES")}
          </span>
        </div>

        {error && <p className="mt-3 text-sm text-danger">{error}</p>}

        <Button className="mt-4 w-full" size="lg" disabled={loading || stake <= 0 || !chosenOdds} onClick={handleConfirm}>
          {loading ? "Confirmando…" : "Confirmar predicción"}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
