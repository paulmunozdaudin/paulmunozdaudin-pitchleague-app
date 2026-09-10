"use client";

import { useSession } from "next-auth/react";
import { useCallback, useMemo } from "react";

import { apiRequest } from "@/lib/api";

export function useApi() {
  const { data: session, status } = useSession();
  const token = session?.backendToken;

  const call = useCallback(
    <T,>(path: string, init?: RequestInit) => apiRequest<T>(path, token, init),
    [token]
  );

  return useMemo(
    () => ({
      ready: status === "authenticated" && !!token,
      loading: status === "loading",
      get: <T,>(path: string) => call<T>(path),
      post: <T,>(path: string, body?: unknown) =>
        call<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
      patch: <T,>(path: string, body?: unknown) =>
        call<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
      del: <T,>(path: string) => call<T>(path, { method: "DELETE" }),
    }),
    [call, status, token]
  );
}
