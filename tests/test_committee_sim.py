import pytest
from app.models.account import Account, Industry
from app.services.committee_sim import CommitteeSimulator


@pytest.fixture
def simulator():
    return CommitteeSimulator()


@pytest.fixture
def account():
    return Account(
        id="acct-001",
        name="Acme Corp",
        industry=Industry.saas,
        employee_count=500,
        annual_revenue=20_000_000,
        tech_stack=["salesforce"],
    )


def test_simulate_returns_committee(simulator, account):
    committee = simulator.simulate(account)
    assert committee.account_id == account.id
    assert len(committee.members) > 0
    assert committee.simulated is True


def test_all_members_have_required_fields(simulator, account):
    committee = simulator.simulate(account)
    for member in committee.members:
        assert member.title
        assert member.role
        assert 0 <= member.influence_score <= 1
