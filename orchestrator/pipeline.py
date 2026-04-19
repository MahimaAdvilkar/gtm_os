from orchestrator.models import IncomingSignal, GTMPlan, SignalType
from orchestrator.signal_router import route
from orchestrator.apify_scraper import scrape_company_signals
from orchestrator.hubspot_push import push_gtm_plan


def run_from_signal(signal: IncomingSignal, push_hubspot: bool = True) -> GTMPlan:
    """Single signal → score → committee → campaign → HubSpot."""
    plan = route(signal)
    if push_hubspot:
        plan.hubspot = push_gtm_plan(plan)
    return plan


def run_from_company(
    company_name: str,
    push_hubspot: bool = True,
    preferred_signal: SignalType | None = None,
) -> list[GTMPlan]:
    """
    Full end-to-end:
    company name → Apify scrape → signals → score → committee → campaign → HubSpot
    """
    signals = scrape_company_signals(company_name, preferred_signal=preferred_signal)
    if not signals:
        raise ValueError(f"No signals found for '{company_name}'")

    # Demo path: generate the GTM motion for the strongest source-backed signal only.
    # Running AI strategy generation for every scraped result can take too long live.
    plans: list[GTMPlan] = []
    for signal in signals[:1]:
        plan = route(signal)
        if push_hubspot:
            plan.hubspot = push_gtm_plan(plan)
        plans.append(plan)

    return plans


def run_batch(company_names: list[str], push_hubspot: bool = True) -> dict[str, list[GTMPlan]]:
    """Run the full pipeline for multiple companies at once."""
    results: dict[str, list[GTMPlan]] = {}
    for name in company_names:
        try:
            results[name] = run_from_company(name, push_hubspot)
        except Exception as e:
            results[name] = [_error_plan(name, str(e))]
    return results


def _error_plan(company_name: str, error: str) -> GTMPlan:
    return GTMPlan(
        company_name=company_name,
        signal_type="error",
        signal_amount=None,
        signal_summary=f"Pipeline failed for {company_name}.",
        signal_source_url=None,
        signal_source_query=None,
        tier="—",
        composite_score=0,
        score_reasoning="No score available because the pipeline failed.",
        why_now="No recommendation available because the pipeline failed.",
        why_this_account="No account thesis available because the pipeline failed.",
        work_saved="No time saved because the pipeline failed.",
        committee_size=0,
        buying_committee=[],
        top_persona="—",
        top_channel="—",
        suggested_first_action="Check the failing integration and retry the workflow.",
        account_snapshot={},
        assumptions=[error],
        objective=f"Pipeline error: {error}",
        sequence_days=0,
        raw_tactics=[],
    )
