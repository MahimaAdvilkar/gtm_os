from fastapi import APIRouter
from app.models.funnel import FunnelOutcome
from app.services.outcome_tracker import OutcomeTracker

router = APIRouter(prefix="/outcomes", tags=["outcomes"])
tracker = OutcomeTracker()


@router.post("/record", status_code=201)
def record_outcome(outcome: FunnelOutcome):
    """Record a funnel stage outcome for an account."""
    tracker.record(outcome)
    return {"status": "recorded", "outcome_id": outcome.id}


@router.get("/summary")
def get_summary():
    """Return aggregate funnel metrics across all tracked outcomes."""
    return tracker.summary()


@router.get("/account/{account_id}", response_model=list[FunnelOutcome])
def get_account_outcomes(account_id: str):
    """Return all funnel outcomes for a specific account."""
    return tracker.get_by_account(account_id)
