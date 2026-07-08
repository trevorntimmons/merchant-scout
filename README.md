# MerchantScout

MerchantScout finds local merchants, estimates how much of a payment-processing/POS opportunity each one is, and ranks them so a sales rep knows exactly who to call or visit first — and why.

Built for two audiences off the same underlying data:

- **BDR/SDR view** — a sortable call list with score, contact info, estimated TPV, and a suggested pitch angle.
- **Field rep view** — the same prospects on a map, with a downloadable route file for door-to-door canvassing.

## How it works

1. Pick a vertical (restaurants, retail, salons & spas, auto repair, professional services, or a generic fallback) and a location.
2. MerchantScout searches Google Places for matching businesses in that area.
3. For each one, it estimates annual revenue and monthly TPV (total payment volume) using vertical-specific assumptions, flags pain/opportunity signals from public data, and scores the merchant 1-100 on **how urgent an opportunity it is** — not how big the business is. TPV is shown as its own column so you can weigh deal size yourself.
4. Every score comes with a plain-English breakdown of what drove it, plus a recommended acquisition angle.

## Quickstart

```bash
git clone <this repo>
cd merchant-scout
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GOOGLE_PLACES_API_KEY
streamlit run app.py
```

You need a [Google Places API (New)](https://developers.google.com/maps/documentation/places/web-service/op-overview) key with Places API enabled and billing turned on. An optional `ANTHROPIC_API_KEY` upgrades the templated pitch angle into a natural-language write-up per prospect — the tool works fine without it.

## The TPV formula

```
estimated annual revenue  (vertical + review-volume benchmark, adjusted by rating)
  × % of revenue that's card-based   (vertical-specific)
  ÷ 12
  = estimated monthly TPV
```

Each vertical config (`verticals/*.json`) sets its own average ticket size, card-payment %, and revenue benchmark brackets. Add a new vertical by dropping in a new JSON file with the same shape — no code changes needed.

Revenue/TPV numbers are estimates, not fact — each one is shown with a **High/Medium/Low confidence** label based on how much public signal (review volume, rating, price level) backs it. Treat these as prioritization signals, not a quote you'd give a merchant.

## Scoring signals (v1)

| Signal | Points | Note |
|---|---|---|
| New business (< 12 months) | +25 | Strongest buying-intent signal in this industry — still shopping for a processor |
| No website found | +20 | Likely no online ordering/payment presence |
| Reviews mention payment/checkout friction | up to +20 | Keyword-matched per vertical |
| Competitor POS/processor named in reviews | +10 | A conversation starter, not confirmed contract info |
| Below-average rating + meaningful review volume | +10 | Operational friction proxy |

The score measures need/opportunity, not deal size — it's what decides call order. "Current processor" signals are always conversation-starters, not confirmed facts: public data can't tell you if a merchant is locked into a contract. Confirm that on the call or in person.

## New-business detection

The strongest signal in this list needs the weakest public data. Two sources, both best-effort:

1. Drop a CSV export from your state's open-data new-business-filings portal into `data/new_business_registry.csv` (columns: `business_name,zip,registration_date`).
2. If no registry match is found, MerchantScout falls back to the earliest Google review date as a rough "active since" proxy (flagged low-confidence in the explanation text).

To wire in a live state API instead of a manual CSV, implement a new `lookup()` function in `core/new_business.py` and swap it into the pipeline in `app.py`.

## Suppression list

Mark a prospect "contacted" in the BDR/SDR view and it's written to `data/exclude_list.csv` — it won't resurface on future runs. Delete a row to un-suppress it, or share the file across a team to avoid double-working the same merchant.

## Cost and caching

Each run calls the Places API (New) `searchText` endpoint once per Google place type in the chosen vertical; the response already includes reviews, phone, website, and rating in one call rather than a separate Details call. Results are cached locally in `.cache/` (default 24h TTL, configurable via `CACHE_TTL_HOURS`) so re-running the same search doesn't re-bill you. Check [current Places API pricing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing) before running large batches.

## Compliance notes

- Phone/email outreach to businesses is generally not subject to the National DNC Registry or TCPA, which primarily cover residential/consumer numbers — but state-level B2B calling rules vary, so check your state's rules before a large campaign. This isn't legal advice; check with counsel if you're scaling this up.
- Email discovery only reads a business's own public homepage/contact page, checks `robots.txt` first, and identifies itself via a descriptive User-Agent. It doesn't scrape third-party sites or personal profiles.
- This tool surfaces publicly available business information for legitimate B2B sales outreach. You're responsible for how you use it.

## Project structure

```
app.py                  Streamlit UI (BDR/SDR view + Field Rep view)
core/
  config.py             .env loading
  vertical_configs.py   loads verticals/*.json
  places_client.py      Google Places API (New) client + local cache
  tpv.py                revenue + TPV estimation
  scoring.py            1-100 need score + explanation
  angle.py              rule-based acquisition angle
  llm_writer.py         optional Claude write-up (falls back to angle.py)
  email_scraper.py      best-effort contact email discovery
  new_business.py       new-business signal (registry CSV + review-date proxy)
  exclude_list.py       suppression list
  geo_export.py         KML export for route planning
verticals/*.json        per-vertical scoring/TPV assumptions
data/*.csv              exclude list + new-business registry (user-supplied)
tests/                  pytest unit tests for tpv.py and scoring.py
```

## Roadmap ideas

- Live state new-business-registry API adapters (beyond the manual CSV)
- Team-level dedup so multiple reps don't double-work the same merchant
- Pluggable enrichment adapters (Apollo/Clay/ZoomInfo) for higher email/firmographic confidence

## License

MIT — see `LICENSE`.
