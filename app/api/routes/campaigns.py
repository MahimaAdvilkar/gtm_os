from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.models.account import Account, AccountScore
from app.models.buyer import BuyingCommittee
from app.models.campaign import CampaignStrategy
from app.services.committee_sim import CommitteeSimulator
from app.services.campaign_gen import CampaignGenerator

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
simulator = CommitteeSimulator()
generator = CampaignGenerator()


class GTMRequest(BaseModel):
    account: Account
    score: AccountScore


@router.post("/simulate-committee", response_model=BuyingCommittee)
def simulate_committee(account: Account, use_ai: bool = Query(False)):
    """Simulate a synthetic buying committee for an account."""
    if use_ai:
        return simulator.simulate_with_ai(account)
    return simulator.simulate(account)


@router.post("/generate", response_model=CampaignStrategy)
def generate_campaign(request: GTMRequest, use_ai: bool = Query(False)):
    """Generate a campaign strategy for an account given its score."""
    committee = simulator.simulate(request.account)
    if use_ai:
        return generator.generate_with_ai(request.account, request.score, committee)
    return generator.generate(request.account, request.score, committee)
