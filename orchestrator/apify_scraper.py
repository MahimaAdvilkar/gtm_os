from __future__ import annotations

from datetime import date, timedelta
import re
from urllib.parse import urlparse

import httpx

from app.config import settings
from orchestrator.models import IncomingSignal, SignalType

APIFY_BASE = "https://api.apify.com/v2"
SEARCH_ACTOR_ID = "apify~google-search-scraper"

SIGNAL_QUERIES = {
    SignalType.funding_round: [
        '{company} raised funding',
        '{company} series a OR series b OR funding round',
        '{company} funding round',
    ],
    SignalType.hiring_surge: [
        '{company} hiring',
        '{company} jobs',
        '{company} careers growth',
    ],
    SignalType.product_launch: [
        '{company} product launch',
        '{company} announced new product',
    ],
    SignalType.leadership_change: [
        '{company} new chief OR appointed OR hired executive',
    ],
    SignalType.tech_install: [
        '{company} adopted platform OR migrated OR implemented',
    ],
    SignalType.employee_post: [
        'site:linkedin.com/posts {company} hiring funding launch',
        'site:linkedin.com/posts {company} "we are hiring"',
        'site:linkedin.com/posts {company} "raised"',
    ],
}

SIGNAL_KEYWORDS = {
    "raised": SignalType.funding_round,
    "funding": SignalType.funding_round,
    "series": SignalType.funding_round,
    "seed": SignalType.funding_round,
    "hiring": SignalType.hiring_surge,
    "headcount": SignalType.hiring_surge,
    "careers": SignalType.hiring_surge,
    "jobs": SignalType.hiring_surge,
    "launch": SignalType.product_launch,
    "released": SignalType.product_launch,
    "announced": SignalType.product_launch,
    "appointed": SignalType.leadership_change,
    "hired": SignalType.leadership_change,
    "chief": SignalType.leadership_change,
    "migrated": SignalType.tech_install,
    "implemented": SignalType.tech_install,
    "adopted": SignalType.tech_install,
    "linkedin": SignalType.employee_post,
    "posted": SignalType.employee_post,
    "we are hiring": SignalType.employee_post,
    "we're hiring": SignalType.employee_post,
    "proud to announce": SignalType.employee_post,
}

TRUSTED_SIGNAL_DOMAINS = {
    "techcrunch.com",
    "crunchbase.com",
    "businesswire.com",
    "prnewswire.com",
    "globenewswire.com",
    "venturebeat.com",
    "siliconangle.com",
    "finextra.com",
    "sifted.eu",
    "eu-startups.com",
    "theinformation.com",
    "forbes.com",
    "reuters.com",
}

NOISY_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "reddit.com",
    "youtube.com",
    "tiktok.com",
}

SOCIAL_SIGNAL_DOMAINS = {
    "linkedin.com",
}

NOISY_TITLE_PATTERNS = (
    "list of",
    "best ",
    "where can i",
    "how to",
    "consultations are available",
    "competing with",
    "signal intelligence",
)


def _detect_signal_type(text: str) -> SignalType | None:
    lower = text.lower()
    for keyword, signal in SIGNAL_KEYWORDS.items():
        if keyword in lower:
            return signal
    return None


def _extract_amount(text: str) -> float | None:
    match = re.search(r"\$(\d+(?:\.\d+)?)\s*(M|B|million|billion)", text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    suffix = match.group(2).lower()
    return value * 1_000_000 if suffix in ("m", "million") else value * 1_000_000_000


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.apify_api_key}"}


