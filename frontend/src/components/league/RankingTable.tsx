"use client";

import { motion } from "framer-motion";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

import { PlayerAvatar } from "@/components/ui/avatar";
import { cn, formatCredits } from "@/lib/utils";
import type { RankingRow } from "@/types/api";

const MEDALS = ["🥇", "🥈", "🥉"];

export function RankingTable({ rows, youUserId }: { rows: RankingRow[]; youUserId?: string }) {
  return (
    <div className="flex flex-col gap-2">
      {rows.map((row, i) => {
        const isYou = row.user.id === youUserId;
        const movement = row.previous_position ? row.previous_position - row.position : 0;

        return (
          <motion.div
            key={row.user.id}
            layout
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03 }}
            className={cn(
              "flex items-center gap-3 rounded-xl border px-4 py-3",
              isYou ? "border-primary bg-primary/10" : "border-border bg-surface/60"
            )}
          >
            <span className="w-7 shrink-0 text-center text-lg">
              {row.position <= 3 ? MEDALS[row.position - 1] : <span className="text-sm text-muted">{row.position}</span>}
            </span>

            <PlayerAvatar name={row.user.name} src={row.user.avatar_url} className="h-8 w-8" />

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{row.user.name}</p>
              {row.streak > 0 && <p className="text-xs text-warning">🔥 {row.streak} semanas seguidas Top 3</p>}
            </div>

            <div className="text-right">
              <p className="tabular-nums font-bold">{row.balance.toLocaleString("es-ES")}</p>
              <p
                className={cn(
                  "text-xs tabular-nums",
                  row.net_change > 0 ? "text-success" : row.net_change < 0 ? "text-danger" : "text-muted"
                )}
              >
                {formatCredits(row.net_change)}
              </p>
            </div>

            {movement !== 0 && (
              <span className={cn("flex items-center text-xs font-semibold", movement > 0 ? "text-success" : "text-danger")}>
                {movement > 0 ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
                {Math.abs(movement)}
              </span>
            )}
            {movement === 0 && row.previous_position && <Minus className="h-3.5 w-3.5 text-muted" />}
          </motion.div>
        );
      })}
    </div>
  );
}
