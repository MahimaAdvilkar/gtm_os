from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from orchestrator.models import IncomingSignal, GTMPlan
from orchestrator.pipeline import run_from_signal, run_from_company, run_batch

router = APIRouter(prefix="/webhook", tags=["webhook"])


class CompanyRequest(BaseModel):
    company_name: str


class BatchRequest(BaseModel):
    company_names: list[str]


@router.post("/signal", response_model=GTMPlan)
def signal_endpoint(
    signal: IncomingSignal,
    push_to_hubspot: bool = Query(True),
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
        return run_from_company(request.company_name, push_hubspot=push_to_hubspot)
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
