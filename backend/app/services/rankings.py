import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import GameweekStatus
from app.models.gameweek import Gameweek
from app.models.league import League, LeagueMembership, Season
from app.models.prediction import Wallet
from app.models.user import User
from app.schemas.ranking import RankingRow


def _active_member_ids(db: Session, league_id: uuid.UUID) -> list[uuid.UUID]:
    return [
        m.user_id
        for m in db.query(LeagueMembership)
        .filter(LeagueMembership.league_id == league_id, LeagueMembership.is_active.is_(True))
        .all()
    ]


def gameweek_ranking(db: Session, league: League, gameweek: Gameweek) -> list[RankingRow]:
    """This gameweek's own leaderboard — purely this week's net change,
    since everyone starts each gameweek at the same budget."""
    member_ids = _active_member_ids(db, league.id)
    wallets = {
        w.user_id: w
        for w in db.query(Wallet).filter(Wallet.gameweek_id == gameweek.id, Wallet.user_id.in_(member_ids)).all()
    }

    rows = []
    for user_id in member_ids:
        wallet = wallets.get(user_id)
        balance = wallet.current_balance if wallet else gameweek.budget
        starting = wallet.starting_balance if wallet else gameweek.budget
        rows.append((user_id, balance, balance - starting))

    rows.sort(key=lambda r: (-r[1], str(r[0])))
    users = {u.id: u for u in db.query(User).filter(User.id.in_(member_ids)).all()}
    return [
        RankingRow(position=i + 1, previous_position=None, user=users[uid], balance=balance, net_change=net)
        for i, (uid, balance, net) in enumerate(rows)
    ]


def season_positions(db: Session, league: League, season: Season, up_to_gameweek_number: int) -> dict[uuid.UUID, int]:
    """Cumulative net winnings across every SETTLED gameweek up to and
    including `up_to_gameweek_number` -> {user_id: position}. This is the
    "who's actually winning the league" ranking used for the champion, the
    season leaderboard, and the movement shown on the results screen."""
    member_ids = _active_member_ids(db, league.id)

    totals = dict.fromkeys(member_ids, 0)
    if up_to_gameweek_number >= 1:
        rows = (
            db.query(Wallet.user_id, func.sum(Wallet.current_balance - Wallet.starting_balance))
            .join(Gameweek, Gameweek.id == Wallet.gameweek_id)
            .filter(
                Gameweek.season_id == season.id,
                Gameweek.status == GameweekStatus.SETTLED,
                Gameweek.number <= up_to_gameweek_number,
                Wallet.user_id.in_(member_ids),
            )
            .group_by(Wallet.user_id)
            .all()
        )
        for user_id, total in rows:
            totals[user_id] = int(total or 0)

    ordered = sorted(totals.items(), key=lambda r: (-r[1], str(r[0])))
    return {user_id: i + 1 for i, (user_id, _total) in enumerate(ordered)}


def season_ranking(db: Session, league: League, season: Season) -> list[RankingRow]:
    latest_number = db.query(func.max(Gameweek.number)).filter(Gameweek.season_id == season.id).scalar() or 0
    positions = season_positions(db, league, season, latest_number)
    totals = _season_totals(db, league, season, latest_number)
    users = {u.id: u for u in db.query(User).filter(User.id.in_(positions.keys())).all()}

    return [
        RankingRow(position=pos, previous_position=None, user=users[uid], balance=totals.get(uid, 0), net_change=0)
        for uid, pos in sorted(positions.items(), key=lambda kv: kv[1])
    ]


def _season_totals(db: Session, league: League, season: Season, up_to_gameweek_number: int) -> dict[uuid.UUID, int]:
    member_ids = _active_member_ids(db, league.id)
    totals = dict.fromkeys(member_ids, 0)
    rows = (
        db.query(Wallet.user_id, func.sum(Wallet.current_balance - Wallet.starting_balance))
        .join(Gameweek, Gameweek.id == Wallet.gameweek_id)
        .filter(
            Gameweek.season_id == season.id,
            Gameweek.status == GameweekStatus.SETTLED,
            Gameweek.number <= up_to_gameweek_number,
            Wallet.user_id.in_(member_ids),
        )
        .group_by(Wallet.user_id)
        .all()
    )
    for user_id, total in rows:
        totals[user_id] = int(total or 0)
    return totals
