import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_league_or_404, get_membership
from app.db.session import get_db
from app.models.gameweek import Match
from app.models.league import League, LeagueMembership
from app.schemas.ai import MatchInsightOut
from app.services.ai_providers import generate_match_insight

router = APIRouter(prefix="/leagues/{league_id}/matches", tags=["matches"])


@router.get("/{match_id}/insight", response_model=MatchInsightOut)
def get_match_insight(
    match_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _membership: LeagueMembership = Depends(get_membership),
) -> MatchInsightOut:
    match = db.get(Match, match_id)
    if match is None or match.gameweek.season.league_id != league.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    text, provider = generate_match_insight(match)
    return MatchInsightOut(match_id=match.id, summary=text, provider=provider)
