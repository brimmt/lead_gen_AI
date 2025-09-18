# GET /leads/bermuda

Scrapes Bermuda Yellow Pages (healthcare / hospital listings) to collect contact info.

## Setup
No API keys required.  
Runs directly against public BermudaYP search pages.

## Query
- `category` *(required)* — e.g. `insurance`, `hospital`, `medical`
- `page` *(optional)* — defaults to 1

## What it captures
- `name` — business/organization
- `url` — source URL
- `metadata`:
  - `phone`
  - `email` (if present)
  - `address`
  - `website`

## Example

GET /leads/bermuda?category=hospital&page=1

## Response (trimmed)
```json
{
  "ok": true,
  "count": 18,
  "items": [
    {
      "source": "bermuda",
      "external_id": "bermudayp:St-Georges-Hospital",
      "title": "St. George's Hospital",
      "url": "https://www.bermudayp.com/search/all/1/hospital",
      "metadata": {
        "phone": "+1 441-123-4567",
        "email": "info@stgeorgeshospital.bm",
        "address": "123 Harbour Road, St. George's",
        "website": "https://stgeorgeshospital.bm"
      },
      "discovered_at": "2025-09-05T16:45:09Z"
    }
  ]
}


Notes

Public data, no login required.

Query runs one BermudaYP search results page at a time.

Keep frequency low (1–2 runs/week) to avoid IP blocks.