"use client";

import confetti from "canvas-confetti";
import { motion } from "framer-motion";
import { use, useEffect, useState } from "react";

import { useLeague } from "@/components/league/LeagueContext";
import { ShareCard } from "@/components/results/ShareCard";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { formatCredits } from "@/lib/utils";
import type { GameweekResultSummary } from "@/types/api";

const BADGE_ICON: Record<string, string> = {
  first_place: "🏆",
  hat_trick: "🎩",
  comeback: "📈",
  giant_killer: "🗡️",
  perfect_week: "💯",
  underdog: "🐺",
  invencible: "🛡️",
  sniper: "🎯",
};

const BADGE_NAME: Record<string, string> = {
  first_place: "Primer Puesto",
  hat_trick: "Hat Trick",
  comeback: "Comeback",
  giant_killer: "Giant Killer",
  perfect_week: "Perfect Week",
  underdog: "Underdog",
  invencible: "Invencible",
  sniper: "Sniper",
};

export default function ResultsPage({ params }: { params: Promise<{ gameweekId: string }> }) {
  const { gameweekId } = use(params);
  const { league } = useLeague();
  const api = useApi();
  const [summary, setSummary] = useState<GameweekResultSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!api.ready) return;
    api
      .get<GameweekResultSummary>(`/leagues/${league.id}/rankings/${gameweekId}/result-summary`)
      .then(setSummary)
      .catch(() => setError("Esta jornada todavía no se ha liquidado."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready, league.id, gameweekId]);

  useEffect(() => {
    if (summary?.position === 1) {
      confetti({ particleCount: 140, spread: 80, origin: { y: 0.4 } });
    }
  }, [summary?.position]);

  if (error) {
    return <p className="mx-auto max-w-md px-4 py-16 text-center text-sm text-muted">{error}</p>;
  }
  if (!summary) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  const positionsGained = summary.positions_gained;

  return (
    <main className="mx-auto flex max-w-md flex-col items-center px-4 py-12 text-center sm:px-6">
      <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: "spring" }}>
        <p className="text-6xl">{summary.position === 1 ? "🏆" : summary.position <= 3 ? "🎉" : "📊"}</p>
      </motion.div>

      <motion.p
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.15 }}
        className={`mt-4 text-4xl font-extrabold tabular-nums ${summary.net_change >= 0 ? "text-success" : "text-danger"}`}
      >
        {formatCredits(summary.net_change)}
      </motion.p>

      {positionsGained !== 0 && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-2 text-muted">
          {positionsGained > 0 ? (
            <>
              Subes del puesto {summary.previous_position} al <span className="font-semibold text-foreground">{summary.position}</span>
            </>
          ) : (
            <>
              Bajas del puesto {summary.previous_position} al <span className="font-semibold text-foreground">{summary.position}</span>
            </>
          )}
        </motion.p>
      )}

      {summary.current_streak >= 2 && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="mt-1 text-warning">
          🔥 Racha de {summary.current_streak} jornadas en el Top 3
        </motion.p>
      )}

      {summary.rival_overtaken && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="mt-1 text-sm text-muted">
          {summary.rival_overtaken} perdió el liderato.
        </motion.p>
      )}

      <p className="mt-4 text-sm text-muted">
        Acertaste {summary.correct_picks} de {summary.total_picks} predicciones
      </p>

      {summary.new_badges.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-4 flex flex-wrap justify-center gap-2"
        >
          {summary.new_badges.map((code) => (
            <Badge key={code} variant="accent">
              {BADGE_ICON[code] ?? "🏅"} {BADGE_NAME[code] ?? code}
            </Badge>
          ))}
        </motion.div>
      )}

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="mt-10">
        <ShareCard
          playerName="Tú"
          leagueName={league.name}
          position={summary.position}
          netChange={summary.net_change}
          gameweekLabel="Esta jornada"
        />
      </motion.div>
    </main>
  );
}
