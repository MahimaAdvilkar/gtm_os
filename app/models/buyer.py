from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class BuyerRole(str, Enum):
    champion = "champion"
    economic_buyer = "economic_buyer"
    technical_evaluator = "technical_evaluator"
    end_user = "end_user"
    blocker = "blocker"


class PainLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class BuyerPersona(BaseModel):
    name: str
    title: str
    role: BuyerRole
    pain_level: PainLevel
    primary_pain: str
    goals: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    preferred_channels: list[str] = Field(default_factory=list)
    influence_score: float = Field(ge=0, le=1, description="0-1 influence weight in decision")


class BuyingCommittee(BaseModel):
    account_id: str
    members: list[BuyerPersona]
    avg_deal_size: Optional[float] = None
    avg_sales_cycle_days: Optional[int] = None
    consensus_required: bool = True
    simulated: bool = True
