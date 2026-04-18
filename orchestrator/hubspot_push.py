import httpx
from app.config import settings
from orchestrator.models import GTMPlan

HUBSPOT_BASE = "https://api.hubapi.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.hubspot_api_key}",
        "Content-Type": "application/json",
    }


def _upsert_company(plan: GTMPlan) -> str:
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
            "description": f"GTM OS | Tier {plan.tier} | Score {plan.composite_score} | Signal: {plan.signal_type}",
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
    payload = {
        "properties": {
            "dealname": f"[GTM OS] {plan.company_name} — {plan.signal_type.replace('_', ' ').title()}",
            "pipeline": "default",
            "dealstage": "appointmentscheduled",
            "description": f"Tier {plan.tier} | Top persona: {plan.top_persona} | Channel: {plan.top_channel} | {plan.objective}",
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


def push_gtm_plan(plan: GTMPlan) -> dict:
    company_id = _upsert_company(plan)
    deal_id = _create_deal(plan, company_id)
    return {
        "company_id": company_id,
        "deal_id": deal_id,
        "portal_url": f"https://app.hubspot.com/contacts/{settings.hubspot_portal_id}/company/{company_id}",
    }
