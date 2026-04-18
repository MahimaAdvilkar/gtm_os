import pytest
from app.models.account import Account, Industry
from app.services.account_scorer import AccountScorer


@pytest.fixture
def scorer():
    return AccountScorer()


@pytest.fixture
def tier_a_account():
    return Account(
        id="acct-001",
        name="Acme Corp",
        industry=Industry.saas,
        employee_count=1000,
        annual_revenue=50_000_000,
        tech_stack=["salesforce", "hubspot", "slack"],
    )


@pytest.fixture
def tier_c_account():
    return Account(
        id="acct-002",
        name="Small Shop",
        industry=Industry.other,
        employee_count=10,
        annual_revenue=200_000,
        tech_stack=[],
    )


def test_score_returns_account_score(scorer, tier_a_account):
    result = scorer.score(tier_a_account)
    assert result.account_id == tier_a_account.id
    assert 0 <= result.composite_score <= 100
    assert result.tier in ("A", "B", "C")


def test_tier_a_account_scores_high(scorer, tier_a_account):
    result = scorer.score(tier_a_account)
    assert result.tier == "A"
    assert result.composite_score >= 75


def test_tier_c_account_scores_low(scorer, tier_c_account):
    result = scorer.score(tier_c_account)
    assert result.tier == "C"
    assert result.composite_score < 50


def test_batch_scoring_is_sorted(scorer, tier_a_account, tier_c_account):
    scores = [scorer.score(a) for a in [tier_c_account, tier_a_account]]
    sorted_scores = sorted(scores, key=lambda s: s.composite_score, reverse=True)
    assert sorted_scores[0].account_id == tier_a_account.id
