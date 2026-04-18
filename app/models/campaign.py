from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class CampaignChannel(str, Enum):
    email = "email"
    linkedin = "linkedin"
    paid_search = "paid_search"
    content = "content"
    outbound_call = "outbound_call"
    webinar = "webinar"
    direct_mail = "direct_mail"


class CampaignTactic(BaseModel):
    channel: CampaignChannel
    message: str
    cta: str
    target_persona: str
    priority: int = Field(ge=1, le=5)


class CampaignStrategy(BaseModel):
    account_id: str
    objective: str
    tactics: list[CampaignTactic]
    sequence_days: int = Field(description="Recommended outreach sequence duration in days")
    estimated_pipeline: Optional[float] = None
    notes: str = ""
