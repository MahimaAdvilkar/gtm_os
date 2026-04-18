from orchestrator.models import IncomingSignal, GTMPlan
from app.models.account import Account, Industry
from app.services.account_scorer import AccountScorer
from app.services.campaign_gen import CampaignGenerator
from app.services.committee_sim import CommitteeSimulator
from app.config import settings

scorer = AccountScorer()
simulator = CommitteeSimulator()
generator = CampaignGenerator()

SIGNAL_BOOSTS: dict[str, dict] = {
    "funding_round":      {"employee_count": 500, "revenue": 20_000_000},
    "leadership_change":  {"employee_count": 200, "revenue": 5_000_000},
    "product_launch":     {"employee_count": 300, "revenue": 10_000_000},
    "hiring_surge":       {"employee_count": 400, "revenue": 15_000_000},
    "tech_install":       {"employee_count": 150, "revenue": 3_000_000},
}

# Use AI-enhanced methods when Anthropic key is available
USE_AI = bool(settings.anthropic_api_key)


def route(signal: IncomingSignal) -> GTMPlan:
    boost = SIGNAL_BOOSTS.get(signal.signal_type, {})

    account = Account(
        id=signal.company_name.lower().replace(" ", "-"),
        name=signal.company_name,
        industry=Industry.saas,
        employee_count=boost.get("employee_count", 100),
        annual_revenue=boost.get("revenue", 1_000_000),
        tech_stack=[],
    )

    # AI scoring if key available, else rule-based
    score = scorer.score_with_ai(account) if USE_AI else scorer.score(account)

    # AI committee simulation if key available
    committee = (
        simulator.simulate_with_ai(account) if USE_AI
        else simulator.simulate(account)
    )

    # AI campaign generation if key available
    strategy = (
        generator.generate_with_ai(account, score, committee) if USE_AI
        else generator.generate(account, score, committee)
    )

    top_member = max(committee.members, key=lambda m: m.influence_score)
    top_tactic = min(strategy.tactics, key=lambda t: t.priority) if strategy.tactics else None

    return GTMPlan(
        company_name=signal.company_name,
        signal_type=signal.signal_type,
        tier=score.tier,
        composite_score=score.composite_score,
        committee_size=len(committee.members),
        top_persona=top_member.title,
        top_channel=top_tactic.channel if top_tactic else "email",
        objective=strategy.objective,
        sequence_days=strategy.sequence_days,
        raw_tactics=[t.model_dump() for t in strategy.tactics],
    )
