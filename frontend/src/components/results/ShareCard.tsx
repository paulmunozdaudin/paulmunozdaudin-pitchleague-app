"use client";

import { Share2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatCredits } from "@/lib/utils";

export function ShareCard({
  playerName,
  leagueName,
  position,
  netChange,
  gameweekLabel,
}: {
  playerName: string;
  leagueName: string;
  position: number;
  netChange: number;
  gameweekLabel: string;
}) {
  const medal = position === 1 ? "🏆" : position === 2 ? "🥈" : position === 3 ? "🥉" : "📊";
  const shareText = `${playerName}\n${medal} ${position}.º en ${leagueName}\n${formatCredits(netChange)} créditos · ${gameweekLabel}\n\nJuega en PitchLeague 👉`;

  async function share() {
    if (navigator.share) {
      try {
        await navigator.share({ text: shareText });
        return;
      } catch {
        // user cancelled — fall through to clipboard
      }
    }
    await navigator.clipboard.writeText(shareText);
  }

  return (
    <div className="w-full max-w-sm overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-primary/20 via-surface to-accent/10 p-6 text-center">
      <p className="text-sm font-medium text-muted">{leagueName}</p>
      <p className="mt-3 text-2xl font-bold">{playerName}</p>
      <p className="mt-1 text-4xl">{medal}</p>
      <p className="mt-1 text-lg font-semibold">{position}.º puesto</p>
      <p className={`mt-1 text-xl font-bold ${netChange >= 0 ? "text-success" : "text-danger"}`}>
        {formatCredits(netChange)}
      </p>
      <p className="mt-1 text-xs text-muted">{gameweekLabel}</p>

      <Button className="mt-5 w-full" variant="accent" onClick={share}>
        <Share2 className="h-4 w-4" /> Compartir resultado
      </Button>
    </div>
  );
}