def _run_google_search(queries: list[str], after_date: str | None = None) -> list[dict]:
    payload = {
        "queries": "\n".join(queries),
        "countryCode": "us",
        "languageCode": "en",
        "searchLanguage": "en",
        "maxPagesPerQuery": 1,
        "resultsPerPage": 5,
        "mobileResults": False,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["GOOGLE_SERP"],
        },
    }
    if after_date:
        payload["afterDate"] = after_date
    response = httpx.post(
        f"{APIFY_BASE}/acts/{SEARCH_ACTOR_ID}/run-sync-get-dataset-items",
        params={"token": settings.apify_api_key},
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def _dedupe_signals(signals: list[IncomingSignal]) -> list[IncomingSignal]:
    seen: set[str] = set()
    deduped: list[IncomingSignal] = []
    for signal in signals:
        key = signal.source_url or signal.description or f"{signal.company_name}:{signal.signal_type}:{signal.source_query}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(signal)
    return deduped


def _has_verifiable_source(signal: IncomingSignal) -> bool:
    return bool(signal.source_url and signal.description)


def _normalize_item(item: dict) -> tuple[str, str, str | None]:
    title = item.get("title") or ""
    snippet = item.get("snippet") or item.get("description") or ""
    link = item.get("url") or item.get("link")
    return title.strip(), snippet.strip(), link


def _domain(url: str | None) -> str:
    if not url:
        return ""
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _extract_public_author(title: str, snippet: str, link: str | None) -> tuple[str | None, str | None]:
    if "linkedin.com" not in _domain(link):
        return None, None

    text = f"{title} {snippet}".strip()
    match = re.search(r"^([A-Z][A-Za-z .'-]{2,80})\s+on LinkedIn", text)
    if match:
        return match.group(1).strip(), None

    match = re.search(r"^([A-Z][A-Za-z .'-]{2,80})\s+-\s+([^|]{2,80})\s+\|?\s*LinkedIn", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return None, None


def _is_trusted_or_specific(title: str, snippet: str, link: str | None, signal_type: SignalType) -> bool:
    text = f"{title} {snippet}".lower()
    domain = _domain(link)
    if domain in NOISY_DOMAINS:
        return False
    if signal_type == SignalType.employee_post and domain in SOCIAL_SIGNAL_DOMAINS:
        return True
    if any(pattern in text for pattern in NOISY_TITLE_PATTERNS):
        return False
    if domain in TRUSTED_SIGNAL_DOMAINS:
        return True
    return bool(_extract_amount(text)) or any(
        phrase in text
        for phrase in (
            "raised $",
            "raises $",
            "secured $",
            "secures $",
            "series a",
            "series b",
            "series c",
            "seed round",
            "funding round",
        )
    )


def _iter_search_results(items: list[dict]) -> list[dict]:
    flattened: list[dict] = []
    for item in items:
        organic_results = item.get("organicResults")
        if isinstance(organic_results, list) and organic_results:
            query_meta = item.get("searchQuery", {})
            query_value = query_meta.get("term") or query_meta.get("query")
            for result in organic_results:
                flattened.append(
                    {
                        "title": result.get("title", ""),
                        "snippet": result.get("description") or result.get("snippet") or "",
                        "link": result.get("url") or result.get("link"),
                        "searchQuery": {"term": query_value},
                    }
                )
            continue
        flattened.append(item)
    return flattened


def _build_signal_from_item(
    company_name: str,
    query: str,
    item: dict,
    hinted_signal: SignalType,
) -> IncomingSignal | None:
    title, snippet, link = _normalize_item(item)
    text = f"{title} {snippet}".strip()
    if not text:
        return None

    signal_type = _detect_signal_type(text) or hinted_signal
    author, author_role = _extract_public_author(title, snippet, link)
    return IncomingSignal(
        company_name=company_name,
        signal_type=signal_type,
        amount=_extract_amount(text),
        description=text,
        source_url=link,
        source_query=query,
        source_author=author,
        source_author_role=author_role,
    )


def scrape_company_signals(
    company_name: str,
    preferred_signal: SignalType | None = None,
) -> list[IncomingSignal]:
    query_map = (
        {preferred_signal: SIGNAL_QUERIES.get(preferred_signal, [])}
        if preferred_signal else SIGNAL_QUERIES
    )

    signals: list[IncomingSignal] = []
    for hinted_signal, templates in query_map.items():
        queries = [templates[0].format(company=company_name)] if templates else []
        if not queries:
            continue
        items = _iter_search_results(_run_google_search(queries))
        for item in items:
            query = item.get("searchQuery", {}).get("term") or item.get("searchQuery", {}).get("query") or queries[0]
            signal = _build_signal_from_item(company_name, query, item, hinted_signal)
            if signal:
                signals.append(signal)

    deduped = _dedupe_signals(signals)
    verified = [signal for signal in deduped if _has_verifiable_source(signal)]
    return sorted(
        verified,
        key=lambda s: (
            0 if preferred_signal and s.signal_type == preferred_signal else 1,
            0 if s.amount else 1,
            0 if _domain(s.source_url) in TRUSTED_SIGNAL_DOMAINS else 1,
        ),
    )


def _extract_company_name(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", text).strip()
    explicit_match = re.search(
        r"^([A-Z][A-Za-z0-9&.\- ]{1,70}?)\s+(?:has\s+)?(?:raised|raises|secured|secures|lands|closed|closes|announces|announced)\b",
        cleaned,
    )
    if explicit_match:
        return explicit_match.group(1).strip(" -:|,")
    for separator in (" raises ", " raised ", " hiring ", " launches ", " launch ", " appoints ", " appointed ", " hires ", " hired "):
        if separator in cleaned.lower():
            idx = cleaned.lower().find(separator)
            candidate = cleaned[:idx].strip(" -:|,")
            if 2 <= len(candidate) <= 80:
                return candidate
    candidate = cleaned.split(" | ")[0].split(" - ")[0].split(":")[0].strip(" ,")
    return candidate if 2 <= len(candidate) <= 80 else None


def scan_market_leads(
    signal_type: SignalType,
    days_back: int = 30,
    focus: str = "B2B SaaS",
) -> list[IncomingSignal]:
    since = (date.today() - timedelta(days=days_back)).isoformat()
    signal_term = {
        SignalType.funding_round: "raised funding",
        SignalType.hiring_surge: "hiring jobs careers",
        SignalType.product_launch: "product launch announced",
        SignalType.leadership_change: "appointed hired executive",
        SignalType.tech_install: "adopted implemented migrated",
        SignalType.employee_post: "linkedin post hiring funding launch",
    }[signal_type]

    if signal_type == SignalType.employee_post:
        queries = [
            f'site:linkedin.com/posts "{focus}" "we are hiring"',
            f'site:linkedin.com/posts "{focus}" "raised"',
            f'site:linkedin.com/posts "{focus}" "launch"',
        ]
    else:
        queries = [
            f'site:techcrunch.com "{signal_term}" startup',
            f'site:businesswire.com "{signal_term}" startup',
            f'site:prnewswire.com "{signal_term}" startup',
            f'"{signal_term}" startup "{focus}"',
        ]

    items = _iter_search_results(_run_google_search(queries, after_date=since))
    leads: list[IncomingSignal] = []
    for item in items:
        title, snippet, link = _normalize_item(item)
        text = f"{title} {snippet}".strip()
        if not text:
            continue
        if not _is_trusted_or_specific(title, snippet, link, signal_type):
            continue
        company_name = _extract_company_name(title) or _extract_company_name(snippet) or "Unknown company"
        if company_name.lower().startswith(("list ", "most ", "best ", "where ")):
            continue
        query = item.get("searchQuery", {}).get("term") or item.get("searchQuery", {}).get("query") or queries[0]
        author, author_role = _extract_public_author(title, snippet, link)
        leads.append(
            IncomingSignal(
                company_name=company_name,
                signal_type=_detect_signal_type(text) or signal_type,
                amount=_extract_amount(text),
                description=text,
                source_url=link,
                source_query=query,
                source_author=author,
                source_author_role=author_role,
            )
        )

    return sorted(
        _dedupe_signals(leads),
        key=lambda lead: (
            0 if lead.amount else 1,
            0 if _domain(lead.source_url) in TRUSTED_SIGNAL_DOMAINS else 1,
            lead.company_name,
        ),
    )
