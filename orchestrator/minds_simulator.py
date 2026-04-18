import httpx
import json
from app.config import settings
from app.models.account import Account
from app.models.buyer import BuyerPersona, BuyingCommittee, BuyerRole, PainLevel

MINDS_BASE = settings.minds_ai_base_url or "https://mdb.ai/api/v1"

ROLES = [
    {"role": "champion", "title": "VP of Operations"},
    {"role": "economic_buyer", "title": "CFO"},
    {"role": "technical_evaluator", "title": "Head of Engineering"},
]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.minds_ai_api_key}",
        "Content-Type": "application/json",
    }


def _simulate_persona(account: Account, role: str, title: str) -> BuyerPersona:
    """Use Minds AI to generate a realistic buyer persona via OpenAI-compatible chat."""
    prompt = f"""You are a {title} at {account.name}, a {account.industry} company with {account.employee_count} employees.
A vendor is trying to sell you a GTM automation platform. Respond as this buyer persona.

Return a JSON object with exactly these fields:
- primary_pain (string: your #1 business pain right now)
- goals (list of 2 strings: what you want to achieve this quarter)
- objections (list of 2 strings: your biggest objections to buying this tool)
- preferred_channels (list of 2 from: email, linkedin, content, webinar, outbound_call)
- influence_score (float 0.0-1.0: how much you influence the final purchase decision)
- pain_level (one of: low, medium, high, critical)

Respond with only valid JSON."""

    resp = httpx.post(
        f"{MINDS_BASE}/chat/completions",
        headers=_headers(),
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400,
            "temperature": 0.7,
        },
        timeout=30,
    )
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    return BuyerPersona(
        name=f"Synthetic {title}",
        title=title,
        role=BuyerRole(role),
        pain_level=PainLevel(data.get("pain_level", "medium")),
        primary_pain=data["primary_pain"],
        goals=data.get("goals", []),
        objections=data.get("objections", []),
        preferred_channels=data.get("preferred_channels", ["email"]),
        influence_score=float(data.get("influence_score", 0.5)),
    )


def simulate_committee_minds(account: Account) -> BuyingCommittee:
    """
    Use Minds AI to generate a realistic, industry-calibrated buying committee.
    Each persona is independently simulated as a live AI agent.
    """
    members: list[BuyerPersona] = []
    for r in ROLES:
        try:
            persona = _simulate_persona(account, r["role"], r["title"])
            members.append(persona)
        except Exception:
            # Fall back to a basic persona if one call fails
            members.append(BuyerPersona(
                name=f"Synthetic {r['title']}",
                title=r["title"],
                role=BuyerRole(r["role"]),
                pain_level=PainLevel.medium,
                primary_pain="Operational efficiency",
                goals=["Reduce manual work", "Improve pipeline visibility"],
                objections=["Budget constraints", "Integration complexity"],
                preferred_channels=["email", "linkedin"],
                influence_score=0.6,
            ))

    return BuyingCommittee(account_id=account.id, members=members, simulated=True)
