from app.models.account import Account, AccountScore
from app.config import settings
import anthropic


ICP_WEIGHTS = {"fit": 0.4, "intent": 0.35, "timing": 0.25}

HIGH_VALUE_INDUSTRIES = {"saas", "fintech", "enterprise"}
HIGH_VALUE_TECH = {"salesforce", "hubspot", "slack", "stripe", "datadog"}


class AccountScorer:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def score(self, account: Account) -> AccountScore:
        fit = self._score_fit(account)
        intent = self._score_intent(account)
        timing = self._score_timing(account)

        composite = (
            fit * ICP_WEIGHTS["fit"]
            + intent * ICP_WEIGHTS["intent"]
            + timing * ICP_WEIGHTS["timing"]
        )

        tier = "A" if composite >= 75 else "B" if composite >= 50 else "C"
        reasoning = self._build_reasoning(account, fit, intent, timing, composite)

        return AccountScore(
            account_id=account.id,
            fit_score=round(fit, 1),
            intent_score=round(intent, 1),
            timing_score=round(timing, 1),
            composite_score=round(composite, 1),
            tier=tier,
            reasoning=reasoning,
        )

    def score_with_ai(self, account: Account) -> AccountScore:
        """Uses Claude to enrich scoring with qualitative reasoning."""
        base_score = self.score(account)

        prompt = f"""You are a B2B GTM analyst. Given this account profile, briefly explain why it is a {base_score.tier}-tier account and any GTM considerations.

Account: {account.name}
Industry: {account.industry}
Employees: {account.employee_count}
Revenue: ${account.annual_revenue:,.0f}
Tech Stack: {', '.join(account.tech_stack) or 'unknown'}

Composite Score: {base_score.composite_score}/100
Respond in 2-3 sentences."""

        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        base_score.reasoning = message.content[0].text
        return base_score

    def _score_fit(self, account: Account) -> float:
        score = 0.0
        if account.industry in HIGH_VALUE_INDUSTRIES:
            score += 35
        if account.employee_count >= 500:
            score += 25
        elif account.employee_count >= 100:
            score += 15
        if account.annual_revenue >= 10_000_000:
            score += 25
        elif account.annual_revenue >= 1_000_000:
            score += 15
        tech_overlap = len(set(t.lower() for t in account.tech_stack) & HIGH_VALUE_TECH)
        score += min(tech_overlap * 5, 15)
        return min(score, 100)

    def _score_intent(self, account: Account) -> float:
        # Placeholder — wire up intent data providers (G2, Bombora, etc.)
        return 50.0

    def _score_timing(self, account: Account) -> float:
        # Placeholder — wire up CRM/event signals
        return 50.0

    def _build_reasoning(self, account, fit, intent, timing, composite) -> str:
        return (
            f"{account.name} scored {composite:.0f}/100 composite "
            f"(fit={fit:.0f}, intent={intent:.0f}, timing={timing:.0f}). "
            f"Industry: {account.industry}, size: {account.employee_count} employees."
        )
