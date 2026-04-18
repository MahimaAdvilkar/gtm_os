from app.models.account import Account
from app.models.buyer import BuyerPersona, BuyingCommittee, BuyerRole, PainLevel
from app.config import settings
import anthropic
import json
from json import JSONDecodeError


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

SIGNAL_ROLE_TEMPLATES: dict[str, list[dict]] = {
    "funding_round": [
        {
            "title": "CRO",
            "role": BuyerRole.champion,
            "pain_level": PainLevel.high,
            "primary_pain": "Turning fresh funding into pipeline growth quickly",
            "preferred_channels": ["email", "linkedin"],
            "influence_score": 0.82,
        },
        {
            "title": "VP of Sales",
            "role": BuyerRole.end_user,
            "pain_level": PainLevel.high,
            "primary_pain": "Prioritizing the right accounts before the new sales plan ramps",
            "preferred_channels": ["linkedin", "outbound_call"],
            "influence_score": 0.74,
        },
        {
            "title": "CFO",
            "role": BuyerRole.economic_buyer,
            "pain_level": PainLevel.medium,
            "primary_pain": "Ensuring new GTM spend translates into efficient pipeline",
            "preferred_channels": ["email", "webinar"],
            "influence_score": 0.9,
        },
    ],
    "hiring_surge": [
        {
            "title": "VP of People",
            "role": BuyerRole.champion,
            "pain_level": PainLevel.high,
            "primary_pain": "Scaling onboarding and team workflows during rapid hiring",
            "preferred_channels": ["email", "linkedin"],
            "influence_score": 0.76,
        },
        {
            "title": "Head of Revenue Operations",
            "role": BuyerRole.technical_evaluator,
            "pain_level": PainLevel.high,
            "primary_pain": "Keeping GTM processes consistent as headcount grows",
            "preferred_channels": ["content", "webinar"],
            "influence_score": 0.72,
        },
        {
            "title": "COO",
            "role": BuyerRole.economic_buyer,
            "pain_level": PainLevel.medium,
            "primary_pain": "Preventing operating complexity from slowing expansion",
            "preferred_channels": ["email", "outbound_call"],
            "influence_score": 0.88,
        },
    ],
    "product_launch": [
        {
            "title": "VP of Marketing",
            "role": BuyerRole.champion,
            "pain_level": PainLevel.high,
            "primary_pain": "Converting launch attention into qualified pipeline",
            "preferred_channels": ["email", "content"],
            "influence_score": 0.8,
        },
        {
            "title": "Product Marketing Lead",
            "role": BuyerRole.end_user,
            "pain_level": PainLevel.high,
            "primary_pain": "Translating new positioning into segmented GTM plays",
            "preferred_channels": ["linkedin", "content"],
            "influence_score": 0.7,
        },
        {
            "title": "CRO",
            "role": BuyerRole.economic_buyer,
            "pain_level": PainLevel.medium,
            "primary_pain": "Making sure launch momentum becomes sales pipeline",
            "preferred_channels": ["email", "webinar"],
            "influence_score": 0.86,
        },
    ],
    "leadership_change": [
        {
            "title": "New Executive Sponsor",
            "role": BuyerRole.champion,
            "pain_level": PainLevel.high,
            "primary_pain": "Quickly auditing tools and resetting team priorities",
            "preferred_channels": ["email", "linkedin"],
            "influence_score": 0.84,
        },
        {
            "title": "Chief of Staff",
            "role": BuyerRole.technical_evaluator,
            "pain_level": PainLevel.medium,
            "primary_pain": "Operationalizing the new leader's first 90-day plan",
            "preferred_channels": ["email", "content"],
            "influence_score": 0.68,
        },
        {
            "title": "CFO",
            "role": BuyerRole.economic_buyer,
            "pain_level": PainLevel.medium,
            "primary_pain": "Evaluating spend changes under new leadership",
            "preferred_channels": ["email", "webinar"],
            "influence_score": 0.82,
        },
    ],
    "tech_install": [
        {
            "title": "Head of RevOps",
            "role": BuyerRole.champion,
            "pain_level": PainLevel.high,
            "primary_pain": "Making sure a new system fits the rest of the GTM stack",
            "preferred_channels": ["email", "content"],
            "influence_score": 0.78,
        },
        {
            "title": "IT Systems Owner",
            "role": BuyerRole.technical_evaluator,
            "pain_level": PainLevel.high,
            "primary_pain": "Managing integration, security, and data flow risk",
            "preferred_channels": ["content", "webinar"],
            "influence_score": 0.72,
        },
        {
            "title": "COO",
            "role": BuyerRole.economic_buyer,
            "pain_level": PainLevel.medium,
            "primary_pain": "Ensuring new tooling improves operating leverage",
            "preferred_channels": ["email", "outbound_call"],
            "influence_score": 0.84,
        },
    ],
    "employee_post": [
        {
            "title": "Public Post Author or Team Lead",
            "role": BuyerRole.champion,
            "pain_level": PainLevel.high,
            "primary_pain": "The public post reveals an active team priority that can become a warm outbound path",
            "preferred_channels": ["linkedin", "email"],
            "influence_score": 0.78,
        },
        {
            "title": "Functional VP",
            "role": BuyerRole.economic_buyer,
            "pain_level": PainLevel.medium,
            "primary_pain": "Turning the public initiative into measurable business impact",
            "preferred_channels": ["email", "outbound_call"],
            "influence_score": 0.82,
        },
        {
            "title": "RevOps or Operations Owner",
            "role": BuyerRole.technical_evaluator,
            "pain_level": PainLevel.medium,
            "primary_pain": "Making sure the new initiative fits existing GTM workflows and systems",
            "preferred_channels": ["content", "webinar"],
            "influence_score": 0.68,
        },
    ],
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
        templates = SIGNAL_ROLE_TEMPLATES.get(account.signal_type or "")
        if templates:
            for template in templates:
                members.append(
                    BuyerPersona(
                        name=f"Synthetic {template['title']}",
                        title=template["title"],
                        role=template["role"],
                        pain_level=template["pain_level"],
                        primary_pain=template["primary_pain"],
                        goals=[],
                        objections=[],
                        preferred_channels=template["preferred_channels"],
                        influence_score=template["influence_score"],
                    )
                )
            return BuyingCommittee(account_id=account.id, members=members)

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
Signal Type: {account.signal_type or 'unknown'}
Source Evidence: {account.signal_context or 'not provided'}

Important: the committee must reflect the signal. For funding, include revenue/growth owners.
For hiring, include operations/people/revops owners. For product launches, include marketing/product marketing/revenue.
For leadership changes, include the new executive, chief of staff, and budget owner.
For tech installs, include RevOps/IT/systems stakeholders.
For employee/public social posts, include the likely post author/team lead, the functional VP, and the operations owner.

Return a JSON array of 3-4 buyer personas. Each must have:
- name (synthetic/generic)
- title
- role (champion|economic_buyer|technical_evaluator|end_user|blocker)
- pain_level (low|medium|high|critical)
- primary_pain (string, specific to the source evidence)
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

        try:
            raw = message.content[0].text.strip()
            if "```" in raw:
                fenced = raw.split("```")
                raw = fenced[1] if len(fenced) > 1 else raw
                raw = raw.removeprefix("json").strip()

            # Extract the outermost JSON array if the model wrapped it in extra text.
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                raw = raw[start:end]

            data = json.loads(raw)
            members = [BuyerPersona(**p) for p in data]
            return BuyingCommittee(account_id=account.id, members=members, simulated=True)
        except (JSONDecodeError, ValueError, KeyError, TypeError):
            # Keep the pipeline stable during demos when model output is not strict JSON.
            return self.simulate(account)
