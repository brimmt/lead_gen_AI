import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os, re
from typing import List, Optional, Tuple

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from fastapi import Depends, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


load_dotenv()
#from routes import bermuda        #To add new route add: from routes import "new route name"
#from routes import gpr
#from routes import twitter_x
#from routes import reddit
#from routes import youtube
#from routes import instagram

PROVIDER = os.getenv("SEARCH_PROVIDER","serpapi").lower()
#SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000
#Login - Dummy User
fake_user = {
    "username": "demo",
    "password": "password123"
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Generate JWT token
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def _serp_key() -> str:
    k = os.getenv("SERPAPI_KEY")
    if not k:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY not set")
    return k


app = FastAPI(title="LeadSearch API", version="0.1.0")  #Update this whenever a new route is added
#app.include_router(bermuda.router)
#app.include_router(gpr.router)
#app.include_router(twitter_x.router)
#app.include_router(reddit.router)
#app.include_router(youtube.router)
#app.include_router(instagram.router)

# TATI ALWAYS DO THE APP. CALL AFTER APP= FASTAPI smart girl 


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://lead-gen-ai-frontend-omega.vercel.app"
    ],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

#Login Code Section  <- Remeber to update and pull from actual database

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    print(f"Got username={username}, password={password}")  # 👈 debug
    if username != fake_user["username"] or password != fake_user["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
def read_me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": username}



 


class Lead(BaseModel):
    profile_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None

class SearchResponse(BaseModel):
    params: dict
    results: List[Lead]


# - Helpers  -- 

NAME_SEP = re.compile(r"\s+")

def split_name(fullname: str) -> Tuple[Optional[str], Optional[str]]:
    if not fullname:
        return None, None
    parts = [p for p in NAME_SEP.split(fullname.strip()) if p]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0].title(), None
    return parts[0].title(), " ".join(p.title() for p in parts[1:])

def parse_from_search_title_snippet(title: str, snippet: str) -> dict:
    """
    Example title patterns:
      "Jane Doe - Marketing Manager - Oncology Care | LinkedIn"
      "John Smith - Growth Lead | LinkedIn"
    Snippet often: "Marketing Manager at Oncology Care · Tampa, FL"
    """
    first = last = role = company = None

    if title:
        t = title.replace("| LinkedIn", "").strip()
        parts = [p.strip(" -–—|") for p in re.split(r"[-–—|]", t) if p.strip()]
        # parts: [Name, Role, Company?]
        if parts:
            first, last = split_name(parts[0])
        if len(parts) >= 2:
            role = parts[1]
        if len(parts) >= 3:
            company = parts[2]

    if snippet and not company and " at " in snippet:
        # "... Role at Company · Location"
        after_at = snippet.split(" at ", 1)[1]
        company = after_at.split(" · ", 1)[0].strip()

    return dict(first_name=first, last_name=last, role=role, company=company)


def serpapi_search_urls(industry: str, location: str, limit: int, role_hint: str = "") -> List[dict]:
    """
    Returns list of dicts with {url, title, snippet} from SerpAPI.
    We request Google results for: site:linkedin.com/in "<industry>" "<location>" "<role_hint?>"
    """
    SERP_KEY = _serp_key()  # lazy lookup

    q = f'site:linkedin.com/in "{industry}" "{location}"'
    if role_hint:
        q += f' "{role_hint}"'

    params = {
        "engine": "google",
        "q": q,
        "num": min(limit, 20),  # SerpAPI max per page
        "api_key": SERP_KEY
    }

    with httpx.Client(timeout=30.0) as client:
        r = client.get("https://serpapi.com/search.json", params=params)
        r.raise_for_status()
        js = r.json()

    results = []
    for item in (js.get("organic_results") or []):
        url = item.get("link")
        if not url or "linkedin.com/in/" not in url:
            continue
        results.append({
            "url": url,
            "title": item.get("title", ""),
            "snippet": item.get("snippet", "")
        })

    # de-dupe, respect limit
    seen = set()
    out = []
    for r in results:
        u = r["url"]
        if u in seen:
            continue
        seen.add(u)
        out.append(r)
        if len(out) >= limit:
            break
    return out

# --- Routes ---
@app.get("/health")
def health():
    return {"ok": True, "provider": PROVIDER}

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )



@app.get("/leadsearch", response_model=SearchResponse)
@limiter.limit("5/minute")
def lead_search(
    request: Request,
    industry: str = Query(..., min_length=2),
    location: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    role_hint: str = Query("", description="e.g., reporter, editor, producer"),
    mode: str = Query("snippet")
):
    """
    Returns leads using search titles/snippets only (fast & resilient).
    Params: industry, location, limit.
    """
    if PROVIDER != "serpapi":
        raise HTTPException(400, "Only 'serpapi' supported in this build. Set SEARCH_PROVIDER=serpapi")

    web_items = serpapi_search_urls(industry, location, limit, role_hint)
    leads: List[Lead] = []

    for item in web_items:
        parsed = parse_from_search_title_snippet(item.get("title",""), item.get("snippet",""))
        leads.append(Lead(
            profile_url=item["url"],
            first_name=parsed.get("first_name"),
            last_name=parsed.get("last_name"),
            company=parsed.get("company"),
            role=parsed.get("role"),
        ))

    return SearchResponse(
        params={"industry": industry, "location": location, "limit": limit, "role_hint": role_hint, "mode": mode},
        results=leads
    )


@app.get("/")
def root():
    return {"ok": True, "service": "LeadSearch API"}




