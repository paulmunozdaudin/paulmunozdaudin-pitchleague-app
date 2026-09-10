"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { TopNav } from "@/components/layout/TopNav";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useApi } from "@/hooks/useApi";
import { cn } from "@/lib/utils";
import type { NotificationItem } from "@/types/api";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

function NotificationRow({ notification, onOpen }: { notification: NotificationItem; onOpen: () => void }) {
  const leagueId = (notification.data?.league_id as string | undefined) ?? undefined;
  const gameweekId = (notification.data?.gameweek_id as string | undefined) ?? undefined;
  const href = leagueId && gameweekId ? `/leagues/${leagueId}/results/${gameweekId}` : undefined;

  const content = (
    <Card
      onClick={onOpen}
      className={cn("flex items-start gap-3 p-4", !notification.read_at && "border-primary/40 bg-primary/5")}
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{notification.title}</p>
        <p className="text-sm text-muted">{notification.body}</p>
        <p className="mt-1 text-xs text-muted">{timeAgo(notification.created_at)}</p>
      </div>
      {!notification.read_at && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />}
    </Card>
  );

  return href ? <Link href={href}>{content}</Link> : content;
}

function NotificationsList() {
  const api = useApi();
  const [items, setItems] = useState<NotificationItem[] | null>(null);

  useEffect(() => {
    if (api.ready) api.get<NotificationItem[]>("/notifications").then(setItems);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready]);

  async function markRead(id: string) {
    setItems((prev) => prev?.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)) ?? null);
    api.post(`/notifications/${id}/read`).catch(() => {});
  }

  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <h1 className="mb-6 text-2xl font-bold">Notificaciones</h1>
        {items === null && (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        )}
        {items?.length === 0 && <p className="text-sm text-muted">No tienes notificaciones todavía.</p>}
        <div className="flex flex-col gap-2">
          {items?.map((n) => (
            <NotificationRow key={n.id} notification={n} onOpen={() => markRead(n.id)} />
          ))}
        </div>
      </main>
    </>
  );
}

export default function NotificationsPage() {
  return (
    <RequireAuth>
      <NotificationsList />
    </RequireAuth>
  );
}
