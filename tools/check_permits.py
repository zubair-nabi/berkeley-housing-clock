#!/usr/bin/env python3
"""
Ask Berkeley whether anything in the waiting room has been permitted since the
State stopped looking.

HCD publishes once a year and its file currently ends 19 December 2025, so a
project permitted during 2026 still reads as waiting. That is the obvious attack
on the waiting-room total, and it is answerable: the City's Accela front end is
public, needs no key, and is current to today.

This walks every waiting site, asks the City for its permit record, and reports
any Building Permit issued after the State's file closed. It writes
data/permits.json, which the page reads to state when it was last verified.

Read the descriptions, do not just count records. Accela files demolition,
shoring, re-roofs and signs under the record type "Building Permit", and records
prefixed ESR- are submittal intakes rather than permits. Conflating those is how
the City Council's April 2026 referral came to report five building permits that
do not authorise a single home. MINOR below is deliberately broad: a false
"minor" leaves a project in the waiting room, which is the safe direction. Any
hit it does not recognise is written out with looksMinor false so a human looks
at it before the number moves.

Gentle by construction: one or two requests per site, paced. Berkeley's other
public endpoint rate limits hard and this one deserves the same courtesy.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://berkeley.agencycounter.com/api"
UA = ("berkeley-housing-clock/1.0 "
      "(+https://github.com/zubair-nabi/berkeley-housing-clock)")
HEAD = {"Agency-Counter-Tenant": "berkeley", "Content-Type": "application/json",
        "User-Agent": UA}
PAUSE = 0.35

# The State's file ends here; anything after it is the blind spot we are closing.
CUTOFF = "2025-12-19"

# Work that is not permission to build the homes.
MINOR = re.compile(
    r"demol|shoring|grading|excavat|soils|fence|\bsign\b|temporary|utilit|sewer|"
    r"reroof|re-roof|roof|solar|tree|repair|tenant improvement|electrical|plumb|"
    r"mechanical|water heater|furnace|window|deck|garden|fire alarm|sprinkler|"
    r"antenna|awning|kitchen|bath|remodel|move|moving", re.I)


def _req(path, body=None, tries=3):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, headers=HEAD,
                               method="POST" if data else "GET")
    for a in range(tries):
        try:
            return json.load(urllib.request.urlopen(r, timeout=40))
        except Exception as e:
            if a == tries - 1:
                print(f"  ! {path}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (a + 1))


def records(addr):
    """Permit records at an address. ___address is an exact match and HCD often
    stores '2190 Shattuck' where Accela has '2190 SHATTUCK AVE', so fall back to
    asking the City for its own spelling."""
    q = urllib.parse.urlencode({"offset": 0, "limit": 10, "sort_by": "-record_date"})
    d = _req(f"/search/list?{q}", {"___address": addr.upper()})
    out = (d or {}).get("data", {}).get("details", [])
    if out:
        return out
    p = _req("/address/predict?q=" + urllib.parse.quote(addr))
    hit = ((p or {}).get("data") or [{}])[0].get("text")
    if hit and hit.upper() != addr.upper():
        d = _req(f"/search/list?{q}", {"___address": hit})
        out = (d or {}).get("data", {}).get("details", [])
    return out


def main():
    src = os.path.join("data", "waiting.json")
    if not os.path.exists(src):
        sys.exit(f"{src} not found — export the waiting room first "
                 "(see the note in README under 'Refreshing the permit check')")
    wait = json.load(open(src))
    hits, unreachable = [], 0
    for i, w in enumerate(wait):
        recs = records(w["addr"])
        if recs is None:
            unreachable += 1
        for x in recs or []:
            if x.get("record_type") != "Building Permit":
                continue
            if not re.search(r"issued|final|complete", x.get("status_text") or "", re.I):
                continue
            if (x.get("record_date") or "")[:10] <= CUTOFF:
                continue
            if (x.get("agency_reference") or "").startswith("ESR-"):
                continue
            desc = (x.get("description") or "").strip()
            hits.append({"addr": w["addr"], "apn": w.get("apn"),
                         "units": w.get("units"),
                         "ref": x.get("agency_reference"),
                         "date": (x.get("record_date") or "")[:10],
                         "status": x.get("status_text"),
                         "desc": desc[:200],
                         "looksMinor": bool(MINOR.search(desc))})
        if i % 10 == 0:
            print(f"  {i}/{len(wait)} checked, {len(hits)} hit(s)", flush=True)
        time.sleep(PAUSE)

    if unreachable > len(wait) // 4:
        sys.exit(f"{unreachable} of {len(wait)} sites unreachable; "
                 "refusing to publish a check this incomplete")

    real = [h for h in hits if not h["looksMinor"]]
    doc = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "checkedDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "source": "https://berkeley.agencycounter.com/building",
           "note": "Building Permits issued after the State's file closed on "
                   f"{CUTOFF}, for every site in the waiting room. Accela files "
                   "demolition and repairs under the same record type, so each "
                   "hit carries its description and a looksMinor flag.",
           "cutoff": CUTOFF,
           "sitesChecked": len(wait),
           "sitesUnreachable": unreachable,
           "permitsFound": len(hits),
           "notMinor": len(real),
           "hits": hits}
    os.makedirs("data", exist_ok=True)
    with open("data/permits.json", "w") as f:
        json.dump(doc, f, indent=1)
    print(f"\nwrote data/permits.json — {len(wait)} sites, {len(hits)} permit(s) "
          f"since {CUTOFF}, {len(real)} not obviously minor")
    for h in hits:
        print(f"   {'minor' if h['looksMinor'] else 'REVIEW'}  {h['addr'][:26]:28s} "
              f"{h['date']}  {h['ref']:16s} {h['desc'][:64]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
