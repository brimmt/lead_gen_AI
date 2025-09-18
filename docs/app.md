# (LinkedIn via Google Search scrape)

# GET /leads/app

Scrapes Google Search results for LinkedIn pages to extract clients and media contacts.

## Setup
No API keys required.  
Runs against Google Search + LinkedIn public profile snippets.

## Query
- `q` *(required)* — search string (e.g. `site:linkedin.com hospital Atlanta contacts`)
- `limit` *(optional)* — number of results to fetch (default 10)

## What it captures
- `title` — page title
- `url` — LinkedIn or site URL
- `metadata`:
  - `snippet` (Google search snippet)
  - `source` (e.g. “linkedin” or “media site”)

## Example
GET /leads/app?q=site:linkedin.com%20hospital%20Atlanta%20contacts&limit=5

## Response (trimmed)
```json
{
  "ok": true,
  "count": 5,
  "items": [
    {
      "source": "app",
      "external_id": "linkedin:john-doe-12345",
      "title": "John Doe – Marketing Director at XYZ Hospital",
      "url": "https://www.linkedin.com/in/john-doe-12345",
      "metadata": {
        "snippet": "Experienced Director of Marketing with a focus on healthcare..."
      },
      "discovered_at": "2025-09-05T16:45:09Z"
    }
  ]
}


** Notes

This uses Google Search scraping → results may vary depending on captchas and rate limits.

Only pulls snippets/URLs; no full LinkedIn scraping (keeps it ToS-safe).

Designed for quick client/media contact discovery.