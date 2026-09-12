from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import require_staff
from app.db.session import get_db
from app.models.user import User
from app.schemas.system_admin import FailedJobOut, ModelVersionOut, OddsHealthRow, SystemOverviewOut
from app.services import system_admin

router = APIRouter(prefix="/admin/system", tags=["system-admin"])


@router.get("/overview", response_model=SystemOverviewOut)
def get_overview(db: Session = Depends(get_db), _staff: User = Depends(require_staff)) -> dict:
    return system_admin.get_overview(db)


@router.get("/model-versions", response_model=list[ModelVersionOut])
def get_model_versions(db: Session = Depends(get_db), _staff: User = Depends(require_staff)):
    return system_admin.list_model_versions(db)


@router.get("/odds-health", response_model=list[OddsHealthRow])
def get_odds_health(db: Session = Depends(get_db), _staff: User = Depends(require_staff)):
    return system_admin.odds_health(db)


@router.get("/failed-jobs", response_model=list[FailedJobOut])
def get_failed_jobs(db: Session = Depends(get_db), _staff: User = Depends(require_staff)):
    return system_admin.list_failed_jobs(db)
