import enum


class MembershipRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class GameweekStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    OPEN = "open"
    LOCKED = "locked"
    SETTLED = "settled"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"


class MatchOutcome(str, enum.Enum):
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"


class Market(str, enum.Enum):
    WINNER = "winner"  # 1X2 head-to-head
    DOUBLE_CHANCE = "double_chance"
    OVER_UNDER = "over_under"
    BOTH_TEAMS_TO_SCORE = "both_teams_to_score"


class Selection(str, enum.Enum):
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"
    HOME_OR_DRAW = "home_or_draw"
    AWAY_OR_DRAW = "away_or_draw"
    HOME_OR_AWAY = "home_or_away"
    OVER = "over"
    UNDER = "under"
    YES = "yes"
    NO = "no"


class BetStatus(str, enum.Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"


class ActivityType(str, enum.Enum):
    BET_PLACED = "bet_placed"
    STREAK_MILESTONE = "streak_milestone"
    BADGE_EARNED = "badge_earned"
    GAMEWEEK_SETTLED = "gameweek_settled"


class StreakType(str, enum.Enum):
    TOP_3_FINISH = "top_3_finish"
    CORRECT_PICKS = "correct_picks"


class ChallengeStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
