from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from orchestrator.models import IncomingSignal, GTMPlan, SignalType, MarketLead
from orchestrator.pipeline import run_from_signal, run_from_company, run_batch
from orchestrator.apify_scraper import scan_market_leads
from urllib.parse import urlparse

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _source_domain(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


class CompanyRequest(BaseModel):
    company_name: str
    preferred_signal: SignalType | None = None


class BatchRequest(BaseModel):
    company_names: list[str]


class MarketScanRequest(BaseModel):
    signal_type: SignalType
    days_back: int = 30
    focus: str = "B2B SaaS"


@router.post("/signal", response_model=GTMPlan)
def signal_endpoint(
    signal: IncomingSignal,
    push_to_hubspot: bool = Query(False),
) -> GTMPlan:
    """Manual signal → full pipeline → HubSpot."""
    try:
        return run_from_signal(signal, push_hubspot=push_to_hubspot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=list[GTMPlan])
def run_endpoint(
    request: CompanyRequest,
    push_to_hubspot: bool = Query(True),
) -> list[GTMPlan]:
    """
    Full end-to-end for one company:
    Apify scrape → score → committee → campaign → HubSpot
    """
    try:
        return run_from_company(
            request.company_name,
            push_hubspot=push_to_hubspot,
            preferred_signal=request.preferred_signal,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=dict)
def batch_endpoint(
    request: BatchRequest,
    push_to_hubspot: bool = Query(True),
) -> dict:
    """Run the full pipeline for multiple companies at once."""
    try:
        return run_batch(request.company_names, push_hubspot=push_to_hubspot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-scan", response_model=list[MarketLead])
def market_scan_endpoint(request: MarketScanRequest) -> list[MarketLead]:
    """Scan the last N days of live web results for funding/hiring style leads."""
    try:
        leads = scan_market_leads(
            signal_type=request.signal_type,
            days_back=request.days_back,
            focus=request.focus,
        )
        return [
            MarketLead(
                company_name=lead.company_name,
                signal_type=lead.signal_type,
                signal_amount=lead.amount,
                signal_summary=lead.description or "",
                signal_source_url=lead.source_url,
                signal_source_query=lead.source_query,
                source_domain=_source_domain(lead.source_url),
                verification_status="source_backed" if lead.source_url else "unverified",
                warm_paths=[
                    {
                        "name": lead.source_author or "Public LinkedIn poster",
                        "role": lead.source_author_role or "Unverified public source",
                        "source_url": lead.source_url,
                        "note": "Verify before adding as a CRM contact.",
                    }
                ] if lead.source_author or (lead.source_url and "linkedin.com" in lead.source_url) else [],
            )
            for lead in leads
            if lead.source_url
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
