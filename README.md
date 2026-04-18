# GTM OS

GTM OS is a signal-to-pipeline engine for revenue teams.

It turns real market signals such as funding rounds, hiring surges, product launches, leadership changes, and public employee posts into CRM-ready sales opportunities with source evidence, account scoring, a buying committee hypothesis, and a first outbound motion.

The core idea is simple:

```text
live market signal -> GTM reasoning -> account strategy -> HubSpot opportunity
```

Most GTM teams lose time between discovering a good account and actually acting on it. GTM OS compresses that workflow from manual research into a few seconds, then pushes the result into the system of record where sales teams already work.

## What It Does

GTM OS helps a rep answer four questions quickly:

1. Why is this account relevant right now?
2. Is this account worth working?
3. Who is likely involved in the buying decision?
4. What should the rep do first?

The system currently supports two operating modes:

- **Run one account**: enter a company name and signal type, then generate a source-backed GTM plan.
- **Scan the market**: search recent live web results for companies matching a signal, such as B2B SaaS companies that recently raised funding.

## Why This Is Different

This is not just an email generator or chatbot.

GTM OS closes the loop:

```text
Detect signal
Score account
Generate buying committee
Write GTM motion
Create HubSpot company + deal
Attach CRM notes with evidence and next steps
```

That last step matters because if the insight never reaches the CRM, it usually does not become sales action.

## Demo Story

Use this framing:

> We built a GTM OS that turns real-world signals like funding, hiring, and public company activity into CRM-ready sales opportunities. It finds the signal, explains why the account matters now, creates a buying committee hypothesis, writes the first outbound motion, and pushes everything into HubSpot so a rep can act immediately.

Recommended demo:

1. Open the local app at `http://127.0.0.1:8000/`.
2. Run a company such as `Anysphere`.
3. Select `Funding Round`.
4. Turn on `Use Live Apify Signals`.
5. Turn on `Push to HubSpot`.
6. Click `Run Pipeline`.
7. Show the GTM plan in the frontend.
8. Click `View in HubSpot`.
9. Show the company/deal and the attached GTM OS notes.

In HubSpot, the judge should see:

- Signal evidence and source URL.
- Why now.
- Why this account.
- Buying committee hypothesis.
- First outreach motion.
- Warm path candidates when found.

## Architecture

```text
Frontend
  FastAPI static UI

Signal Layer
  Apify Google Search crawler
  Market scan
  Company-specific signal lookup

Reasoning Layer
  Account scoring
  Signal-aware buying committee generation
  Persona-specific campaign strategy

Execution Layer
  HubSpot company creation/update
  HubSpot deal creation
  HubSpot CRM notes for evidence, committee, and next action
```

## Tech Stack

- Python
- FastAPI
- Pydantic
- Apify
- Anthropic Claude
- HubSpot CRM API
- HTML/CSS/JavaScript frontend

## Project Structure

```text
app/
  main.py                  FastAPI application entry point
  static/index.html        Local demo frontend
  api/routes/              API routes
  models/                  Pydantic domain models
  services/                Account scoring, committee, campaign, outcomes

orchestrator/
  apify_scraper.py         Live signal discovery through Apify
  signal_router.py         Signal -> scored GTM plan
  pipeline.py              End-to-end pipeline orchestration
  hubspot_push.py          HubSpot company, deal, and CRM notes
  models.py                Signal, GTM plan, and market lead models

tests/
  Unit tests for core services
```

## Setup

Create a local environment file:

```bash
cp .env.example .env
```

Add local keys to `.env`:

```text
ANTHROPIC_API_KEY=...
APIFY_API_KEY=...
HUBSPOT_API_KEY=...
HUBSPOT_PORTAL_ID=...
```

Important: `.env` is ignored by git and must not be committed.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

## API Examples

Run one company with live signal lookup:

```bash
curl -X POST "http://127.0.0.1:8000/webhook/run?push_to_hubspot=false" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Anysphere","preferred_signal":"funding_round"}'
```

Push the result to HubSpot:

```bash
curl -X POST "http://127.0.0.1:8000/webhook/run?push_to_hubspot=true" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Anysphere","preferred_signal":"funding_round"}'
```

Scan the market for recent leads:

```bash
curl -X POST "http://127.0.0.1:8000/webhook/market-scan" \
  -H "Content-Type: application/json" \
  -d '{"signal_type":"funding_round","days_back":30,"focus":"B2B SaaS"}'
```

## Authenticity Notes

GTM OS distinguishes between source-backed evidence and AI-generated hypotheses.

- Live signals come from Apify-powered web search results.
- Source URLs are preserved and shown in the frontend and HubSpot.
- Buying committees are clearly treated as hypotheses to accelerate first-pass planning.
- Public authors or LinkedIn-style warm paths are treated as candidates, not verified contacts.
- Contacts should only be created after identity and email verification.

This keeps the product useful without pretending scraped data is more certain than it is.

## Current Limitations

- Firmographic data such as employee count and revenue is estimated unless a data provider is connected.
- Buying committee members are generated hypotheses, not guaranteed real people.
- Warm path candidates require verification before outreach.
- Apify search quality depends on the source results available for a query.

## Future Work

- Add Crunchbase or another firmographic provider for verified funding and company data.
- Add email/contact enrichment for verified contact creation.
- Add deduplication across repeated signals.
- Add feedback from HubSpot outcomes to improve scoring.
- Add lead scoring by source credibility and recency.

