## Setup  Add your APIkey(s) to .env, restart the server. Example:
#REDDIT_CLIENT_ID=your_bdg_api_key

from fastapi import APIRouter, HTTPException, Query
import httpx, os
from datetime import datetime

router = APIRouter(prefix="/leads/reddit", tags=["reddit"])

# ==== EDIT HERE: choose which fields to capture ====
CAPTURE_FIELDS = {
    "title": True,
    "author": True,         # reddit username
    "subreddit": True,
    "ups": True,
    "num_comments": True,
    "created_utc": True,
    "permalink": True,
    "selftext": False,      # set True if you want the body text (bigger payloads)
}
# ===================================================

def _pick(post: dict) -> dict:
    m = {}
    if CAPTURE_FIELDS.get("author"):        m["author"] = post.get("author")
    if CAPTURE_FIELDS.get("subreddit"):     m["subreddit"] = post.get("subreddit")
    if CAPTURE_FIELDS.get("ups"):           m["ups"] = post.get("ups")
    if CAPTURE_FIELDS.get("num_comments"):  m["num_comments"] = post.get("num_comments")
    if CAPTURE_FIELDS.get("created_utc"):   m["created_utc"] = post.get("created_utc")
    if CAPTURE_FIELDS.get("permalink"):     m["permalink"] = post.get("permalink")
    if CAPTURE_FIELDS.get("selftext"):      m["selftext"] = post.get("selftext")
    return m

@router.get("")
async def reddit_search(q: str = Query(..., min_length=2),
                        subreddit: str | None = None,
                        limit: int = 25):
    cid = os.getenv("REDDIT_CLIENT_ID")  #Enter your Client_ID & Client Secret within the ""
    csec = os.getenv("REDDIT_CLIENT_SECRET")
    ua = os.getenv("REDDIT_USER_AGENT", "leadsearch/1.0 by BDG")
    if not (cid and csec):
        raise HTTPException(501, "Reddit API credentials not configured. See README.")

    async with httpx.AsyncClient(timeout=20) as client:
        tok = await client.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(cid, csec),
            headers={"User-Agent": ua},
        )
        tok.raise_for_status()
        access = tok.json()["access_token"]

        headers = {"Authorization": f"Bearer {access}", "User-Agent": ua}
        params = {"q": q, "limit": limit, "sort": "new", "t": "month", "type": "link"}
        url = f"https://oauth.reddit.com/r/{subreddit}/search" if subreddit else "https://oauth.reddit.com/search"
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()

    items = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        items.append({
            "source": "reddit",
            "external_id": d.get("id"),
            "title": d.get("title", "") if CAPTURE_FIELDS.get("title") else "",
            "url": f"https://www.reddit.com{d.get('permalink','')}",
            "metadata": _pick(d),            # <= EDIT CAPTURE_FIELDS above
            "discovered_at": datetime.utcnow().isoformat()
        })
    return {"ok": True, "count": len(items), "items": items}