import pytest
from app.models.account import Account, Industry
from app.models.account import AccountScore
from app.services.account_scorer import AccountScorer
from app.services.committee_sim import CommitteeSimulator
from app.services.campaign_gen import CampaignGenerator


@pytest.fixture
def account():
    return Account(
        id="acct-001",
        name="Acme Corp",
        industry=Industry.saas,
        employee_count=500,
        annual_revenue=20_000_000,
        tech_stack=["salesforce", "slack"],
    )


@pytest.fixture
def setup(account):
    score = AccountScorer().score(account)
    committee = CommitteeSimulator().simulate(account)
    return account, score, committee


def test_generate_returns_strategy(setup):
    account, score, committee = setup
    strategy = CampaignGenerator().generate(account, score, committee)
    assert strategy.account_id == account.id
    assert len(strategy.tactics) > 0
    assert strategy.sequence_days > 0


def test_tier_a_gets_shorter_sequence(setup):
    account, score, committee = setup
    if score.tier == "A":
        strategy = CampaignGenerator().generate(account, score, committee)
        assert strategy.sequence_days == 30
