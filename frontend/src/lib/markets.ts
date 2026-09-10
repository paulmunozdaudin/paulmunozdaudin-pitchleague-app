import type { Market, Selection } from "@/types/api";

export const MARKET_LABELS: Record<Market, string> = {
  winner: "Ganador",
  double_chance: "Doble oportunidad",
  over_under: "Over/Under",
  both_teams_to_score: "Ambos marcan",
};

export function selectionLabel(selection: Selection, homeTeam: string, awayTeam: string, line?: string | null): string {
  switch (selection) {
    case "home":
      return homeTeam;
    case "away":
      return awayTeam;
    case "draw":
      return "Empate";
    case "home_or_draw":
      return `${homeTeam} o empate`;
    case "away_or_draw":
      return `${awayTeam} o empate`;
    case "home_or_away":
      return "Gana alguno";
    case "over":
      return `Más de ${line ?? "2.5"}`;
    case "under":
      return `Menos de ${line ?? "2.5"}`;
    case "yes":
      return "Sí";
    case "no":
      return "No";
    default:
      return selection;
  }
}
