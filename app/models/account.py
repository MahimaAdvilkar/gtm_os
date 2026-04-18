from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Industry(str, Enum):
    saas = "saas"
    fintech = "fintech"
    healthcare = "healthcare"
    ecommerce = "ecommerce"
    enterprise = "enterprise"
    other = "other"


class Account(BaseModel):
    id: str
    name: str
    industry: Industry
    employee_count: int
    annual_revenue: float
    tech_stack: list[str] = Field(default_factory=list)
    location: Optional[str] = None
    website: Optional[str] = None


class AccountScore(BaseModel):
    account_id: str
    fit_score: float = Field(ge=0, le=100, description="ICP fit score 0-100")
    intent_score: float = Field(ge=0, le=100, description="Buying intent signal 0-100")
    timing_score: float = Field(ge=0, le=100, description="Purchase timing likelihood 0-100")
    composite_score: float = Field(ge=0, le=100, description="Weighted composite 0-100")
    tier: str = Field(description="A, B, or C tier")
    reasoning: str = Field(description="Explanation of the score")
