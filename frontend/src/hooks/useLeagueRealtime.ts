"use client";

import { useSession } from "next-auth/react";
import { useEffect, useRef } from "react";

type RealtimeEvent = { type: string; [key: string]: unknown };

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^http/, "ws");

export function useLeagueRealtime(leagueId: string | undefined, onEvent: (event: RealtimeEvent) => void) {
  const { data: session } = useSession();
  const token = session?.backendToken;
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!leagueId || !token) return;

    const socket = new WebSocket(`${WS_BASE}/ws/leagues/${leagueId}?token=${encodeURIComponent(token)}`);
    socket.onmessage = (event) => {
      try {
        handlerRef.current(JSON.parse(event.data));
      } catch {
        // ignore malformed frames
      }
    };

    return () => socket.close();
  }, [leagueId, token]);
}
