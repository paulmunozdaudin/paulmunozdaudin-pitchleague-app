"use client";

import { AnimatePresence, motion } from "framer-motion";
import { RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { BetSlipMobileBar, BetSlipPanel } from "@/components/gameweek/BetSlipPanel";
import { BetSlipProvider } from "@/components/gameweek/BetSlipContext";
import { MatchCard } from "@/components/gameweek/MatchCard";
import { useLeague } from "@/components/league/LeagueContext";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { useLeagueRealtime } from "@/hooks/useLeagueRealtime";
import { ApiError } from "@/lib/api";
import type { Gameweek } from "@/types/api";

function useCountdown(target: string) {
  const [label, setLabel] = useState("");
  useEffect(() => {
    function tick() {
      const diff = new Date(target).getTime() - Date.now();
      if (diff <= 0) return setLabel("¡Bloqueada!");
      const hours = Math.floor(diff / 3_600_000);
      const minutes = Math.floor((diff % 3_600_000) / 60_000);
      setLabel(hours > 24 ? `${Math.floor(hours / 24)}d ${hours % 24}h` : `${hours}h ${minutes}m`);
    }
    tick();
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, [target]);
  return label;
}

export default function GameweekPage() {
  const { league } = useLeague();
  const api = useApi();
  const [gameweek, setGameweek] = useState<Gameweek | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.get<Gameweek>(`/leagues/${league.id}/gameweeks/current`);
      setGameweek(data);
      setNotFound(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setNotFound(true);
    }
  }, [api, league.id]);

  useEffect(() => {
    if (api.ready) load();
  }, [api.ready, load]);

  useLeagueRealtime(league.id, (event) => {
    if (event.type === "gameweek_settled") load();
  });

  const countdown = useCountdown(gameweek?.locks_at ?? new Date().toISOString());

  async function generateGameweek() {
    setGenerating(true);
    try {
      const data = await api.post<Gameweek>(`/leagues/${league.id}/gameweeks/generate-next`);
      setGameweek(data);
      setNotFound(false);
    } catch {
      // surfaced via disabled state / retry
    } finally {
      setGenerating(false);
    }
  }

  if (notFound) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6">
        <Sparkles className="mx-auto mb-4 h-8 w-8 text-primary" />
        <h2 className="text-xl font-semibold">No hay una jornada abierta</h2>
        <p className="mt-1 text-sm text-muted">
          {league.is_admin
            ? "Genera la próxima jornada para que todos podáis empezar a predecir."
            : "Espera a que el admin de la liga abra la próxima jornada."}
        </p>
        {league.is_admin && (
          <Button className="mt-6" onClick={generateGameweek} disabled={generating}>
            {generating ? "Generando…" : "Generar jornada"}
          </Button>
        )}
      </main>
    );
  }

  if (!gameweek) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  const balance = gameweek.my_wallet_balance ?? gameweek.budget;
  const starting = gameweek.my_wallet_starting ?? gameweek.budget;
  const progressPct = starting > 0 ? (balance / starting) * 100 : 0;

  return (
    <BetSlipProvider leagueId={league.id} gameweekId={gameweek.id} onPlaced={load}>
      <main className="mx-auto max-w-6xl px-4 py-8 pb-40 sm:px-6 lg:pb-8">
        <Card className="mb-6 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted">{gameweek.name}</p>
              <p className="text-2xl font-bold tabular-nums">{balance.toLocaleString("es-ES")} créditos</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted">Se bloquea en</p>
              <p className="font-semibold text-warning">{countdown}</p>
            </div>
          </div>
          <Progress value={Math.max(0, Math.min(100, progressPct))} className="mt-4" />
        </Card>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <AnimatePresence mode="popLayout">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {gameweek.matches.map((match, i) => (
                <motion.div
                  key={match.id}
                  layout
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <MatchCard leagueId={league.id} match={match} />
                </motion.div>
              ))}
            </div>
          </AnimatePresence>

          <div className="hidden lg:block">
            <div className="sticky top-6">
              <BetSlipPanel availableBudget={balance} />
            </div>
          </div>
        </div>

        {league.is_admin && (
          <div className="mt-6 flex justify-center">
            <Button variant="ghost" size="sm" onClick={load}>
              <RefreshCw className="h-3.5 w-3.5" /> Actualizar
            </Button>
          </div>
        )}

        <BetSlipMobileBar availableBudget={balance} />
      </main>
    </BetSlipProvider>
  );
}
