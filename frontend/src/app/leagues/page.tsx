"use client";

import { motion } from "framer-motion";
import { Plus, Users } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { TopNav } from "@/components/layout/TopNav";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import type { League } from "@/types/api";

function LeaguesHub() {
  const api = useApi();
  const [leagues, setLeagues] = useState<League[] | null>(null);

  useEffect(() => {
    if (!api.ready) return;
    api.get<League[]>("/leagues").then(setLeagues);
  }, [api.ready]);

  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Tus ligas</h1>
          <div className="flex gap-2">
            <Button asChild size="sm" variant="secondary">
              <Link href="/onboarding/join">Unirme</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/onboarding/create">
                <Plus className="h-4 w-4" /> Nueva liga
              </Link>
            </Button>
          </div>
        </div>

        {leagues === null && (
          <div className="mt-16 flex justify-center">
            <Spinner />
          </div>
        )}

        {leagues?.length === 0 && (
          <Card className="mt-8 flex flex-col items-center gap-3 p-10 text-center">
            <Users className="h-8 w-8 text-muted" />
            <p className="font-medium">Todavía no estás en ninguna liga</p>
            <p className="text-sm text-muted">Crea una liga o únete con el código de un amigo.</p>
          </Card>
        )}

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {leagues?.map((league, i) => (
            <motion.div
              key={league.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link href={`/leagues/${league.id}`}>
                <Card className="flex flex-col gap-3 p-5 transition-colors hover:border-primary/50">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold">{league.name}</p>
                    {league.is_admin && (
                      <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[11px] font-medium text-primary">
                        Admin
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-sm text-muted">
                    <span className="flex items-center gap-1.5">
                      <Users className="h-3.5 w-3.5" /> {league.member_count} jugadores
                    </span>
                    <span className="font-mono text-xs">{league.invite_code}</span>
                  </div>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      </main>
    </>
  );
}

export default function LeaguesPage() {
  return (
    <RequireAuth>
      <LeaguesHub />
    </RequireAuth>
  );
}
