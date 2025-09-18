## Setup  Add your APIkey(s) to .env, restart the server. Example:
#X_BEARER_TOKEN=your_bdg_api_key

from fastapi import APIRouter, HTTPException, Query
import httpx, os
from datetime import datetime

router = APIRouter(prefix="/leads/x", tags=["x"])

# ==== EDIT HERE: choose which fields to capture ====
CAPTURE_FIELDS = {
    "text": True,
    "created_at": True,
    "author_id": True,
    "username": True,      # we’ll request expansions to get author username
}
# ===================================================

def _pick(tweet: dict, users_by_id: dict) -> dict:
    m = {}
    if CAPTURE_FIELDS.get("text"):        m["text"] = tweet.get("text")
    if CAPTURE_FIELDS.get("created_at"):  m["created_at"] = tweet.get("created_at")
    if CAPTURE_FIELDS.get("author_id"):
        aid = tweet.get("author_id")
        m["author_id"] = aid
        if CAPTURE_FIELDS.get("username") and aid and aid in users_by_id:
            m["username"] = users_by_id[aid].get("username")
    return m

@router.get("")
async def x_search(q: str = Query(..., min_length=2), max_results: int = 10):
    bearer = os.getenv("X_BEARER_TOKEN")  #Enter your API here within the ""
    if not bearer:
        raise HTTPException(501, "X API bearer token not configured. See README.")
    headers = {"Authorization": f"Bearer {bearer}"}
    params = {
        "query": q,
        "max_results": max(10, min(max_results, 100)),
        "tweet.fields": "created_at,author_id",
        "expansions": "author_id",
        "user.fields": "username,name"
    }
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        r = await client.get("https://api.twitter.com/2/tweets/search/recent", params=params)
        r.raise_for_status()
        data = r.json()

    users_by_id = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    items = []
    for t in data.get("data", []):
        tid = t["id"]
        items.append({
            "source": "x",
            "external_id": tid,
            "title": t.get("text", "")[:120],
            "url": f"https://x.com/i/web/status/{tid}",
            "metadata": _pick(t, users_by_id),  # <= EDIT CAPTURE_FIELDS above
            "discovered_at": datetime.utcnow().isoformat()
        })
    return {"ok": True, "count": len(items), "items": items}