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
    "employee_post":       {"employee_count": 250, "revenue": 8_000_000},
}

# Use AI-enhanced methods when Anthropic key is available
USE_AI = bool(settings.anthropic_api_key)

INDUSTRY_KEYWORDS = {
    Industry.fintech: {"payments", "finance", "fintech", "card", "banking", "treasury"},
    Industry.healthcare: {"health", "healthcare", "clinical", "medical", "patient"},
    Industry.ecommerce: {"commerce", "ecommerce", "retail", "marketplace", "checkout"},
    Industry.enterprise: {"security", "compliance", "infrastructure", "enterprise", "it"},
    Industry.saas: {"ai", "software", "developer", "platform", "saas", "automation"},
}

SIGNAL_EXPLANATIONS = {
    "funding_round": "Fresh capital usually means new budget, more hiring, and executive pressure to deploy tools that accelerate growth.",
    "hiring_surge": "Rapid hiring creates onboarding, process, and tooling pain, which makes buyers more open to workflow and productivity solutions.",
    "product_launch": "A new launch often creates urgency around pipeline generation, instrumentation, and execution reliability.",
    "leadership_change": "A new executive is a forcing function for tooling changes, team audits, and process resets.",
    "tech_install": "A new install or stack change is a strong buying trigger because adjacent tooling is actively being evaluated.",
    "employee_post": "A public employee or team post is a warm-path signal because someone inside the account is already exposing a current priority in public.",
}

ACCOUNT_EXPLANATIONS = {
    Industry.saas: "The account sits in a software category where outbound teams can use a signal-led playbook to start timely conversations.",
    Industry.enterprise: "The account appears to have enterprise workflow or infrastructure characteristics, which usually means multi-stakeholder evaluation and larger contract value.",
    Industry.fintech: "The account appears fintech-oriented, where timing, compliance, and ROI messaging tend to matter early in evaluation.",
    Industry.healthcare: "The account appears healthcare-oriented, so the sales motion likely depends on trust, controls, and operational pain.",
    Industry.ecommerce: "The account appears commerce-oriented, where growth and tooling changes tend to create short buying windows.",
}


def _infer_industry(signal: IncomingSignal) -> Industry:
    text = " ".join(filter(None, [signal.company_name, signal.description, signal.source_url])).lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return industry
    return Industry.saas


def _build_signal_summary(signal: IncomingSignal) -> str:
    if signal.description:
        return signal.description.strip()

    label = signal.signal_type.replace("_", " ")
    if signal.amount and signal.signal_type == "funding_round":
        amount = f"${signal.amount:,.0f}"
        return f"{signal.company_name} appears to have a {label} signal of approximately {amount}."
    return f"{signal.company_name} triggered a {label} signal."


def _build_why_now(signal: IncomingSignal, score_tier: str) -> str:
    base = SIGNAL_EXPLANATIONS.get(signal.signal_type, "This signal suggests the account may be entering an evaluation window.")
    urgency = {
        "A": "This should be worked immediately by the outbound team.",
        "B": "This is worth near-term outbound prioritization.",
        "C": "This is a lower-confidence trigger and should be validated before heavy outreach.",
    }[score_tier]
    return f"{base} {urgency}"


def _build_why_this_account(industry: Industry, score) -> str:
    base = ACCOUNT_EXPLANATIONS.get(
        industry,
        "This account matches a signal-led outbound motion where a fast first touch can create pipeline before competitors react.",
    )
    return (
        f"{base} "
        f"The current model scores it at {score.composite_score}/100 with fit {score.fit_score}, "
        f"intent {score.intent_score}, and timing {score.timing_score}."
    )


