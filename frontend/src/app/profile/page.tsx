"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { TopNav } from "@/components/layout/TopNav";
import { PlayerAvatar } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { formatCredits } from "@/lib/utils";
import type { ProfileStats } from "@/types/api";

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4 text-center">
      <p className="text-xl font-bold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </Card>
  );
}

function ProfileContent() {
  const { data: session } = useSession();
  const api = useApi();
  const [stats, setStats] = useState<ProfileStats | null>(null);

  useEffect(() => {
    if (api.ready) api.get<ProfileStats>("/profile/me/stats").then(setStats);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready]);

  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <div className="flex items-center gap-4">
          <PlayerAvatar name={session?.user?.name ?? "?"} src={session?.user?.image} className="h-14 w-14 text-lg" />
          <div>
            <p className="text-xl font-bold">{session?.user?.name}</p>
            <p className="text-sm text-muted">{session?.user?.email}</p>
          </div>
        </div>

        {!stats && (
          <div className="mt-16 flex justify-center">
            <Spinner />
          </div>
        )}

        {stats && (
          <>
            <Card className="mt-6 p-5">
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold">Nivel {stats.level}</span>
                <span className="text-muted">{stats.xp} XP · {stats.xp_to_next_level} para subir</span>
              </div>
              <Progress
                className="mt-3"
                value={((500 - stats.xp_to_next_level) / 500) * 100}
              />
            </Card>

            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <StatTile label="Accuracy" value={`${stats.accuracy}%`} />
              <StatTile label="Best Week" value={formatCredits(stats.best_week_net)} />
              <StatTile label="Longest Streak" value={String(stats.longest_streak)} />
              <StatTile label="Mayor multiplicador" value={`${stats.highest_multiplier.toFixed(2)}x`} />
              <StatTile label="ROI virtual" value={`${stats.roi_percent}%`} />
              <StatTile label="Jornadas jugadas" value={String(stats.gameweeks_played)} />
            </div>

            <h2 className="mb-3 mt-8 font-semibold">Insignias</h2>
            {stats.badges.length === 0 && <p className="text-sm text-muted">Todavía no has desbloqueado ninguna. ¡Juega tu primera jornada!</p>}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {stats.badges.map((badge) => (
                <Card key={badge.code} className="flex flex-col items-center gap-1 p-4 text-center">
                  <span className="text-2xl">{badge.icon}</span>
                  <p className="text-xs font-semibold">{badge.name}</p>
                </Card>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfileContent />
    </RequireAuth>
  );
}
