# GET /leads/youtube

Search YouTube Data API v3.

## Setup

Restart the server.

## Query
- `q` *(required)*
- `published_after` *(ISO 8601, optional)*
- `max_results` *(default 25)*

## What it captures (default)
- `title`
- `metadata.channelTitle` *(channel display/username-like)*
- `metadata.channelId`
- `metadata.publishedAt`
- (optional) `metadata.description`, `metadata.thumbnails`

> Toggle fields in `routes/youtube.py` → `CAPTURE_FIELDS`.

## Compliance
API-only. No scraping.

## Example
GET /leads/youtube?q=hospital%20analytics&max_results=10