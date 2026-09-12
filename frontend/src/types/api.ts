export type Market = "winner" | "double_chance" | "over_under" | "both_teams_to_score";
export type Selection =
  | "home"
  | "draw"
  | "away"
  | "home_or_draw"
  | "away_or_draw"
  | "home_or_away"
  | "over"
  | "under"
  | "yes"
  | "no";
export type MatchStatus = "scheduled" | "live" | "finished" | "postponed";
export type MatchOutcome = "home" | "draw" | "away";
export type GameweekStatus = "upcoming" | "open" | "locked" | "settled";
export type BetStatus = "pending" | "won" | "lost" | "void";

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
}

export interface League {
  id: string;
  name: string;
  avatar_emoji: string;
  invite_code: string;
  admin_user_id: string;
  budget_per_gameweek: number;
  max_players: number;
  member_count: number;
  is_admin: boolean;
}

export interface LeagueMember {
  user: User;
  role: "admin" | "member";
  joined_at: string | null;
}

export interface LeagueDetail extends League {
  members: LeagueMember[];
}

export interface Odds {
  market: Market;
  selection: Selection;
  line: string | null;
  price: string;
  fetched_at: string;
}

export interface MatchLegSummary {
  bet_id: string;
  market: Market;
  selection: Selection;
  line: string | null;
  odds_price_at_pick: string;
  status: BetStatus;
}

export interface BetLeg {
  id: string;
  match_id: string;
  market: Market;
  selection: Selection;
  line: string | null;
  odds_price_at_pick: string;
  status: BetStatus;
}

export interface Bet {
  id: string;
  stake: number;
  combined_odds: string;
  potential_payout: number;
  status: BetStatus;
  payout: number | null;
  created_at: string;
  legs: BetLeg[];
}

export interface Match {
  id: string;
  competition: string;
  home_team: string;
  away_team: string;
  kickoff_at: string;
  status: MatchStatus;
  home_score: number | null;
  away_score: number | null;
  result: MatchOutcome | null;
  odds: Odds[];
  is_locked: boolean;
  my_legs: MatchLegSummary[];
}

export interface Gameweek {
  id: string;
  number: number;
  name: string;
  opens_at: string;
  locks_at: string;
  budget: number;
  status: GameweekStatus;
  matches: Match[];
  my_wallet_balance: number | null;
  my_wallet_starting: number | null;
}

export interface RankingRow {
  position: number;
  previous_position: number | null;
  user: User;
  balance: number;
  net_change: number;
  streak: number;
  is_you: boolean;
}

export interface GameweekResultSummary {
  gameweek_id: string;
  net_change: number;
  position: number;
  previous_position: number | null;
  positions_gained: number;
  correct_picks: number;
  total_picks: number;
  current_streak: number;
  new_badges: string[];
  rival_overtaken: string | null;
}

export interface Badge {
  code: string;
  name: string;
  description: string;
  icon: string;
  earned_at: string | null;
}

export interface ProfileStats {
  gameweeks_played: number;
  accuracy: number;
  best_week_net: number;
  longest_streak: number;
  highest_multiplier: number;
  roi_percent: number;
  xp: number;
  level: number;
  xp_to_next_level: number;
  badges: Badge[];
}

export type ActivityType = "bet_placed" | "streak_milestone" | "badge_earned" | "gameweek_settled";

export interface LeagueActivity {
  id: string;
  user: User;
  type: ActivityType;
  data: Record<string, unknown>;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown> | null;
  read_at: string | null;
  created_at: string;
}

export interface ModelProbabilities {
  home: number;
  draw: number;
  away: number;
  source: string;
}

export interface MatchInsight {
  match_id: string;
  summary: string;
  provider: string;
  model: ModelProbabilities;
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[] | { message: string; [key: string]: unknown };
}
