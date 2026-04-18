from app.models.funnel import FunnelOutcome, FunnelStage
from collections import defaultdict
from datetime import datetime


class OutcomeTracker:
    """Tracks funnel outcomes and derives conversion metrics to feed back into scoring."""

    def __init__(self):
        self._outcomes: list[FunnelOutcome] = []

    def record(self, outcome: FunnelOutcome) -> None:
        self._outcomes.append(outcome)

    def get_by_account(self, account_id: str) -> list[FunnelOutcome]:
        return [o for o in self._outcomes if o.account_id == account_id]

    def conversion_rates(self) -> dict[str, float]:
        stage_counts: dict[str, int] = defaultdict(int)
        converted_counts: dict[str, int] = defaultdict(int)

        for outcome in self._outcomes:
            key = outcome.stage.value
            stage_counts[key] += 1
            if outcome.converted:
                converted_counts[key] += 1

        return {
            stage: converted_counts[stage] / count
            for stage, count in stage_counts.items()
            if count > 0
        }

    def win_rate(self) -> float:
        decisions = [
            o for o in self._outcomes
            if o.stage in (FunnelStage.closed_won, FunnelStage.closed_lost)
        ]
        if not decisions:
            return 0.0
        return sum(1 for o in decisions if o.stage == FunnelStage.closed_won) / len(decisions)

    def average_deal_value(self) -> float:
        won = [o for o in self._outcomes if o.stage == FunnelStage.closed_won and o.deal_value]
        if not won:
            return 0.0
        return sum(o.deal_value for o in won) / len(won)

    def top_lost_reasons(self, n: int = 5) -> list[tuple[str, int]]:
        counts: dict[str, int] = defaultdict(int)
        for o in self._outcomes:
            if o.stage == FunnelStage.closed_lost and o.lost_reason:
                counts[o.lost_reason] += 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def summary(self) -> dict:
        return {
            "total_accounts": len({o.account_id for o in self._outcomes}),
            "total_outcomes": len(self._outcomes),
            "win_rate": round(self.win_rate(), 3),
            "avg_deal_value": round(self.average_deal_value(), 2),
            "conversion_rates": self.conversion_rates(),
            "top_lost_reasons": self.top_lost_reasons(),
        }
