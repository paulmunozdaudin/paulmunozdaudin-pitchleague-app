"use client";

import { Bell, Bot, Goal, Home, LogOut, Settings, Trophy, User } from "lucide-react";
import { signOut } from "next-auth/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useApi } from "@/hooks/useApi";
import { cn } from "@/lib/utils";
import type { NotificationItem } from "@/types/api";
import { useLeague } from "./LeagueContext";

function useNavItems() {
  const { league } = useLeague();
  const base = `/leagues/${league.id}`;
  return [
    { href: base, label: "Liga", icon: Home, exact: true },
    { href: `${base}/gameweek`, label: "Partidos", icon: Goal },
    { href: `${base}/ia`, label: "IA", icon: Bot },
    { href: `${base}/ranking`, label: "Ranking", icon: Trophy },
    { href: "/profile", label: "Perfil", icon: User },
  ];
}

function isActive(pathname: string, href: string, exact?: boolean) {
  return exact ? pathname === href : pathname.startsWith(href);
}

export function LeagueBottomNav() {
  const items = useNavItems();
  const pathname = usePathname();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur-md lg:hidden">
      <div className="mx-auto flex h-16 max-w-6xl items-stretch justify-around px-2">
        {items.map((item) => {
          const active = isActive(pathname, item.href, item.exact);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors",
                active ? "text-primary" : "text-muted"
              )}
            >
              <Icon className={cn("h-5 w-5", active && "fill-primary/15")} />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function LeagueSidebar() {
  const { league } = useLeague();
  const items = useNavItems();
  const pathname = usePathname();
  const api = useApi();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!api.ready) return;
    api
      .get<NotificationItem[]>("/notifications")
      .then((list) => setUnread(list.filter((n) => !n.read_at).length))
      .catch(() => {});
  }, [api.ready]);

  return (
    <aside className="hidden lg:flex lg:w-60 lg:shrink-0 lg:flex-col lg:border-r lg:border-border lg:bg-surface/40 lg:px-3 lg:py-6">
      <Link href="/leagues" className="mb-6 flex items-center gap-2 px-2 font-bold tracking-tight">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-sm text-white">
          P
        </span>
        PitchLeague
      </Link>

      <div className="mb-4 flex items-center gap-2 rounded-xl bg-surface-raised px-3 py-2.5">
        <span className="text-xl">{league.avatar_emoji}</span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{league.name}</p>
          <p className="text-xs text-muted">{league.member_count} jugadores</p>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-1">
        {items.map((item) => {
          const active = isActive(pathname, item.href, item.exact);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "bg-primary/10 text-primary" : "text-muted hover:bg-surface-raised hover:text-foreground"
              )}
            >
              <Icon className="h-4.5 w-4.5" />
              {item.label}
            </Link>
          );
        })}
        <Link
          href="/notifications"
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
            pathname === "/notifications"
              ? "bg-primary/10 text-primary"
              : "text-muted hover:bg-surface-raised hover:text-foreground"
          )}
        >
          <span className="relative">
            <Bell className="h-4.5 w-4.5" />
            {unread > 0 && <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-danger" />}
          </span>
          Notificaciones
        </Link>
        {league.is_admin && (
          <Link
            href={`/leagues/${league.id}/admin`}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              pathname.startsWith(`/leagues/${league.id}/admin`)
                ? "bg-primary/10 text-primary"
                : "text-muted hover:bg-surface-raised hover:text-foreground"
            )}
          >
            <Settings className="h-4.5 w-4.5" />
            Admin
          </Link>
        )}
      </div>

      <button
        onClick={() => signOut({ callbackUrl: "/" })}
        className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted hover:bg-surface-raised hover:text-danger"
      >
        <LogOut className="h-4.5 w-4.5" />
        Cerrar sesión
      </button>
    </aside>
  );
}
