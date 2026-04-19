import httpx
from datetime import datetime, timezone
from app.config import settings
from orchestrator.models import GTMPlan

HUBSPOT_BASE = "https://api.hubapi.com"
NOTE_TO_COMPANY_ASSOCIATION = 190
NOTE_TO_DEAL_ASSOCIATION = 214


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.hubspot_api_key}",
        "Content-Type": "application/json",
    }


def _upsert_company(plan: GTMPlan) -> str:
    warm_path_text = _warm_path_text(plan)
    search_resp = httpx.post(
        f"{HUBSPOT_BASE}/crm/v3/objects/companies/search",
        headers=_headers(),
        json={
            "filterGroups": [{"filters": [{
                "propertyName": "name",
                "operator": "EQ",
                "value": plan.company_name,
            }]}],
            "limit": 1,
        },
        timeout=15,
    )
    search_resp.raise_for_status()
    results = search_resp.json().get("results", [])

    # Only standard HubSpot properties — no custom fields needed
    payload = {
        "properties": {
            "name": plan.company_name,
            "description": (
                f"GTM OS\n"
                f"Signal: {plan.signal_type}\n"
                f"Amount: {f'${plan.signal_amount:,.0f}' if plan.signal_amount else 'n/a'}\n"
                f"Summary: {plan.signal_summary}\n"
                f"Tier: {plan.tier} | Score: {plan.composite_score}\n"
                f"Why now: {plan.why_now}\n"
                f"Why this account: {plan.why_this_account}\n"
                f"Suggested first action: {plan.suggested_first_action}\n"
                f"Warm path: {warm_path_text}\n"
                f"Assumptions: {'; '.join(plan.assumptions[:2])}"
            ),
        }
    }

    if results:
        company_id = results[0]["id"]
        httpx.patch(
            f"{HUBSPOT_BASE}/crm/v3/objects/companies/{company_id}",
            headers=_headers(), json=payload, timeout=15,
        ).raise_for_status()
    else:
        resp = httpx.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/companies",
            headers=_headers(), json=payload, timeout=15,
        )
        resp.raise_for_status()
        company_id = resp.json()["id"]

    return company_id


def _create_deal(plan: GTMPlan, company_id: str) -> str:
    warm_path_text = _warm_path_text(plan)
    top_tactic = plan.raw_tactics[0] if plan.raw_tactics else None
    tactic_summary = (
        f"First action: {top_tactic['channel']} to {top_tactic['target_persona']} — {top_tactic['message']}"
        if top_tactic else "No tactic generated."
    )
    payload = {
        "properties": {
            "dealname": f"[GTM OS] {plan.company_name} — {plan.signal_type.replace('_', ' ').title()}",
            "pipeline": "default",
            "dealstage": "appointmentscheduled",
            "description": (
                f"Signal summary: {plan.signal_summary}\n"
                f"Why now: {plan.why_now}\n"
                f"Why this account: {plan.why_this_account}\n"
                f"Tier {plan.tier} | Score {plan.composite_score}\n"
                f"Top persona: {plan.top_persona} | Preferred channel: {plan.top_channel}\n"
                f"Suggested first action: {plan.suggested_first_action}\n"
                f"Warm path: {warm_path_text}\n"
                f"Objective: {plan.objective}\n"
                f"{tactic_summary}\n"
                f"Source: {plan.signal_source_url or 'operator entered'}"
            ),
        },
        "associations": [{
            "to": {"id": company_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}],
        }],
    }

    resp = httpx.post(
        f"{HUBSPOT_BASE}/crm/v3/objects/deals",
        headers=_headers(), json=payload, timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _warm_path_text(plan: GTMPlan) -> str:
    if not plan.warm_paths:
        return "None detected."
    path = plan.warm_paths[0]
    return (
        f"{path.get('name', 'Public source')} ({path.get('role', 'unverified role')}) "
        f"via {path.get('source_url') or 'source result'}; verify before creating a contact."
    )


def _format_money(amount: float | None) -> str:
    return f"${amount:,.0f}" if amount else "n/a"


def _note_timestamp_ms() -> str:
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def _create_note(title: str, body: str, company_id: str, deal_id: str) -> str:
    payload = {
        "properties": {
            "hs_note_body": f"<b>{title}</b><br><br>{body}",
            "hs_timestamp": _note_timestamp_ms(),
        },
        "associations": [
            {
                "to": {"id": company_id},
                "types": [{
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": NOTE_TO_COMPANY_ASSOCIATION,
                }],
            },
            {
                "to": {"id": deal_id},
                "types": [{
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": NOTE_TO_DEAL_ASSOCIATION,
                }],
            },
        ],
    }
    resp = httpx.post(
        f"{HUBSPOT_BASE}/crm/v3/objects/notes",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _create_context_notes(plan: GTMPlan, company_id: str, deal_id: str) -> list[str]:
    notes = [
        (
            "GTM OS Signal Evidence",
            "<br>".join([
                f"Company: {plan.company_name}",
                f"Signal: {plan.signal_type.replace('_', ' ').title()}",
                f"Amount: {_format_money(plan.signal_amount)}",
                f"Source: {plan.signal_source_url or 'Manual input'}",
                f"Search query: {plan.signal_source_query or 'n/a'}",
                f"Summary: {plan.signal_summary}",
                f"Why now: {plan.why_now}",
                f"Why this account: {plan.why_this_account}",
            ]),
        ),
        (
            "GTM OS Buying Committee Hypothesis",
            "<br>".join(
                [
                    f"{m.get('title', 'Unknown title')} - {m.get('role', 'unknown role')} - "
                    f"pain: {m.get('primary_pain', 'n/a')} - "
                    f"influence: {m.get('influence_score', 'n/a')}"
                    for m in plan.buying_committee
                ]
            ),
        ),
        (
            "GTM OS First Outreach Motion",
            "<br>".join(
                [
                    f"{t.get('priority', '-')}. {str(t.get('channel', '')).upper()} to "
                    f"{t.get('target_persona', 'Unknown persona')}: "
                    f"{t.get('message', 'No message')} CTA: {t.get('cta', 'n/a')}"
                    for t in plan.raw_tactics
                ]
            ),
        ),
    ]

    if plan.warm_paths:
        notes.append((
            "GTM OS Warm Path Candidates",
            "<br>".join(
                [
                    f"{p.get('name', 'Public source')} - {p.get('role', 'unverified role')} - "
                    f"{p.get('source_url', 'no source URL')}. Verify identity/email before creating a contact."
                    for p in plan.warm_paths
                ]
            ),
        ))

    return [_create_note(title, body, company_id, deal_id) for title, body in notes]


def push_gtm_plan(plan: GTMPlan) -> dict:
    company_id = _upsert_company(plan)
    deal_id = _create_deal(plan, company_id)
    notes_created: list[str] = []
    note_error = None
    try:
        notes_created = _create_context_notes(plan, company_id, deal_id)
    except Exception as exc:
        # Do not fail the opportunity push if activity-note creation hits a HubSpot limitation.
        note_error = str(exc)

    return {
        "company_id": company_id,
        "deal_id": deal_id,
        "notes_created": notes_created,
        "note_error": note_error,
        "portal_url": f"https://app.hubspot.com/contacts/{settings.hubspot_portal_id}/company/{company_id}",
    }
