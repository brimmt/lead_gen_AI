import os
import re
import time
import html
import random
import logging
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse, urljoin

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from fastapi import APIRouter

router = APIRouter(prefix="", tags=["bermuda-contacts"])

#SERP_KEY = os.getenv("SERPAPI_KEY")

def _serp_key() -> str:
    """Fetch SerpAPI key at runtime (not import time)."""
    k = os.getenv("SERPAPI_KEY")
    if not k:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY not set")
    return k



USER_AGENTS = [
    # (rotate to avoid being blocked)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0", ]


GENERIC_EMAIL_PREFIXES = (
    "info", "contact", "enquiry", "enquiries", "support", "admin",
    "office", "hello", "reception", "team", "customerservice", "sales"
)

SKIP_DOMAINS = {
    "facebook.com","linkedin.com","twitter.com","x.com","instagram.com",
    "youtube.com","maps.google.com","google.com","bing.com","yahoo.com","wikipedia.org"
}

HTTP_TIMEOUT = 12
CRAWL_PAUSE = (0.6, 1.3)  # polite pause between requests

class ContactResult(BaseModel):
    company_name: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    phones: List[str] = Field(default_factory=list)  #added 08/28/2025
    addresses: List[str] = Field(default_factory=list) #added 08/28/2025

def _headers() -> Dict[str, str]:
    return {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html,application/xhtml+xml"}

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""

def _looks_generic(email: str) -> bool:
    local = email.split("@", 1)[0].lower()
    return any(local == p or local.startswith(p + "+") for p in GENERIC_EMAIL_PREFIXES)

EMAIL_RE = re.compile(r'[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}', re.I)

def _extract_emails(text: str) -> List[str]:
    found = set(m.group(0) for m in EMAIL_RE.finditer(text or ""))
    # basic sanity
    found = {e.strip().strip(".,;:") for e in found if len(e) <= 80 and "@" in e}
    return sorted(found)

def _fetch(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=_headers(), timeout=HTTP_TIMEOUT)
        if r.status_code >= 400 or "text/html" not in r.headers.get("Content-Type",""):
            return None
        return r.text
    except Exception:
        return None

def _find_contact_links(base_url: str, html_text: str, limit: int = 5) -> List[str]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        txt = (a.get_text() or "").lower()
        if any(k in href.lower() for k in ("/contact", "contact-us", "contactus")) or "contact" in txt:
            links.append(urljoin(base_url, href))
    # add a couple of likely fallbacks
    for p in ("/contact", "/contact-us", "/contactus"):
        links.append(urljoin(base_url, p))
    # de-dupe while preserving order
    seen, out = set(), []
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:limit]

def serp_search(category: str, per_category: int = 12) -> List[Dict[str, Any]]:
    SERP_KEY = _serp_key()
    # We bias results toward Bermuda and business sites
    # q examples: "bank bermuda", "hospital bermuda", "insurance bermuda"
    q = f'{category} bermuda'
    results = []
    start = 0
    while len(results) < per_category and start <= 20:
        params = {
            "engine": "google",
            "q": q,
            "num": min(10, per_category - len(results)),
            "start": start,
            "hl": "en",
            "safe": "active",
            "api_key": SERP_KEY
        }
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        org = data.get("organic_results", []) or []
        for item in org:
            link = item.get("link")
            title = html.unescape(item.get("title") or "")
            if not link:
                continue
            dom = _domain(link)
            if not dom or dom in SKIP_DOMAINS:
                continue
            # Prefer the root site if link is deep
            site = f"{urlparse(link).scheme}://{urlparse(link).netloc}"
            results.append({"title": title, "link": link, "site": site})
        if not org:
            break
        start += 10
        time.sleep(random.uniform(*CRAWL_PAUSE))
    # Deduplicate by site
    seen, uniq = set(), []
    for r in results:
        if r["site"] not in seen:
            seen.add(r["site"])
            uniq.append(r)
    return uniq[:per_category]

def crawl_contact_info(site_url: str, pause=(0.6, 1.3), max_links=5) -> tuple[List[str], List[str], List[str]]:
    emails: set = set()
    phones: set = set()
    addrs:  set = set()

    home_html = _fetch(site_url)
    if home_html:
        # homepage
        emails.update(_extract_emails(home_html))
        try:
            emails.update(_extract_mailtos(home_html))
        except NameError:
            pass
        phones.update(_extract_phones(home_html))
        phones.update(_extract_tel_links(home_html))
        addrs.update(_extract_addresses(home_html))

        # likely contact pages
        for contact_url in _find_contact_links(site_url, home_html, limit=max_links):
            time.sleep(random.uniform(*pause))
            html_text = _fetch(contact_url)
            if not html_text:
                continue
            emails.update(_extract_emails(html_text))
            try:
                emails.update(_extract_mailtos(html_text))
            except NameError:
                pass
            phones.update(_extract_phones(html_text))
            phones.update(_extract_tel_links(html_text))
            addrs.update(_extract_addresses(html_text))

            # stop once we’ve got something useful
            if (any(_looks_generic(e) for e in emails) or len(phones) >= 1) and len(addrs) >= 1:
                break

    # filter emails to same-domain + generic
    dom = _domain(site_url)
    email_filtered = []
    for e in emails:
        edom = _domain("http://" + e.split("@", 1)[-1])
        if (not dom or edom == dom) and _looks_generic(e):
            email_filtered.append(e)

    return sorted(set(email_filtered))[:5], sorted(set(phones))[:5], sorted(set(addrs))[:5]

@router.get("/bermuda_contacts_serp", response_model=List[ContactResult])
def bermuda_contacts_serp(
    categories: str = Query("bank,hospital,insurance"),
    per_category: int = Query(12, ge=1, le=25),
    fast: bool = Query(False, description="Fewer contact pages + shorter delays"),
    only_with_emails: bool = Query(True, description="Filter out rows with no emails"),
    only_with_contacts: bool = Query(False, description="Require email OR phone/address (overridden by only_with_emails)")
):
    # speed knobs
    pause = (0.2, 0.4) if fast else CRAWL_PAUSE
    max_contact_links = 1 if fast else 5

    cats = [c.strip() for c in categories.split(",") if c.strip()]
    if not cats:
        raise HTTPException(status_code=400, detail="No categories provided")

    out: List[ContactResult] = []
    for cat in cats:
        try:
            serp = serp_search(cat, per_category=per_category)
        except Exception as e:
            logging.exception("SerpAPI error")
            raise HTTPException(status_code=502, detail=f"SerpAPI failed for '{cat}': {e}")

        for item in serp:
            site = item["site"]
            title = item.get("title") or ""
            time.sleep(random.uniform(*pause))
            emails, phones, addrs = crawl_contact_info(site, pause=pause, max_links=max_contact_links)
            out.append(ContactResult(
                company_name=title or _domain(site),
                website=site,
                category=cat,
                emails=emails,
                phones=phones,
                addresses=addrs,
                source_url=item.get("link")
            ))

    # de-dupe by website
    deduped: Dict[str, ContactResult] = {}
    for r in out:
        key = (r.website or "").lower()
        if key in deduped:
            d = deduped[key]
            d.emails = sorted(set(d.emails + r.emails))
            d.phones = sorted(set(d.phones + r.phones))
            d.addresses = sorted(set(d.addresses + r.addresses))
            if r.company_name and (not d.company_name or len(r.company_name) > len(d.company_name)):
                d.company_name = r.company_name
        else:
            deduped[key] = r

    results = list(deduped.values())
    if only_with_emails:
        results = [r for r in results if r.emails]
    elif only_with_contacts:
        results = [r for r in results if (r.emails or r.phones or r.addresses)]
    return results

@router.get("/_env_check")
def env_check():
    val = os.getenv("SERPAPI_KEY")
    return {"serp_key_loaded": bool(val), "length": len(val) if val else 0}

def _extract_mailtos(html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    out = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            addr = href.split(":", 1)[1].split("?")[0]
            if addr:
                out.add(addr)
    return sorted(out)


# ---------- Phones ----------
PHONE_RE = re.compile(
    r'(?:\+?1[\s.\-()]*)?(?:\(?\s*441\)?[\s.\-]*)?[2-9]\d{2}[\s.\-]?\d{4}',
    re.I
)

def _extract_tel_links(html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    out = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("tel:"):
            num = href.split(":", 1)[1].split("?")[0]
            if num:
                out.add(num)
    return sorted(out)

def _extract_phones(text: str) -> List[str]:
    if not text:
        return []
    found = set(m.group(0) for m in PHONE_RE.finditer(text))
    cleaned = {re.sub(r'[^0-9+]', '', p) for p in found}
    def fmt(d):
        digits = re.sub(r'\D','', d)
        if len(digits) == 11 and digits.startswith('1') and digits[1:4] == '441':
            return f'+1 441-{digits[4:7]}-{digits[7:]}'
        if len(digits) == 10 and digits[:3] == '441':
            return f'+1 441-{digits[3:6]}-{digits[6:]}'
        if len(digits) == 7:
            return f'{digits[:3]}-{digits[3:]}'
        return d
    return sorted({fmt(p) for p in cleaned})


# ---------- Addresses ----------
BERMUDA_LOCALITIES = {
    "Hamilton","Pembroke","Paget","Warwick","Devonshire","Smith's","Sandys",
    "St. George's","St Georges","Somerset","Southampton"
}
STREET_HINTS = ("st ", "rd ", "ave", "road", "street", "lane", "ln", "drive", "dr", "way", "court", "ct", "place", "pl", "par-ish", "parish", "building")
  
def _norm_space(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').strip())

def _extract_schema_org_addresses(soup: BeautifulSoup) -> List[str]:
    out = []
    for node in soup.select('[itemtype*="PostalAddress" i]'):
        parts = []
        for key in ("streetAddress","addressLocality","addressRegion","postalCode"):
            el = node.select_one(f'[itemprop="{key}"]')
            if el and el.get_text(strip=True):
                parts.append(el.get_text(" ", strip=True))
        if parts:
            out.append(_norm_space(", ".join(parts)))
    return out

def _extract_address_tags(soup: BeautifulSoup) -> List[str]:
    out = []
    for tag in soup.find_all("address"):
        txt = _norm_space(tag.get_text(" ", strip=True))
        if txt:
            out.append(txt)
    return out

def _extract_guess_addresses(soup: BeautifulSoup) -> List[str]:
    # Grab obvious “addressy” nodes
    candidates = []
    for el in soup.find_all(True, attrs={"class": True}):
        cls = " ".join(el.get("class", [])).lower()
        if any(k in cls for k in ("address","addr","location","contact")):
            candidates.append(el)
    for el in soup.find_all(True, attrs={"id": True}):
        i = (el.get("id") or "").lower()
        if any(k in i for k in ("address","addr","location","contact")):
            candidates.append(el)

    out = []
    for el in candidates[:15]:
        txt = _norm_space(el.get_text(" ", strip=True))
        if not txt:
            continue
        # Heuristics: a digit + a street hint OR a locality name
        low = txt.lower()
        has_num = bool(re.search(r'\d', low))
        has_hint = any(h in low for h in STREET_HINTS)
        has_loc = any(l.lower() in low for l in BERMUDA_LOCALITIES)
        if (has_num and has_hint) or has_loc:
            out.append(txt)
    # de-dup & keep short-ish lines
    uniq = []
    seen = set()
    for a in out:
        a2 = a[:200]
        if a2 not in seen:
            seen.add(a2)
            uniq.append(a2)
    return uniq

def _extract_addresses(html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    found = set()
    for a in _extract_schema_org_addresses(soup):
        found.add(a)
    for a in _extract_address_tags(soup):
        found.add(a)
    for a in _extract_guess_addresses(soup):
        found.add(a)
    # light cleanup: remove lines that are just phone/email blobs
    filtered = [a for a in found if not EMAIL_RE.search(a)]
    return sorted(filtered)





YB_DOMAIN = "bermudayp.com"

def _is_external(href: str) -> bool:
    try:
        d = urlparse(href).netloc.lower().replace("www.", "")
        return d and YB_DOMAIN not in d
    except Exception:
        return False

LISTING_RE = re.compile(r"/listing/view/\d+")
SEARCH_PAGE_RE = re.compile(r"/search/all/\d+/")

BAD_TITLES = {"explore our area", "home", "contact us", "contact", "about us"}

def _extract_listing_name(soup: BeautifulSoup) -> Optional[str]:
    # Try specific selectors first, then generic headers, then <title>, then og:title
    selectors = [
        'h1[itemprop="name"]',
        '.listing-title h1',
        '.listing-title',
        'h1',
        'h2',
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if not el:
            continue
        name = el.get_text(" ", strip=True)
        if name and name.lower() not in BAD_TITLES:
            return name

    # meta og:title as a fallback
    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        name = og.get("content").strip()
        if name and name.lower() not in BAD_TITLES:
            return name

    # <title> as last resort
    if soup.title:
        name = soup.title.get_text(strip=True)
        if name and name.lower() not in BAD_TITLES:
            return name

    return None


















def _yp_detail_parse(detail_url: str) -> Dict[str, Any]:
    html_text = _fetch(detail_url)
    if not html_text:
        return {}
    soup = BeautifulSoup(html_text, "html.parser")

    # Name (fallback to <title>)
    name = _extract_listing_name(soup)
    

    # Website: prefer anchor literally labeled "Website"; else first external http(s)
    website = None
    for a in soup.find_all("a", href=True):
        txt = (a.get_text() or "").strip().lower()
        href = a["href"].strip()
        if txt == "website" and href.startswith("http"):
            website = href
            break
    if not website:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("http") and _is_external(href):
                website = href
                break

    # Phones / addresses via your extractors
    body_text = soup.get_text(" ", strip=True)
    phones = set(_extract_phones(body_text))
    phones.update(_extract_tel_links(html_text))
    addrs = set(_extract_addresses(html_text))

    return {
        "company_name": name,
        "website": website,
        "phones": sorted(phones)[:5],
        "addresses": sorted(addrs)[:5],
        "source_url": detail_url.strip(),
    }

def _yp_collect_listing_links(search_url: str) -> List[str]:
    """Grab all detail page links on a search page."""
    html_text = _fetch(search_url)
    if not html_text:
        return []
    soup = BeautifulSoup(html_text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if LISTING_RE.search(href):
            links.append(urljoin(search_url, href))
    # de-dupe preserve order
    seen, out = set(), []
    for u in links:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


@router.get("/bermuda_yp", response_model=List[ContactResult])
def bermuda_yp(
    url: str = Query(..., description="BermudaYP search URL, e.g., https://www.bermudayp.com/search/all/1/insurances"),
    pages: int = Query(1, ge=1, le=10),
    limit: int = Query(30, ge=1, le=200),
    also_crawl_site: bool = Query(False, description="If true and website is present, try to pull generic emails from the site"),
    fast: bool = Query(True, description="Short pauses")
):
    pause = (0.2, 0.4) if fast else CRAWL_PAUSE

    # paginate like /search/all/1/<term>, /search/all/2/<term>, ...
    page_urls = []
    if SEARCH_PAGE_RE.search(url):
        m = re.search(r"/search/all/(\d+)/", url)
        start = int(m.group(1)) if m else 1
        for p in range(start, start + pages):
            page_urls.append(re.sub(r"/search/all/\d+/", f"/search/all/{p}/", url, count=1))
    else:
        page_urls = [url]

    detail_links = []
    for pu in page_urls:
        detail_links.extend(_yp_collect_listing_links(pu))
        time.sleep(random.uniform(*pause))
        if len(detail_links) >= limit:
            break
    detail_links = detail_links[:limit]

    out: List[ContactResult] = []
    for dlink in detail_links:
        row = {}
        try:
            row = _yp_detail_parse(dlink)
        except Exception:
            pass
        if not row:
            continue

        emails: List[str] = []
        phones_from_site: List[str] = []
        addrs_from_site: List[str] = []

        if also_crawl_site and row.get("website"):
            time.sleep(random.uniform(*pause))
            e2, p2, a2 = crawl_contact_info(row["website"], pause=pause, max_links=2)
            emails = e2
            phones_from_site = p2
            addrs_from_site = a2

        phones_merged = sorted(set((row.get("phones") or []) + phones_from_site))[:5]
        addrs_merged  = sorted(set((row.get("addresses") or []) + addrs_from_site))[:5]
        

        out.append(ContactResult(
            company_name=row.get("company_name") or _domain((row.get("website") or "").strip()) or "Unknown",
            website=(row.get("website") or "").strip() or None,
            category="bermuda_yp",
            emails=emails,
            phones=phones_merged,
            addresses=addrs_merged,
            source_url=(row.get("source_url") or "").strip()

))

    # de-dupe by website if present, else by source_url
    deduped: Dict[str, ContactResult] = {}
    for r in out:
        key = (r.website or r.source_url or "").lower()
        if key in deduped:
            d = deduped[key]
            d.emails = sorted(set(d.emails + r.emails))
            d.phones = sorted(set(d.phones + r.phones))
            d.addresses = sorted(set(d.addresses + r.addresses))
            if r.company_name and (not d.company_name or len(r.company_name) > len(d.company_name)):
                d.company_name = r.company_name
        else:
            deduped[key] = r

    return list(deduped.values())