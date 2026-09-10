"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import type { League } from "@/types/api";

function CreateLeagueForm() {
  const api = useApi();
  const router = useRouter();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const league = await api.post<League>("/leagues", { name });
      router.push(`/leagues/${league.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Algo salió mal. Inténtalo de nuevo.");
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-2xl font-bold">Crea tu liga</h1>
      <p className="mt-1 text-sm text-muted">
        Ponle un nombre. Podrás invitar a tus amigos con un código nada más crearla.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
        <Input
          autoFocus
          placeholder="Los Desgraciados"
          value={name}
          onChange={(e) => setName(e.target.value)}
          minLength={2}
          maxLength={80}
          required
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" size="lg" disabled={loading || name.trim().length < 2}>
          {loading ? "Creando…" : "Crear liga"}
        </Button>
      </form>
    </main>
  );
}

export default function CreateLeaguePage() {
  return (
    <RequireAuth>
      <CreateLeagueForm />
    </RequireAuth>
  );
}
