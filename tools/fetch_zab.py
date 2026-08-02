#!/usr/bin/env python3
"""
Build data/zab.json from Berkeley's published Zoning Adjustments Board agendas.

Berkeley serves the agendas as PDFs from its own site with no CORS header, so a
browser cannot read them. This runs in CI instead, writes JSON into the repo, and
the site loads that. The PDFs are real text, not scans, so no OCR is involved.

Deliberately gentle: the listing page is fetched once per year requested and each
PDF once, with a pause between. Berkeley's servers have rate limited us before.
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import date, datetime

BASE = "https://berkeleyca.gov"
LIST = BASE + "/your-government/boards-commissions/zoning-adjustments-board"
UA = {"User-Agent": "berkeley-housing-clock/1.0 (+https://github.com/zubair-nabi/berkeley-housing-clock)"}
PAUSE = 2.0

# Addresses that appear on every agenda because they are the venue or City offices,
# not projects. Without this they become phantom developments.
VENUES = {"1231 ADDISON ST", "1947 CENTER ST", "2180 MILVIA ST"}

CASE = re.compile(r"\b((?:ZP|PLN|LMSAP|UP|DRC)\s*\n?\s*20\d{2}\s*-\s*\d{3,5})\b", re.I)
ADDR = re.compile(
    r"\b(\d{2,5})\s+((?:[A-Z][A-Za-z\.]*\s+){0,3}?)"
    r"(Street|St|Avenue|Ave|Way|Road|Rd|Boulevard|Blvd|Drive|Dr|Place|Pl|Court|Ct|Lane|Ln|Terrace|Path)\b")
UNITS = re.compile(r"(\d{1,4})\s*(?:new\s+)?(?:dwelling\s+units?|residential\s+units?|units?|apartments?)\b", re.I)


def get(url, binary=False, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read() if binary else r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                print(f"  ! {url}: {e}", file=sys.stderr)
                return None
            time.sleep(3 * (i + 1))


def norm_addr(num, mid, suf):
    mid = " ".join(mid.split())
    suf = {"St": "St", "Street": "St", "Ave": "Ave", "Avenue": "Ave", "Blvd": "Blvd",
           "Boulevard": "Blvd", "Rd": "Rd", "Road": "Rd", "Dr": "Dr", "Drive": "Dr",
           "Pl": "Pl", "Place": "Pl", "Ct": "Ct", "Court": "Ct", "Ln": "Ln",
           "Lane": "Ln"}.get(suf, suf)
    return f"{num} {mid} {suf}".replace("  ", " ").strip()


def agenda_links(years):
    """Scrape the listing page for agenda PDF URLs. The filename suffix is not
    stable (_Linked, _Linked_revised, _Linked_0), so links must be read, not built."""
    found = {}
    for y in years:
        html = get(f"{LIST}?field_meeting_date_value={y}")
        if not html:
            continue
        for m in re.finditer(r'href="([^"]*legislative-body-meeting-agendas/[^"]+\.pdf)"', html, re.I):
            href = urllib.parse.unquote(m.group(1))
            d = re.search(r"(20\d{2})[-_](\d{2})[-_](\d{2})", href)
            if not d:
                continue
            iso = f"{d.group(1)}-{d.group(2)}-{d.group(3)}"
            # prefer a revised agenda over the original for the same date
            if iso not in found or "revis" in href.lower():
                found[iso] = urllib.parse.urljoin(BASE, m.group(1))
        time.sleep(PAUSE)
    return dict(sorted(found.items(), reverse=True))


def parse_agenda(pdf_bytes):
    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf_bytes)).pages)
    text = text.replace(" ", " ")

    cases = []
    for c in CASE.findall(text):
        c = re.sub(r"\s+", "", c).upper()
        if c not in cases:
            cases.append(c)

    addrs = []
    for num, mid, suf in ADDR.findall(text):
        a = norm_addr(num, mid, suf)
        if a.upper() in VENUES or len(a) < 6:
            continue
        if a not in addrs:
            addrs.append(a)

    units = [int(u) for u in UNITS.findall(text) if 0 < int(u) <= 2000]
    return {"cases": cases, "addresses": addrs,
            "maxUnitsMentioned": max(units) if units else None,
            "chars": len(text)}


def main():
    this_year = date.today().year
    years = [this_year, this_year - 1]
    if "--all" in sys.argv:
        years = list(range(this_year, 2020, -1))

    out, links = [], agenda_links(years)
    print(f"found {len(links)} agendas across {years}")
    for iso, url in links.items():
        b = get(url, binary=True)
        time.sleep(PAUSE)
        if not b:
            continue
        try:
            p = parse_agenda(b)
        except Exception as e:
            print(f"  ! parse {iso}: {e}", file=sys.stderr)
            continue
        out.append({"date": iso, "url": url, **p})
        print(f"  {iso}  {len(p['cases'])} case(s), {len(p['addresses'])} address(es)")

    doc = {"generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "source": LIST,
           "note": "Parsed from Berkeley's published ZAB agenda PDFs. Case numbers and "
                   "addresses are extracted text, not a City data feed.",
           "meetings": sorted(out, key=lambda m: m["date"], reverse=True)}
    os.makedirs("data", exist_ok=True)
    with open("data/zab.json", "w") as f:
        json.dump(doc, f, indent=1)
    print(f"wrote data/zab.json with {len(out)} meetings")


if __name__ == "__main__":
    main()
