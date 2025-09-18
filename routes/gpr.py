# routes/gpr.py
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
import re, asyncio

router = APIRouter(prefix="/leads/gpr", tags=["gpr"])
BASE = "https://ssl.doas.state.ga.us/gpr"

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
)

PHONE_RE = re.compile(r'(\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4})(?:\s*(?:x|ext\.?)\s*(\d+))?', re.I)

def normalize_detail(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")  # if lxml complains, switch to "html.parser"

    # Title (top of page)
    title_el = soup.select_one("h1, .page-title, .col-lg-12 h1")
    title = title_el.get_text(strip=True) if title_el else "Untitled Opportunity"

    # Agency line is the <h4 class="mt-3"> just above Buyer Contact (from your screenshot)
    agency_name = None
    h4s = soup.select("h4.mt-3")
    if h4s:
        # Grab the one that looks like "66789  THE ATLANTA DEVELOPMENT AUTHORITY"
        line = h4s[0].get_text(" ", strip=True).replace("\xa0", " ")
        # Drop leading numeric code if present
        agency_name = re.sub(r"^\d+\s+", "", line)

    # Find the Buyer Contact <h3> then its following <p>
    contact_name = contact_email = contact_phone = phone_ext = None
    buyer_h3 = next((h for h in soup.find_all("h3") if "Buyer Contact" in h.get_text()), None)
    if buyer_h3:
        p = buyer_h3.find_next("p")
        if p:
            # Email from <a href="mailto:..."> or its text
            a = p.find("a", href=re.compile(r"^mailto:", re.I))
            if a:
                contact_email = (a.get_text(strip=True) or a.get("href", "").split(":", 1)[-1]).strip()

            # Contact name: first text node BEFORE the <a>
            for node in p.children:
                if isinstance(node, NavigableString):
                    s = str(node).replace("\xa0", " ").strip(" ,")
                    if s:
                        contact_name = s
                        break
                elif node.name == "a":
                    # stop once we reach the link; name should already be set
                    break

            # Phone appears after the link in the same <p>
            txt = p.get_text(" ", strip=True).replace("\xa0", " ")
            m = PHONE_RE.search(txt)
            if m:
                contact_phone = m.group(1)
                phone_ext = m.group(2)

    # End Date (highlighted on the right)
    end_date = None
    # Try a flexible search for any node that contains 'End Date:'
    end_label = soup.find(string=re.compile(r"End Date\s*:", re.I))
    if end_label:
        line = end_label.parent.get_text(" ", strip=True).replace("\xa0", " ")
        # e.g., "End Date: Sep 30, 2025 @ 05:00 PM EDT"
        m = re.search(r"End Date:\s*(.+)", line, re.I)
        if m:
            end_date = m.group(1)

    # Grab other table metadata generically (keeps your original behavior)
    metadata = {}
    for tr in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.select("th,td")]
        if len(cells) == 2:
            k, v = cells
            key = k.lower().replace(" ", "_").replace(":", "")
            metadata[key] = v

    # external_id from URL
    m = re.search(r"eSourceNumber=([A-Z0-9\-]+)", url)
    external_id = m.group(1) if m else url
    #Update the table below to filter what's captured
    return {
        "source": "gpr",
        "external_id": external_id,
        "title": title,
        "agency_name": agency_name,
        "url": url,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "phone_ext": phone_ext,
        "end_date": end_date,
        "metadata": metadata,  # full table for reference
        "discovered_at": datetime.utcnow().isoformat()
    }

@router.get("")  # full path = /leads/gpr
async def fetch_gpr(eSourceNumber: str = Query(..., min_length=5)):
    url = f"{BASE}/eventDetails?eSourceNumber={eSourceNumber}&sourceSystemType=gpr20"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=CHROME_UA,
                locale="en-US",
                viewport={"width": 1366, "height": 900},
                ignore_https_errors=True,
            )
            page = await context.new_page()
            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": "https://ssl.doas.state.ga.us/gpr/",
            })

            resp = await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            final_url = page.url
            status = resp.status if resp else None

            if "unsupported" in final_url.lower():
                raise RuntimeError(f"Redirected to unsupported page: {final_url}")
            if status is None or status >= 400:
                raise RuntimeError(f"Bad status {status} at {final_url}")

            # wait for meaningful content
            await page.wait_for_selector("table, h1, .page-title", timeout=20_000)
            html = await page.content()
            await context.close()
            await browser.close()

    except PWTimeout as e:
        raise HTTPException(status_code=504, detail=f"Playwright timeout: {e}")
    except Exception as e:
        # include the exact exception so we can iterate quickly
        raise HTTPException(status_code=502, detail=f"Playwright fetch failed: {type(e).__name__}: {e}")

    lead = normalize_detail(html, url)
    return {"ok": True, "count": 1, "items": [lead]}