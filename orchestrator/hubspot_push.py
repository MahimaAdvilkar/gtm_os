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
    """Create or update a HubSpot company, return its ID."""
    payload = {
        "properties": {
            "name": plan.company_name,
            "gtm_tier": plan.tier,
            "gtm_score": str(plan.composite_score),
            "gtm_objective": plan.objective,
            "gtm_sequence_days": str(plan.sequence_days),
            "gtm_signal": plan.signal_type,
        }
    }

    # Search for existing company first
    search_resp = httpx.post(
        f"{HUBSPOT_BASE}/crm/v3/objects/companies/search",
        headers=_headers(),
        json={
            "filterGroups": [{
                "filters": [{
                    "propertyName": "name",
                    "operator": "EQ",
                    "value": plan.company_name,
                }]
            }],
            "limit": 1,
        },
        timeout=15,
    )
    search_resp.raise_for_status()
    results = search_resp.json().get("results", [])

    if results:
        company_id = results[0]["id"]
        httpx.patch(
            f"{HUBSPOT_BASE}/crm/v3/objects/companies/{company_id}",
            headers=_headers(),
            json=payload,
            timeout=15,
        ).raise_for_status()
    else:
        create_resp = httpx.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/companies",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        create_resp.raise_for_status()
        company_id = create_resp.json()["id"]

    return company_id


def _create_deal(plan: GTMPlan, company_id: str) -> str:
    """Create a HubSpot deal linked to the company."""
    payload = {
        "properties": {
            "dealname": f"[GTM OS] {plan.company_name} — {plan.signal_type}",
            "pipeline": "default",
            "dealstage": "appointmentscheduled",
            "gtm_tier": plan.tier,
            "gtm_top_persona": plan.top_persona,
            "gtm_top_channel": plan.top_channel,
        },
        "associations": [{
            "to": {"id": company_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}],
        }],
    }

    resp = httpx.post(
        f"{HUBSPOT_BASE}/crm/v3/objects/deals",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def push_gtm_plan(plan: GTMPlan) -> dict:
    """Push a GTM plan into HubSpot as a company + deal."""
    company_id = _upsert_company(plan)
    deal_id = _create_deal(plan, company_id)
    return {
        "company_id": company_id,
        "deal_id": deal_id,
        "portal_url": f"https://app.hubspot.com/contacts/{settings.hubspot_portal_id}/company/{company_id}",
    }
