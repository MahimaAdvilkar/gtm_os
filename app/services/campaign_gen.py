from app.models.account import Account, AccountScore
from app.models.buyer import BuyingCommittee
from app.models.campaign import CampaignStrategy, CampaignTactic, CampaignChannel
from app.config import settings
import anthropic
import json


class CampaignGenerator:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def generate(
        self,
        account: Account,
        score: AccountScore,
        committee: BuyingCommittee,
    ) -> CampaignStrategy:
        """Generate a rule-based campaign strategy."""
        tactics: list[CampaignTactic] = []

        for member in committee.members:
            for channel_name in member.preferred_channels[:2]:
                try:
                    channel = CampaignChannel(channel_name)
                except ValueError:
                    continue
                tactics.append(
                    CampaignTactic(
                        channel=channel,
                        message=f"Address {member.primary_pain} for {member.title}",
                        cta="Book a 20-min discovery call",
                        target_persona=member.title,
                        priority=1 if member.influence_score >= 0.7 else 2,
                    )
                )

        sequence_days = 30 if score.tier == "A" else 45 if score.tier == "B" else 60

        return CampaignStrategy(
            account_id=account.id,
            objective=f"Move {account.name} from awareness to evaluation in {sequence_days} days",
            tactics=tactics,
            sequence_days=sequence_days,
        )

    def generate_with_ai(
        self,
        account: Account,
        score: AccountScore,
        committee: BuyingCommittee,
    ) -> CampaignStrategy:
        """Use Claude to generate a tailored, multi-touch campaign strategy."""
        personas_summary = "\n".join(
            f"- {m.title} ({m.role}): pain='{m.primary_pain}', channels={m.preferred_channels}"
            for m in committee.members
        )

        prompt = f"""You are a GTM strategist. Design a multi-touch campaign strategy.

Account: {account.name} | Industry: {account.industry} | Tier: {score.tier} (score={score.composite_score})
Tech Stack: {', '.join(account.tech_stack) or 'unknown'}

Buying Committee:
{personas_summary}

Return a JSON object with:
- objective (string)
- sequence_days (int)
- estimated_pipeline (float, USD)
- notes (string)
- tactics (array of objects with: channel, message, cta, target_persona, priority 1-5)
  channel must be one of: email, linkedin, paid_search, content, outbound_call, webinar, direct_mail

Respond with only valid JSON."""

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

        tactics = [CampaignTactic(**t) for t in data.pop("tactics", [])]
        return CampaignStrategy(account_id=account.id, tactics=tactics, **data)
