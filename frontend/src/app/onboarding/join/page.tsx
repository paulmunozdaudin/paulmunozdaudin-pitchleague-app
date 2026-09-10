"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import type { League } from "@/types/api";

function JoinLeagueForm() {
  const api = useApi();
  const router = useRouter();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const league = await api.post<League>("/leagues/join", { invite_code: code });
      router.push(`/leagues/${league.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Código inválido.");
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-2xl font-bold">Únete a una liga</h1>
      <p className="mt-1 text-sm text-muted">Pide a tu amigo el código de invitación de su liga (ej. PL-7K2X).</p>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
        <Input
          autoFocus
          placeholder="PL-7K2X"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          className="text-center font-mono text-lg tracking-widest"
          maxLength={10}
          required
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" size="lg" variant="accent" disabled={loading || code.trim().length < 4}>
          {loading ? "Entrando…" : "Unirme"}
        </Button>
      </form>
    </main>
  );
}

export default function JoinLeaguePage() {
  return (
    <RequireAuth>
      <JoinLeagueForm />
    </RequireAuth>
  );
}
