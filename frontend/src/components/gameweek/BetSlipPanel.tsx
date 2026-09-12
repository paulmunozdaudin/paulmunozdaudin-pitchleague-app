"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Layers, Ticket, X } from "lucide-react";
import { useState } from "react";

import { useBetSlip } from "@/components/gameweek/BetSlipContext";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { selectionLabel } from "@/lib/markets";
import { cn, formatOdds } from "@/lib/utils";

const STEP = 100;

export function BetSlipPanel({ availableBudget }: { availableBudget: number }) {
  const { legs, removeLeg, clear, combinedOdds, oddsChanged, acceptOddsChange, placing, error, place } = useBetSlip();
  const [stake, setStake] = useState(1000);
  const [confirmedBet, setConfirmedBet] = useState<{ stake: number; combinedOdds: number } | null>(null);

  if (legs.length === 0 && !confirmedBet) {
    return (
      <Card className="flex flex-col items-center gap-2 p-6 text-center text-sm text-muted">
        <Ticket className="h-6 w-6" />
        Elige una cuota para empezar tu predicción.
      </Card>
    );
  }

  const potentialReturn = Math.round(stake * combinedOdds);
  const clampedStake = Math.min(stake, availableBudget);

  async function handleConfirm() {
    const bet = await place(clampedStake);
    if (bet) {
      setConfirmedBet({ stake: bet.stake, combinedOdds: Number(bet.combined_odds) });
      setTimeout(() => setConfirmedBet(null), 3000);
    }
  }

  return (
    <Card className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-1.5 text-sm font-semibold">
          {legs.length > 1 ? <Layers className="h-4 w-4" /> : <Ticket className="h-4 w-4" />}
          {legs.length > 1 ? "Tu combinación" : "Tu selección"}
        </p>
        {legs.length > 0 && (
          <button onClick={clear} className="text-xs text-muted hover:text-danger">
            Vaciar
          </button>
        )}
      </div>

      <AnimatePresence>
        {confirmedBet && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="rounded-xl bg-success/15 p-3 text-center text-sm text-success"
          >
            ¡Predicción confirmada! {confirmedBet.stake.toLocaleString("es-ES")} cr a cuota{" "}
            {confirmedBet.combinedOdds.toFixed(2)}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col gap-2">
        {legs.map((leg) => (
          <div key={leg.match.id} className="flex items-center justify-between rounded-lg bg-surface-raised px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-xs text-muted">
                {leg.match.home_team} vs {leg.match.away_team}
              </p>
              <p className="text-sm font-medium">
                {selectionLabel(leg.selection, leg.match.home_team, leg.match.away_team, leg.line)}{" "}
                <span className="tabular-nums text-primary">{formatOdds(leg.price)}</span>
              </p>
            </div>
            <button onClick={() => removeLeg(leg.match.id)} className="shrink-0 p-1 text-muted hover:text-danger">
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      {legs.length > 1 && (
        <div className="flex items-center justify-between rounded-lg bg-primary/10 px-3 py-2 text-sm">
          <span className="text-muted">Cuota combinada</span>
          <span className="font-bold text-primary tabular-nums">{combinedOdds.toFixed(2)}</span>
        </div>
      )}

      {oddsChanged && (
        <div className="rounded-lg bg-warning/15 p-3 text-xs text-warning">
          Una cuota ha cambiado.{" "}
          <button onClick={acceptOddsChange} className="font-semibold underline">
            Aceptar nueva cuota
          </button>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between text-xs text-muted">
          <span>Invertir (máx. {availableBudget.toLocaleString("es-ES")})</span>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <Button type="button" size="sm" variant="outline" onClick={() => setStake((s) => Math.max(STEP, s - STEP))}>
            -
          </Button>
          <input
            type="number"
            value={clampedStake}
            onChange={(e) => setStake(Math.max(0, Number(e.target.value)))}
            className="h-9 w-full rounded-lg border border-border bg-surface px-3 text-center text-sm tabular-nums"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setStake((s) => Math.min(availableBudget, s + STEP))}
          >
            +
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-xl bg-surface-raised px-3 py-2">
        <span className="text-sm text-muted">Retorno posible</span>
        <span className="text-lg font-bold text-success tabular-nums">
          {potentialReturn.toLocaleString("es-ES")} 🪙
        </span>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <Button
        size="lg"
        disabled={placing || clampedStake <= 0 || legs.length === 0 || !!oddsChanged}
        onClick={handleConfirm}
      >
        {placing ? "Confirmando…" : "Confirmar"}
      </Button>
    </Card>
  );
}

export function BetSlipMobileBar({ availableBudget }: { availableBudget: number }) {
  const { legs, combinedOdds } = useBetSlip();
  const [open, setOpen] = useState(false);

  if (legs.length === 0) return null;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={cn(
          "fixed inset-x-4 bottom-4 z-30 flex items-center justify-between rounded-2xl bg-primary px-5 py-4 text-primary-foreground shadow-2xl lg:hidden"
        )}
      >
        <span className="flex items-center gap-2 font-semibold">
          <Ticket className="h-4 w-4" /> {legs.length} {legs.length === 1 ? "selección" : "selecciones"}
        </span>
        <span className="tabular-nums">Cuota {combinedOdds.toFixed(2)}</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 lg:hidden"
            onClick={() => setOpen(false)}
          >
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30 }}
              className="absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-3xl bg-background p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border" />
              <BetSlipPanel availableBudget={availableBudget} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
