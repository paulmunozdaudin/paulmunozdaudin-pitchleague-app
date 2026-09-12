"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { useApi } from "@/hooks/useApi";
import { ApiError } from "@/lib/api";
import type { Bet, Market, Match, Selection } from "@/types/api";

export interface SlipLeg {
  match: Match;
  market: Market;
  selection: Selection;
  line: string | null;
  price: string;
}

interface OddsChangedInfo {
  matchId: string;
  expectedPrice: string;
  currentPrice: string;
}

interface BetSlipContextValue {
  legs: SlipLeg[];
  addOrReplaceLeg: (leg: SlipLeg) => void;
  removeLeg: (matchId: string) => void;
  clear: () => void;
  combinedOdds: number;
  oddsChanged: OddsChangedInfo | null;
  acceptOddsChange: () => void;
  placing: boolean;
  error: string | null;
  place: (stake: number) => Promise<Bet | null>;
}

const BetSlipContext = createContext<BetSlipContextValue | null>(null);

export function useBetSlip(): BetSlipContextValue {
  const ctx = useContext(BetSlipContext);
  if (!ctx) throw new Error("useBetSlip must be used within BetSlipProvider");
  return ctx;
}

export function BetSlipProvider({
  leagueId,
  gameweekId,
  onPlaced,
  children,
}: {
  leagueId: string;
  gameweekId: string;
  onPlaced: () => void;
  children: ReactNode;
}) {
  const api = useApi();
  const [legs, setLegs] = useState<SlipLeg[]>([]);
  const [oddsChanged, setOddsChanged] = useState<OddsChangedInfo | null>(null);
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addOrReplaceLeg = useCallback((leg: SlipLeg) => {
    setLegs((prev) => [...prev.filter((l) => l.match.id !== leg.match.id), leg]);
    setError(null);
  }, []);

  const removeLeg = useCallback((matchId: string) => {
    setLegs((prev) => prev.filter((l) => l.match.id !== matchId));
  }, []);

  const clear = useCallback(() => {
    setLegs([]);
    setOddsChanged(null);
    setError(null);
  }, []);

  const combinedOdds = useMemo(() => legs.reduce((acc, l) => acc * Number(l.price), 1), [legs]);

  const acceptOddsChange = useCallback(() => {
    if (!oddsChanged) return;
    setLegs((prev) =>
      prev.map((l) => (l.match.id === oddsChanged.matchId ? { ...l, price: oddsChanged.currentPrice } : l))
    );
    setOddsChanged(null);
  }, [oddsChanged]);

  const place = useCallback(
    async (stake: number): Promise<Bet | null> => {
      setPlacing(true);
      setError(null);
      try {
        const bet = await api.post<Bet>(`/leagues/${leagueId}/gameweeks/${gameweekId}/bets`, {
          stake,
          legs: legs.map((l) => ({
            match_id: l.match.id,
            market: l.market,
            selection: l.selection,
            line: l.line,
            expected_price: l.price,
          })),
        });
        clear();
        onPlaced();
        return bet;
      } catch (err) {
        if (err instanceof ApiError && err.status === 409 && err.detail && typeof err.detail === "object") {
          const detail = err.detail as { match_id: string; expected_price: string; current_price: string };
          setOddsChanged({ matchId: detail.match_id, expectedPrice: detail.expected_price, currentPrice: detail.current_price });
          setError(err.message);
        } else {
          setError(err instanceof ApiError ? err.message : "No se pudo confirmar la predicción.");
        }
        return null;
      } finally {
        setPlacing(false);
      }
    },
    [api, leagueId, gameweekId, legs, clear, onPlaced]
  );

  return (
    <BetSlipContext.Provider
      value={{ legs, addOrReplaceLeg, removeLeg, clear, combinedOdds, oddsChanged, acceptOddsChange, placing, error, place }}
    >
      {children}
    </BetSlipContext.Provider>
  );
}
