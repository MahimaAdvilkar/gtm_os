from fastapi import APIRouter, Query
from app.models.account import Account, AccountScore
from app.services.account_scorer import AccountScorer

router = APIRouter(prefix="/accounts", tags=["accounts"])
scorer = AccountScorer()


@router.post("/score", response_model=AccountScore)
def score_account(account: Account, use_ai: bool = Query(False)):
    """Score an account for ICP fit, intent, and timing."""
    if use_ai:
        return scorer.score_with_ai(account)
    return scorer.score(account)


@router.post("/score/batch", response_model=list[AccountScore])
def score_accounts_batch(accounts: list[Account]):
    """Score multiple accounts and return ranked results."""
    scores = [scorer.score(a) for a in accounts]
    return sorted(scores, key=lambda s: s.composite_score, reverse=True)
