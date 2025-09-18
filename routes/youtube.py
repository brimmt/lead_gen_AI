## Setup  Add your APIkey(s) to .env, restart the server. Example:
#YOUTUBE_API_KEY=your_bdg_api_key

from fastapi import APIRouter, HTTPException, Query
import httpx, os
from datetime import datetime

router = APIRouter(prefix="/leads/youtube", tags=["youtube"])

# ==== EDIT HERE: choose which fields to capture ====
CAPTURE_FIELDS = {
    "channelId": True,
    "channelTitle": True,    # channel "username-like" display
    "publishedAt": True,
    "description": False,    # set to True if you want more text
    "thumbnails": False,
}
# ===================================================

def _pick(snippet: dict) -> dict:
    m = {}
    if CAPTURE_FIELDS.get("channelId"):     m["channelId"] = snippet.get("channelId")
    if CAPTURE_FIELDS.get("channelTitle"):  m["channelTitle"] = snippet.get("channelTitle")
    if CAPTURE_FIELDS.get("publishedAt"):   m["publishedAt"] = snippet.get("publishedAt")
    if CAPTURE_FIELDS.get("description"):   m["description"] = snippet.get("description")
    if CAPTURE_FIELDS.get("thumbnails"):    m["thumbnails"] = snippet.get("thumbnails")
    return m

@router.get("")
async def youtube_search(q: str = Query(..., min_length=2),
                         published_after: str | None = None,
                         max_results: int = 25):
    api_key = os.getenv("YOUTUBE_API_KEY")  #Enter your API within the ""
    if not api_key:
        raise HTTPException(501, "YouTube API key not configured. See README.")
    params = {
        "part": "snippet",
        "q": q,
        "type": "video",
        "maxResults": max_results,
        "key": api_key
    }
    if published_after:
        params["publishedAfter"] = published_after

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://www.googleapis.com/youtube/v3/search", params=params)
        r.raise_for_status()
        data = r.json()

    items = []
    for it in data.get("items", []):
        vid = it["id"].get("videoId")
        if not vid: 
            continue
        sn = it["snippet"]
        items.append({
            "source": "youtube",
            "external_id": vid,
            "title": sn.get("title", ""),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "metadata": _pick(sn),          # <= EDIT CAPTURE_FIELDS above
            "discovered_at": datetime.utcnow().isoformat()
        })
    return {"ok": True, "count": len(items), "items": items}