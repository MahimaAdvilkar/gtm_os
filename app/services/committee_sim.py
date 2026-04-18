from app.models.account import Account
from app.models.buyer import BuyerPersona, BuyingCommittee, BuyerRole, PainLevel
from app.config import settings
import anthropic
import json


ROLE_TEMPLATES: dict[str, dict] = {
    "champion": {
        "title": "VP of Operations",
        "pain_level": PainLevel.high,
        "primary_pain": "Manual processes slowing team velocity",
        "preferred_channels": ["email", "linkedin"],
        "influence_score": 0.7,
    },
    "economic_buyer": {
        "title": "CFO",
        "pain_level": PainLevel.medium,
        "primary_pain": "ROI justification and budget allocation",
        "preferred_channels": ["email", "webinar"],
        "influence_score": 0.9,
    },
    "technical_evaluator": {
        "title": "Head of Engineering",
        "pain_level": PainLevel.medium,
        "primary_pain": "Integration complexity and security requirements",
        "preferred_channels": ["content", "webinar"],
        "influence_score": 0.6,
    },
}


class CommitteeSimulator:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def simulate(self, account: Account) -> BuyingCommittee:
        """Generate a synthetic buying committee based on account profile."""
        members = []
        for role_key, template in ROLE_TEMPLATES.items():
            members.append(
                BuyerPersona(
                    name=f"Synthetic {template['title']}",
                    title=template["title"],
                    role=BuyerRole(role_key),
                    pain_level=template["pain_level"],
                    primary_pain=template["primary_pain"],
                    goals=[],
                    objections=[],
                    preferred_channels=template["preferred_channels"],
                    influence_score=template["influence_score"],
                )
            )

        return BuyingCommittee(account_id=account.id, members=members)

    def simulate_with_ai(self, account: Account) -> BuyingCommittee:
        """Use Claude to generate a realistic, industry-specific buying committee."""
        prompt = f"""You are a B2B sales expert. Generate a realistic buying committee for this account.

Account: {account.name}
Industry: {account.industry}
Employees: {account.employee_count}
Tech Stack: {', '.join(account.tech_stack) or 'unknown'}

Return a JSON array of 3-4 buyer personas. Each must have:
- name (synthetic/generic)
- title
- role (champion|economic_buyer|technical_evaluator|end_user|blocker)
- pain_level (low|medium|high|critical)
- primary_pain (string)
- goals (list of 2 strings)
- objections (list of 2 strings)
- preferred_channels (list from: email, linkedin, paid_search, content, outbound_call, webinar)
- influence_score (0.0-1.0)

Respond with only valid JSON array."""

        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        members = [BuyerPersona(**p) for p in data]
        return BuyingCommittee(account_id=account.id, members=members, simulated=True)
