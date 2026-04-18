import httpx
from app.config import settings
from orchestrator.models import IncomingSignal, SignalType

APIFY_BASE = "https://api.apify.com/v2"
# Google News scraper — free, no extra cost on your plan
NEWS_ACTOR_ID = "apify/google-news-scraper"

SIGNAL_KEYWORDS = {
    "raised": SignalType.funding_round,
    "funding": SignalType.funding_round,
    "series": SignalType.funding_round,
    "hired": SignalType.leadership_change,
    "appointed": SignalType.leadership_change,
    "launches": SignalType.product_launch,
    "hiring": SignalType.hiring_surge,
    "headcount": SignalType.hiring_surge,
}


def _detect_signal_type(text: str) -> SignalType:
    lower = text.lower()
    for keyword, signal in SIGNAL_KEYWORDS.items():
        if keyword in lower:
            return signal
    return SignalType.funding_round


def _extract_amount(text: str) -> float | None:
    import re
    match = re.search(r"\$(\d+(?:\.\d+)?)\s*(M|B|million|billion)", text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    suffix = match.group(2).lower()
    return value * 1_000_000 if suffix in ("m", "million") else value * 1_000_000_000


def scrape_company_signals(company_name: str) -> list[IncomingSignal]:
    """Run the Apify Google News scraper for a company and return parsed signals."""
    headers = {"Authorization": f"Bearer {settings.apify_api_key}"}

    run_payload = {
        "queries": [f"{company_name} funding OR raised OR launch OR hiring 2024 2025"],
        "maxResultsPerQuery": 5,
        "languageCode": "en",
        "countryCode": "us",
    }

    # Start actor run
    run_resp = httpx.post(
        f"{APIFY_BASE}/acts/{NEWS_ACTOR_ID}/runs",
        json=run_payload,
        headers=headers,
        timeout=30,
    )
    run_resp.raise_for_status()
    run_id = run_resp.json()["data"]["id"]

    # Wait for run to finish (poll)
    import time
    for _ in range(12):
        status_resp = httpx.get(
            f"{APIFY_BASE}/actor-runs/{run_id}",
            headers=headers,
            timeout=10,
        )
        status = status_resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED"):
            raise RuntimeError(f"Apify run {run_id} failed with status: {status}")
        time.sleep(5)

    # Fetch results
    dataset_id = status_resp.json()["data"]["defaultDatasetId"]
    items_resp = httpx.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        headers=headers,
        params={"format": "json", "limit": 10},
        timeout=10,
    )
    items_resp.raise_for_status()
    items = items_resp.json()

    signals: list[IncomingSignal] = []
    for item in items:
        title = item.get("title", "")
        snippet = item.get("description", "") or item.get("snippet", "")
        text = f"{title} {snippet}"

        signals.append(
            IncomingSignal(
                company_name=company_name,
                signal_type=_detect_signal_type(text),
                amount=_extract_amount(text),
                description=text.strip(),
                source_url=item.get("url"),
            )
        )

    return signals
