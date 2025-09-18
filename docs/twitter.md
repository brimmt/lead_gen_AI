# GET /leads/x

Search recent posts on X (Twitter) v2.

## Setup

Update X_BEARER_TOKEN=your_bearer_token in .env file

Restart the server.

## Query
- `q` *(required)*
- `max_results` *(default 10, max 100)*

## What it captures (default)
- `title` (first 120 chars of text)
- `metadata.text`
- `metadata.created_at`
- `metadata.author_id`
- `metadata.username` *(via expansions)*

> Toggle fields in `routes/twitter_x.py` → `CAPTURE_FIELDS`.

## Compliance
API-only. No scraping.

## Example
GET /leads/x?q=medtech%20rfp&max_results=20