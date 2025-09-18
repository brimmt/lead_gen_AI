from fastapi import APIRouter, HTTPException, Query
import os

router = APIRouter(prefix="/leads/instagram", tags=["instagram"])

# ==== EDIT HERE when BDG has a real IG Graph app ====
# Typical fields you’d capture after permissions:
# - username (via Business Discovery endpoint)
# - caption, media_type, permalink (via /media)
# ====================================================

@router.get("")
async def instagram_placeholder(hashtag: str = Query(..., min_length=2)):
    if not (os.getenv("IG_ACCESS_TOKEN") and os.getenv("IG_BUSINESS_ACCOUNT_ID")):
        raise HTTPException(501, "Instagram Graph credentials not configured. See README.")
    # NOTE: Implement after BDG's FB App is Live and permissions approved.
    # Example flow:
    # 1) Hashtag search → get hashtag ID
    # 2) Query recent media for that hashtag
    # 3) Or use Business Discovery to fetch account by username to get fields incl. username
    return {"ok": True, "count": 0, "note": "IG Graph requires approved app/permissions. See docs."}