from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class FunnelStage(str, Enum):
    awareness = "awareness"
    consideration = "consideration"
    evaluation = "evaluation"
    decision = "decision"
    closed_won = "closed_won"
    closed_lost = "closed_lost"


class FunnelOutcome(BaseModel):
    id: str
    account_id: str
    campaign_id: Optional[str] = None
    stage: FunnelStage
    entered_at: datetime
    exited_at: Optional[datetime] = None
    converted: bool = False
    deal_value: Optional[float] = None
    lost_reason: Optional[str] = None
    notes: str = ""
