"use client";

import { Copy, RefreshCw, RotateCcw, UserMinus } from "lucide-react";
import { useEffect, useState } from "react";

import { useLeague } from "@/components/league/LeagueContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PlayerAvatar } from "@/components/ui/avatar";
import { useApi } from "@/hooks/useApi";
import { ApiError } from "@/lib/api";
import type { Gameweek } from "@/types/api";

function InviteShare({ code }: { code: string }) {
  const message = encodeURIComponent(`Únete a mi liga en PitchLeague con el código ${code} 🏆`);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="rounded-lg bg-surface-raised px-3 py-2 font-mono text-lg tracking-widest">{code}</span>
      <Button size="sm" variant="secondary" onClick={() => navigator.clipboard.writeText(code)}>
        <Copy className="h-3.5 w-3.5" /> Copiar
      </Button>
      <Button asChild size="sm" variant="secondary">
        <a href={`https://wa.me/?text=${message}`} target="_blank" rel="noreferrer">
          WhatsApp
        </a>
      </Button>
      <Button asChild size="sm" variant="secondary">
        <a href={`https://t.me/share/url?url=&text=${message}`} target="_blank" rel="noreferrer">
          Telegram
        </a>
      </Button>
    </div>
  );
}

export default function AdminPage() {
  const { league, refresh } = useLeague();
  const api = useApi();
  const [name, setName] = useState(league.name);
  const [budget, setBudget] = useState(league.budget_per_gameweek);
  const [saving, setSaving] = useState(false);
  const [gameweek, setGameweek] = useState<Gameweek | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!api.ready) return;
    api
      .get<Gameweek>(`/leagues/${league.id}/gameweeks/current`)
      .then(setGameweek)
      .catch(() => setGameweek(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready, league.id]);

  async function saveSettings() {
    setSaving(true);
    try {
      await api.patch(`/leagues/${league.id}`, { name, budget_per_gameweek: budget });
      await refresh();
      setMessage("Cambios guardados.");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  async function kick(userId: string) {
    if (!confirm("¿Expulsar a este jugador de la liga?")) return;
    await api.del(`/leagues/${league.id}/members/${userId}`);
    await refresh();
  }

  async function resetSeason() {
    if (!confirm("Esto archiva la temporada actual y empieza una nueva desde cero. ¿Continuar?")) return;
    await api.post(`/leagues/${league.id}/reset-season`);
    setMessage("Nueva temporada iniciada.");
  }

  async function refreshOdds() {
    if (!gameweek) return;
    await api.post(`/leagues/${league.id}/gameweeks/${gameweek.id}/refresh-odds`);
    setMessage("Cuotas actualizadas.");
  }

  async function settle() {
    if (!gameweek) return;
    const result = await api.post<{ settled: boolean }>(`/leagues/${league.id}/gameweeks/${gameweek.id}/settle`);
    setMessage(result.settled ? "Jornada liquidada." : "Todavía hay partidos sin terminar — inténtalo más tarde.");
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <h1 className="mb-6 text-2xl font-bold">Panel de administración</h1>

      <Card>
        <CardHeader>
          <CardTitle>Invitar amigos</CardTitle>
        </CardHeader>
        <CardContent>
          <InviteShare code={league.invite_code} />
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Ajustes de la liga</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted">Nombre</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted">Presupuesto por jornada</label>
            <Input type="number" min={100} step={100} value={budget} onChange={(e) => setBudget(Number(e.target.value))} />
          </div>
          <Button onClick={saveSettings} disabled={saving} className="self-start">
            {saving ? "Guardando…" : "Guardar cambios"}
          </Button>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Jornada actual</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={refreshOdds} disabled={!gameweek}>
            <RefreshCw className="h-3.5 w-3.5" /> Actualizar cuotas
          </Button>
          <Button size="sm" variant="secondary" onClick={settle} disabled={!gameweek}>
            Liquidar jornada
          </Button>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Jugadores</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {league.members.map((member) => (
            <div key={member.user.id} className="flex items-center justify-between rounded-lg px-1 py-1.5">
              <div className="flex items-center gap-2">
                <PlayerAvatar name={member.user.name} src={member.user.avatar_url} className="h-7 w-7" />
                <span className="text-sm">{member.user.name}</span>
                {member.role === "admin" && <span className="text-xs text-muted">(admin)</span>}
              </div>
              {member.role !== "admin" && (
                <Button size="sm" variant="ghost" onClick={() => kick(member.user.id)}>
                  <UserMinus className="h-3.5 w-3.5 text-danger" />
                </Button>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="mt-4 border-danger/30">
        <CardHeader>
          <CardTitle className="text-danger">Zona de riesgo</CardTitle>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" size="sm" onClick={resetSeason}>
            <RotateCcw className="h-3.5 w-3.5" /> Reiniciar temporada
          </Button>
        </CardContent>
      </Card>

      {message && <p className="mt-4 text-center text-sm text-muted">{message}</p>}
    </main>
  );
}
