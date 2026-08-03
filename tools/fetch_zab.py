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
from datetime import date, datetime, timezone

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


# Exit code for "upstream was unreachable, so there is nothing to say". Distinct
# from a parse failure, which is a real problem and must stay loud. 75 is
# EX_TEMPFAIL from sysexits.h, the conventional "try again later".
EX_TEMPFAIL = 75

# berkeleyca.gov timed out on a scheduled run and each attempt sat on the old
# 60s timeout, so two listing fetches burned six minutes before failing. The
# site answers in about two seconds when it is up; if it has not responded in
# 25 there is nothing to wait for.
TIMEOUT = 25


def get(url, binary=False, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT) as r:
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
    stable (_Linked, _Linked_revised, _Linked_0), so links must be read, not built.

    Returns (links, reached) where reached is how many listing pages actually
    answered. Zero means the site was down, which is a different thing from the
    site being up and having no agendas, and the caller must not confuse them."""
    found, reached = {}, 0
    for y in years:
        html = get(f"{LIST}?field_meeting_date_value={y}")
        if not html:
            continue
        reached += 1
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
    return dict(sorted(found.items(), reverse=True)), reached


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
            "maxUnitsMentioned": max(units) if units else None}


def main():
    this_year = date.today().year
    years = [this_year, this_year - 1]
    if "--all" in sys.argv:
        years = list(range(this_year, 2020, -1))

    out = []
    links, reached = agenda_links(years)
    if not reached:
        # Every listing fetch failed. We know nothing, and writing what we know
        # would replace a good file with an empty one. A scheduled run once did
        # exactly this and only the workflow's sanity gate stopped the commit;
        # run by hand it would have destroyed data/zab.json.
        print(f"could not reach {BASE} for any of {years}; leaving data/zab.json alone",
              file=sys.stderr)
        return EX_TEMPFAIL
    print(f"found {len(links)} agendas across {years} ({reached}/{len(years)} listing pages answered)")
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

    meetings = sorted(out, key=lambda m: m["date"], reverse=True)

    # Keep the previous timestamp if nothing substantive changed. Otherwise every
    # run produces a diff and the schedule fills the history with noise.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = None
    try:
        prev = json.load(open("data/zab.json"))
        if prev.get("meetings") == meetings:
            stamp = prev.get("generated", stamp)
            print("no change since last run")
    except Exception:
        pass

    # Some listing pages answered but the harvest came back much thinner than what
    # is already on disk: individual PDFs failed, or the page markup changed. Either
    # way this is not an improvement, so keep the good file and say so loudly. The
    # workflow has the same check, deliberately -- this one makes the script safe to
    # run by hand, which is where an overwrite would be unrecoverable.
    have = len(prev.get("meetings", [])) if isinstance(prev, dict) else 0
    if have and len(meetings) < max(3, have // 2):
        print(f"parsed only {len(meetings)} meetings against {have} already on disk; "
              "refusing to overwrite", file=sys.stderr)
        return 1

    doc = {"generated": stamp,
           "source": LIST,
           "note": "Parsed from Berkeley's published ZAB agenda PDFs. Case numbers and "
                   "addresses are extracted text, not a City data feed.",
           "meetings": meetings}
    os.makedirs("data", exist_ok=True)
    with open("data/zab.json", "w") as f:
        json.dump(doc, f, indent=1)
    print(f"wrote data/zab.json with {len(out)} meetings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
