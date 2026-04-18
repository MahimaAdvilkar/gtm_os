"""
GTM OS — Hackathon Demo Runner
Usage:
    python demo.py                        # runs default Cursor scenario
    python demo.py "Ramp" funding_round
    python demo.py "Rippling" hiring_surge
"""
import sys
from orchestrator.models import IncomingSignal, SignalType
from orchestrator.pipeline import run_from_signal

DIVIDER = "─" * 60


def print_plan(plan) -> None:
    print(f"\n{DIVIDER}")
    print(f"  GTM OS — Signal Processed")
    print(DIVIDER)
    print(f"  Company      : {plan.company_name}")
    print(f"  Signal       : {plan.signal_type}")
    print(f"  Tier         : {plan.tier}  |  Score: {plan.composite_score}/100")
    print(f"  Committee    : {plan.committee_size} buyers simulated")
    print(f"  Top Persona  : {plan.top_persona}")
    print(f"  Top Channel  : {plan.top_channel}")
    print(f"  Objective    : {plan.objective}")
    print(f"  Sequence     : {plan.sequence_days} days")
    print(f"\n  Tactics ({len(plan.raw_tactics)}):")
    for t in plan.raw_tactics:
        print(f"    [{t['priority']}] {t['channel'].upper():12} → {t['target_persona']}")
        print(f"         {t['message']}")
    if plan.hubspot:
        print(f"\n  HubSpot:")
        print(f"    Company ID : {plan.hubspot.get('company_id')}")
        print(f"    Deal ID    : {plan.hubspot.get('deal_id')}")
        print(f"    URL        : {plan.hubspot.get('portal_url')}")
    print(DIVIDER)


def main():
    company = sys.argv[1] if len(sys.argv) > 1 else "Cursor"
    signal_type = sys.argv[2] if len(sys.argv) > 2 else "funding_round"
    amount_map = {
        "funding_round": 100_000_000,
        "hiring_surge": None,
        "product_launch": None,
        "leadership_change": None,
        "tech_install": None,
    }

    print(f"\nRunning GTM OS pipeline for: {company} ({signal_type})")
    print("Simulating buying committee via Minds AI...")
    print("Scoring account...")

    signal = IncomingSignal(
        company_name=company,
        signal_type=SignalType(signal_type),
        amount=amount_map.get(signal_type),
    )

    # push_hubspot=False for quick demo; set True when showing judges
    plan = run_from_signal(signal, push_hubspot=False)
    print_plan(plan)


if __name__ == "__main__":
    main()
