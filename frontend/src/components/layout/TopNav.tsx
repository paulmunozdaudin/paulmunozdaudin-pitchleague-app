"use client";

import { Bell, LogOut, ShieldAlert } from "lucide-react";
import { signOut, useSession } from "next-auth/react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PlayerAvatar } from "@/components/ui/avatar";
import { useApi } from "@/hooks/useApi";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { NotificationItem } from "@/types/api";

export function TopNav() {
  const { data: session } = useSession();
  const api = useApi();
  const { user } = useCurrentUser();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!api.ready) return;
    api
      .get<NotificationItem[]>("/notifications")
      .then((items) => setUnread(items.filter((n) => !n.read_at).length))
      .catch(() => {});
  }, [api.ready]);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
        <Link href="/leagues" className="flex items-center gap-2 font-bold tracking-tight">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-sm text-white">
            P
          </span>
          PitchLeague
        </Link>

        <div className="flex items-center gap-3">
          {user?.is_staff && (
            <Link
              href="/admin/system"
              className="flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-surface-raised hover:text-foreground"
              title="Panel de sistema"
            >
              <ShieldAlert className="h-4.5 w-4.5" />
            </Link>
          )}
          <Link
            href="/notifications"
            className="relative flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-surface-raised hover:text-foreground"
          >
            <Bell className="h-4.5 w-4.5" />
            {unread > 0 && (
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger ring-2 ring-background" />
            )}
          </Link>

          <Link href="/profile" className="flex items-center gap-2">
            <PlayerAvatar name={session?.user?.name ?? "?"} src={session?.user?.image} className="h-8 w-8" />
          </Link>

          <button
            onClick={() => signOut({ callbackUrl: "/" })}
            className="flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-surface-raised hover:text-danger"
            title="Cerrar sesión"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