def _build_assumptions(signal: IncomingSignal, industry: Industry, employee_count: int, revenue: float) -> list[str]:
    assumptions = [
        f"Industry inferred as {industry.value} from company and signal context.",
        f"Company size is estimated at roughly {employee_count} employees based on signal type, not a firmographic provider.",
        f"Revenue is estimated at about ${revenue:,.0f} for prioritization only.",
        "Buying committee is an AI-generated hypothesis to speed first-pass outreach planning.",
    ]
    if not signal.source_url:
        assumptions.append("No source URL was provided, so the signal should be treated as operator-entered rather than source-verified.")
    return assumptions


def _build_work_saved() -> str:
    return "Estimated rep work eliminated: 30 to 60 minutes of manual account research, persona mapping, and first-touch planning."


def _build_first_action(top_tactic, top_member, signal: IncomingSignal) -> str:
    if signal.source_author:
        return (
            f"Open the source post from {signal.source_author}, verify their role and relevance, then use that public "
            f"context as a warm path before routing outreach to {top_member.title}."
        )
    if signal.signal_type == "employee_post":
        return (
            f"Open the source post, verify the poster/team context, then engage the public thread or route a "
            f"personalized note to {top_member.title} anchored on that post."
        )
    if top_tactic is None:
        return f"Validate the {signal.signal_type.replace('_', ' ')} signal, confirm account fit, and queue the account for SDR review."
    signal_label = signal.signal_type.replace("_", " ")
    return (
        f"Start with {top_tactic.channel.replace('_', ' ')} to {top_member.title}, "
        f"anchored on the {signal_label} trigger, and use this as the first outbound touch."
    )


def route(signal: IncomingSignal) -> GTMPlan:
    boost = SIGNAL_BOOSTS.get(signal.signal_type, {})
    industry = _infer_industry(signal)
    employee_count = boost.get("employee_count", 100)
    annual_revenue = boost.get("revenue", 1_000_000)
    signal_summary = _build_signal_summary(signal)

    account = Account(
        id=signal.company_name.lower().replace(" ", "-"),
        name=signal.company_name,
        industry=industry,
        employee_count=employee_count,
        annual_revenue=annual_revenue,
        tech_stack=[],
        signal_context=signal_summary,
        signal_type=signal.signal_type,
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
    why_now = _build_why_now(signal, score.tier)
    why_this_account = _build_why_this_account(industry, score)
    assumptions = _build_assumptions(signal, industry, employee_count, annual_revenue)
    work_saved = _build_work_saved()
    suggested_first_action = _build_first_action(top_tactic, top_member, signal)
    warm_paths = []
    if signal.source_author or (signal.source_url and "linkedin.com" in signal.source_url):
        warm_paths.append(
            {
                "name": signal.source_author or "Public LinkedIn poster",
                "role": signal.source_author_role or "Unverified public source",
                "source_url": signal.source_url,
                "source_query": signal.source_query,
                "note": "Use as a warm-path hypothesis. Verify the person and role before adding as a CRM contact.",
            }
        )

    return GTMPlan(
        company_name=signal.company_name,
        signal_type=signal.signal_type,
        signal_amount=signal.amount,
        signal_summary=signal_summary,
        signal_source_url=signal.source_url,
        signal_source_query=signal.source_query,
        warm_paths=warm_paths,
        tier=score.tier,
        composite_score=score.composite_score,
        score_reasoning=score.reasoning,
        why_now=why_now,
        why_this_account=why_this_account,
        work_saved=work_saved,
        committee_size=len(committee.members),
        buying_committee=[member.model_dump(mode="json") for member in committee.members],
        top_persona=top_member.title,
        top_channel=top_tactic.channel if top_tactic else "email",
        suggested_first_action=suggested_first_action,
        account_snapshot={
            "industry": industry.value,
            "employee_count_estimate": employee_count,
            "annual_revenue_estimate": annual_revenue,
            "signal_type": signal.signal_type,
        },
        assumptions=assumptions,
        objective=strategy.objective,
        sequence_days=strategy.sequence_days,
        raw_tactics=[t.model_dump(mode="json") for t in strategy.tactics],
    )
