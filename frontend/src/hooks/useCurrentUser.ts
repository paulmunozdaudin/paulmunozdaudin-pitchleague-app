"use client";

import { useEffect, useState } from "react";

import { useApi } from "@/hooks/useApi";
import type { User } from "@/types/api";

export function useCurrentUser(): { user: User | null; loading: boolean } {
  const api = useApi();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!api.ready) return;
    api
      .get<User>("/auth/me")
      .then(setUser)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.ready]);

  return { user, loading };
}
