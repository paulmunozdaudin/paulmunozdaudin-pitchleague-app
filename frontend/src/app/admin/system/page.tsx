"use client";

import { AlertTriangle, Bot, ShieldAlert, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { TopNav } from "@/components/layout/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { FailedJob, OddsHealthRow, SystemModelVersion, SystemOverview } from "@/types/api";

function timeAgo(iso: string | null): string {
  if (!iso) return "nunca";
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums">{value}</p>
    </Card>
  );
}

function SystemAdminDashboard() {
  const api = useApi();
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [models, setModels] = useState<SystemModelVersion[] | null>(null);
  const [oddsHealth, setOddsHealth] = useState<OddsHealthRow[] | null>(null);
  const [failedJobs, setFailedJobs] = useState<FailedJob[] | null>(null);

  useEffect(() => {
    if (!api.ready) return;
    api.get<SystemOverview>("/admin/system/overview").then(setOverview);
    api.get<SystemModelVersion[]>("/admin/system/model-versions").then(setModels);
    api.get<OddsHealthRow[]>("/admin/system/odds-health").then(setOddsHealth);
    api.get<FailedJob[]>("/admin/system/failed-jobs").then(setFailedJobs);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready]);

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-primary" />
        <h1 className="text-xl font-bold">Panel de sistema</h1>
      </div>

      {!overview && (
        <div className="flex justify-center py-10">
          <Spinner className="h-6 w-6" />
        </div>
      )}

      {overview && (
        <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Usuarios" value={overview.users_count} />
          <StatCard label="Ligas" value={overview.leagues_count} />
          <StatCard label="Partidos" value={overview.matches_count} />
          <StatCard label="Jornadas abiertas" value={overview.open_gameweeks_count} />
        </div>
      )}

      {overview && (
        <Card className="mb-8 p-4 text-sm text-muted">
          Proveedor de cuotas: <span className="font-semibold text-foreground">{overview.odds_provider}</span> ·
          Proveedor de IA: <span className="font-semibold text-foreground">{overview.ai_insights_provider}</span>
        </Card>
      )}

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="h-4 w-4" /> Versiones del Model Engine
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {models?.length === 0 && <p className="text-sm text-muted">Todavía no se ha entrenado ningún modelo.</p>}
          {models?.map((m) => {
            // metrics is keyed by every model that was backtested for this
            // division (elo, poisson, ..., market) — model_name says which
            // one was actually shipped, so its own metrics live there.
            const ownMetrics = m.metrics[m.model_name] as { log_loss?: number } | undefined;
            const marketMetrics = m.metrics.market as { log_loss?: number } | undefined;
            return (
              <div key={m.id} className="flex items-center justify-between rounded-lg bg-surface-raised px-3 py-2 text-sm">
                <div>
                  <span className="font-semibold">{m.division}</span> · {m.model_name}
                  {m.is_active && <span className="ml-2 rounded-full bg-success/15 px-2 py-0.5 text-xs text-success">activo</span>}
                </div>
                <span className="text-xs text-muted tabular-nums">
                  log loss {ownMetrics?.log_loss?.toFixed(4) ?? "—"}
                  {marketMetrics?.log_loss !== undefined && (
                    <span> · mercado {marketMetrics.log_loss.toFixed(4)}</span>
                  )}
                </span>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Salud de las cuotas</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {oddsHealth?.length === 0 && <p className="text-sm text-muted">No hay jornadas abiertas ahora mismo.</p>}
          {oddsHealth?.map((row) => (
            <div
              key={row.competition}
              className="flex items-center justify-between rounded-lg bg-surface-raised px-3 py-2 text-sm"
            >
              <span className="font-semibold">{row.competition}</span>
              <span className="text-xs text-muted">
                {row.matches_open} partidos · última actualización {timeAgo(row.last_fetched_at)}
                {row.stale_matches > 0 && (
                  <span className="ml-2 text-warning">· {row.stale_matches} sin refrescar</span>
                )}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangle className="h-4 w-4" /> Jobs fallidos recientes
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {failedJobs?.length === 0 && <p className="text-sm text-muted">Ningún job ha fallado. 🎉</p>}
          {failedJobs?.map((job) => (
            <div key={job.id} className="rounded-lg bg-danger/10 px-3 py-2 text-sm">
              <p className="font-semibold text-danger">
                {job.job_name}
                {job.reference && <span className="font-normal text-muted"> · {job.reference}</span>}
              </p>
              <p className="mt-0.5 text-xs text-muted">{job.error_message}</p>
              <p className="mt-0.5 text-xs text-muted">{timeAgo(job.occurred_at)}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </main>
  );
}

function SystemAdminGate() {
  const { user, loading } = useCurrentUser();

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (!user?.is_staff) {
    return (
      <main className="mx-auto max-w-md px-4 py-16 text-center sm:px-6">
        <Users className="mx-auto mb-4 h-8 w-8 text-muted" />
        <h1 className="text-lg font-semibold">Acceso restringido</h1>
        <p className="mt-1 text-sm text-muted">Este panel es solo para el equipo de PitchLeague.</p>
      </main>
    );
  }

  return <SystemAdminDashboard />;
}

export default function SystemAdminPage() {
  return (
    <RequireAuth>
      <TopNav />
      <SystemAdminGate />
    </RequireAuth>
  );
}
