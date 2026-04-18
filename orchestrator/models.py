from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SignalType(str, Enum):
    funding_round = "funding_round"
    leadership_change = "leadership_change"
    product_launch = "product_launch"
    hiring_surge = "hiring_surge"
    tech_install = "tech_install"


class IncomingSignal(BaseModel):
    company_name: str
    signal_type: SignalType
    amount: Optional[float] = None          # e.g. 100_000_000 for $100M
    description: Optional[str] = None       # raw text from Apify/news
    source_url: Optional[str] = None


class GTMPlan(BaseModel):
    company_name: str
    signal_type: str
    tier: str
    composite_score: float
    committee_size: int
    top_persona: str
    top_channel: str
    objective: str
    sequence_days: int
    raw_tactics: list[dict]
    hubspot: Optional[dict] = None
