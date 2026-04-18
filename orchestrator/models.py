from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SignalType(str, Enum):
    funding_round = "funding_round"
    leadership_change = "leadership_change"
    product_launch = "product_launch"
    hiring_surge = "hiring_surge"
    tech_install = "tech_install"
    employee_post = "employee_post"


class IncomingSignal(BaseModel):
    company_name: str
    signal_type: SignalType
    amount: Optional[float] = None          # e.g. 100_000_000 for $100M
    description: Optional[str] = None       # raw text from Apify/news
    source_url: Optional[str] = None
    source_query: Optional[str] = None
    source_author: Optional[str] = None
    source_author_role: Optional[str] = None


class GTMPlan(BaseModel):
    company_name: str
    signal_type: str
    signal_amount: Optional[float] = None
    signal_summary: str
    signal_source_url: Optional[str] = None
    signal_source_query: Optional[str] = None
    warm_paths: list[dict] = []
    tier: str
    composite_score: float
    score_reasoning: str
    why_now: str
    why_this_account: str
    work_saved: str
    committee_size: int
    buying_committee: list[dict]
    top_persona: str
    top_channel: str
    suggested_first_action: str
    account_snapshot: dict
    assumptions: list[str]
    objective: str
    sequence_days: int
    raw_tactics: list[dict]
    hubspot: Optional[dict] = None


class MarketLead(BaseModel):
    company_name: str
    signal_type: str
    signal_amount: Optional[float] = None
    signal_summary: str
    signal_source_url: Optional[str] = None
    signal_source_query: Optional[str] = None
    source_domain: Optional[str] = None
    verification_status: str = "source_backed"
    warm_paths: list[dict] = []
