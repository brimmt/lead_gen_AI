# LeadSearch API (handoff)

Small FastAPI service that collects leads from compliant sources and returns a unified schema.

- ✅ **GPR (Georgia Procurement Registry)** — working via Playwright (public data)
- 🟨 **Reddit / YouTube / X / Instagram** — API-ready (BDG must add keys)
- 🧩 **Bermuda / LinkedIn** — existing routes (see their docs)

## Quick Start
```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt
playwright install chromium
uvicorn app:app --host 127.0.0.1 --port 8000



GPR
 — pulls agency, title, buyer contact (name, email, phone/ext), end date, plus raw metadata.

Reddit
 — API-ready search; captures author (username), subreddit, upvotes, etc.

YouTube
 — API-ready search; captures channel title (username-like), publishedAt, etc.

X (Twitter)
 — API-ready recent search; captures author username via expansions.

Instagram
 — Graph API placeholder (requires BDG FB App + permissions).

Bermuda
 — scrapes Bermuda hospitals/medical (contacts).

App / LinkedIn
 — LinkedIn via Google search (clients + media contact extraction).