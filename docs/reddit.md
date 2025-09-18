# GET /leads/reddit

Search Reddit via OAuth (application-only).

## Setup
Add credentials to `.env`:

Restart the server.

## Query
- `q` *(required)* — search string
- `subreddit` *(optional)*
- `limit` *(optional, default 25)*

## What it captures (default)
- `title`
- `metadata.author` *(username)*
- `metadata.subreddit`
- `metadata.ups`
- `metadata.num_comments`
- `metadata.created_utc`
- `metadata.permalink`

> **Customize captured fields:** open `routes/reddit.py` and toggle the `CAPTURE_FIELDS` dict.

## Compliance
API-only. No scraping.


## Example
GET /leads/reddit?q=hospital%20analytics&subreddit=dataengineering&limit=10