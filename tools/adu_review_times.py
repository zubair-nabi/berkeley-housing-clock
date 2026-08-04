#!/usr/bin/env python3
"""
Where the time goes inside a Berkeley permit review, from the City's own workflow
milestones.

Everything else on this site measures the gap *between* approval and a building
permit. This measures inside the approval step, and it exists because the
recommendations page needed to answer two questions the State's file cannot:

  1. Every statutory clock Berkeley is held to starts when an application is
     deemed *complete*, not when it is filed. AB 2234 gives 30 business days for
     25 homes or fewer and 60 above that; the state ADU statute gives 60 days;
     AB 1332 gives 30 where a preapproved plan is used. So how long does reaching
     completeness take, and is it big enough to matter? It is: a median of 116
     days against 52 for the decision that follows.

  2. Does an application crawl from desk to desk? No. The technical reviews run
     concurrently, the spread between the first desk finishing and the last is a
     median of 4 days, and the consolidating desk adds 1. What costs time is a
     revision: 78 days against 0 without one, on 63% of records.

Both come from the `workflow` array Accela's public front end returns on every
record, which carries a dated, labelled milestone for each review step.

WHAT THIS CANNOT DO. Only the final "Application Complete" event is stored, not
the round trips that got there, so the 116 days locates the delay without saying
whose it is. Applicant-side and City-side are indistinguishable here. The portal
has a record-comment field that would explain each correction and its published
config marks it unavailable, which is why the reason is not recoverable from
outside. Do not let these numbers be read as an accusation about staff.

SAMPLING. Addresses come from HCD's Table A2 rows for Berkeley with UNIT_CAT=ADU.
The search endpoint caps at 10 records per address, so a busy address can hide
its ADU record; 26% of addresses returned the cap and are under-represented.
Records are kept only when the description names an ADU, so the sample skews to
records whose description is informative.

Usage:
    python3 tools/adu_review_times.py            # analyse data/adu-records.json
    python3 tools/adu_review_times.py --harvest  # re-fetch from the City first

Harvesting walks ~1000 addresses at 0.35s apart, about 15 minutes. The committed
data/adu-records.json means nobody has to do that to check the numbers.
"""
import collections
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://berkeley.agencycounter.com/api"
HEAD = {"Agency-Counter-Tenant": "berkeley", "Content-Type": "application/json",
        "User-Agent": "berkeley-housing-clock/1.0 "
                      "(+https://github.com/zubair-nabi/berkeley-housing-clock)"}
CKAN = "https://data.ca.gov/api/3/action/datastore_search"
RES_A2 = "fe505d9b-8c36-42ba-ba30-08bc4f34e022"
PAUSE = 0.35
RECORDS = os.path.join("data", "adu-records.json")
OUT = os.path.join("data", "adu-review.json")

ADU = re.compile(r"\bADU\b|\bJADU\b|accessory dwelling|second unit|junior accessory", re.I)
# Reviews that are not a technical desk: completeness is the intake gate and
# routing is the act of handing work out, so neither belongs in "how long did
# the desks take".
NOT_A_DESK = {"Completeness Review", "Plan Distribution"}
# The Permit Service Center consolidates the technical reviews, so it is last by
# construction. Measured separately for exactly that reason.
CONSOLIDATOR = "PSC Review"


def _req(path, body=None, tries=3):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, headers=HEAD,
                               method="POST" if data else "GET")
    for a in range(tries):
        try:
            return json.load(urllib.request.urlopen(r, timeout=45))
        except Exception as e:
            if a == tries - 1:
                return {"_err": str(e)}
            time.sleep(2 * (a + 1))


def adu_addresses():
    u = (f"{CKAN}?resource_id={RES_A2}&limit=10000&filters="
         + urllib.parse.quote(json.dumps({"JURIS_NAME": "BERKELEY"})))
    rows = json.load(urllib.request.urlopen(u, timeout=90))["result"]["records"]
    seen, out = set(), []
    for r in rows:
        if (r.get("UNIT_CAT") or "").strip() != "ADU":
            continue
        a = (r.get("STREET_ADDRESS") or "").strip()
        if a and a.upper() not in seen:
            seen.add(a.upper())
            out.append(a)
    return out


def harvest():
    addrs = adu_addresses()
    print(f"{len(addrs)} distinct ADU addresses", flush=True)
    q = urllib.parse.urlencode({"offset": 0, "limit": 10, "sort_by": "-record_date"})
    kept, unreachable, capped = [], 0, 0
    for i, addr in enumerate(addrs):
        d = _req(f"/search/list?{q}", {"___address": addr.upper()})
        if "_err" in d:
            unreachable += 1
            time.sleep(PAUSE)
            continue
        recs = (d.get("data") or {}).get("details") or []
        if not recs:
            p = _req("/address/predict?q=" + urllib.parse.quote(addr))
            hit = ((p.get("data") or [{}]) or [{}])[0].get("text") if "_err" not in p else None
            if hit and hit.upper() != addr.upper():
                d = _req(f"/search/list?{q}", {"___address": hit})
                recs = (d.get("data") or {}).get("details") or []
        if len(recs) >= 10:
            capped += 1
        for x in recs:
            if ADU.search(x.get("description") or ""):
                kept.append({
                    "addr": addr, "ref": x.get("agency_reference"),
                    "type": x.get("record_type"), "status": x.get("status_text"),
                    "desc": (x.get("description") or "")[:220],
                    "opened": x.get("opened_date"), "closed": x.get("closed_date"),
                    "workflow": [{"date": w.get("date"), "label": w.get("label"),
                                  "content": w.get("content")}
                                 for w in (x.get("workflow") or [])],
                })
        if i % 50 == 0:
            print(f"  {i}/{len(addrs)} kept={len(kept)} capped={capped}", flush=True)
        time.sleep(PAUSE)

    if unreachable > len(addrs) // 4:
        sys.exit(f"{unreachable} of {len(addrs)} addresses unreachable; "
                 "refusing to overwrite the record with a harvest this incomplete")
    os.makedirs("data", exist_ok=True)
    doc = {"generated": datetime.datetime.now(datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
           "addressesChecked": len(addrs), "unreachable": unreachable,
           "hitTenRecordCap": capped, "records": kept}
    json.dump(doc, open(RECORDS, "w"), indent=1)
    print(f"\nwrote {RECORDS}: {len(kept)} ADU-named records, {capped} addresses capped")


def _d(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _median(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def analyse():
    if not os.path.exists(RECORDS):
        sys.exit(f"{RECORDS} not found. Run with --harvest first.")
    doc = json.load(open(RECORDS))
    R = doc["records"]

    complete, decide = [], []
    review_span, consolidate, to_ready = [], [], []
    revised_days, clean_days, desks = [], [], collections.defaultdict(list)
    construction = collections.Counter()
    PRE = re.compile(r"prefab|modular|factory|abodu|manufactured", re.I)
    CONV = re.compile(r"convert|conversion|existing garage|garage to|basement|"
                      r"within the existing|legaliz", re.I)
    NEW = re.compile(r"\bnew\b|construct|build a|detached", re.I)

    for r in R:
        wf = r["workflow"]
        opened = _d(r["opened"])
        sub = next((w for w in wf if w["label"] == "Application Submittal"), None)
        route = next((w for w in wf if w["label"] in ("Plan Distribution",
                                                      "Application Submittal")), None)
        rdy = next((w for w in wf if (w["content"] or "").lower()
                    .startswith("ready to issue")), None)
        cr = next((w for w in wf if w["label"] == "Completeness Review"), None)
        dec = next((w for w in wf if w["label"] in ("Staff Decision", "Case Closed")), None)
        resub = [w for w in wf if "Resubmittal" in (w["label"] or "")]

        # 1. the intake gate against the decision the statutes actually govern.
        # These are independent intervals and are gated independently: a record
        # with a missing or malformed opened_date can still time a perfectly good
        # completeness-to-decision, and nesting the second test inside the first
        # silently dropped two of those.
        if cr and _d(cr["date"]):
            if opened and (_d(cr["date"]) - opened).days >= 0:
                complete.append((_d(cr["date"]) - opened).days)
            if dec and _d(dec["date"]) and (_d(dec["date"]) - _d(cr["date"])).days >= 0:
                decide.append((_d(dec["date"]) - _d(cr["date"])).days)

        # 2. what a revision costs
        if sub and rdy and _d(sub["date"]) and _d(rdy["date"]):
            n = (_d(rdy["date"]) - _d(sub["date"])).days
            if n >= 0:
                (revised_days if resub else clean_days).append(n)

        # 3. is review serial or concurrent, and who consolidates
        if route and _d(route["date"]):
            s = _d(route["date"])
            tech = [_d(w["date"]) for w in wf
                    if (w["label"] or "").endswith("Review")
                    and w["label"] not in NOT_A_DESK and w["label"] != CONSOLIDATOR
                    and (w["content"] or "").startswith("Approved") and _d(w["date"])]
            psc = next((_d(w["date"]) for w in wf if w["label"] == CONSOLIDATOR
                        and (w["content"] or "").startswith("Approved") and _d(w["date"])),
                       None)
            if tech:
                review_span.append((max(tech) - s).days)
                if psc:
                    consolidate.append((psc - max(tech)).days)
                    if rdy and _d(rdy["date"]):
                        to_ready.append((_d(rdy["date"]) - psc).days)
        # 4. does correction risk rise with the number of desks?
        seen = {w["label"] for w in wf if (w["label"] or "").endswith("Review")
                and w["label"] not in NOT_A_DESK}
        if seen:
            desks[min(len(seen), 6)].append(bool(resub))

        # 5. prefabricated or built on the lot
        if r["type"] in ("Building Permit", "Zoning Permit", "Minor Permit",
                         "Zoning Certificate - Building Permit",
                         "Zoning Certificate - Accessory Dwelling Units"):
            t = r["desc"] or ""
            construction["prefab" if PRE.search(t) else
                         "conversion" if CONV.search(t) else
                         "new on lot" if NEW.search(t) else "unclassified"] += 1

    total_rev = len(revised_days) + len(clean_days)
    out = {
        "generated": datetime.datetime.now(datetime.timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "harvestedAt": doc.get("generated"),
        "addressesChecked": doc["addressesChecked"],
        "recordsNamingAnADU": len(R),
        "addressesHittingTenRecordCap": doc["hitTenRecordCap"],
        "capShareOfAddresses": round(100 * doc["hitTenRecordCap"]
                                     / max(doc["addressesChecked"], 1)),
        "submittalToComplete": {"medianDays": _median(complete), "n": len(complete)},
        "completeToDecision": {"medianDays": _median(decide), "n": len(decide)},
        "revision": {
            "shareNeedingOne": round(100 * len(revised_days) / total_rev) if total_rev else None,
            "withRevisionMedianDays": _median(revised_days), "nWith": len(revised_days),
            "noRevisionMedianDays": _median(clean_days), "nWithout": len(clean_days)},
        "concurrency": {
            "routeToLastTechnicalDeskMedianDays": _median(review_span), "n": len(review_span),
            "lastDeskToConsolidationMedianDays": _median(consolidate), "nConsolidate": len(consolidate),
            "consolidationToReadyMedianDays": _median(to_ready), "nReady": len(to_ready)},
        "revisionRateByDeskCount": {
            str(k): {"n": len(v), "sharePct": round(100 * sum(v) / len(v))}
            for k, v in sorted(desks.items())},
        "constructionType": dict(construction),
    }
    os.makedirs("data", exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)

    print(f"addresses {out['addressesChecked']}  records {out['recordsNamingAnADU']}  "
          f"capped {out['capShareOfAddresses']}%\n")
    print(f"  submittal -> deemed complete   median {out['submittalToComplete']['medianDays']:4} d"
          f"   n={out['submittalToComplete']['n']}")
    print(f"  complete  -> decision          median {out['completeToDecision']['medianDays']:4} d"
          f"   n={out['completeToDecision']['n']}")
    rv = out["revision"]
    print(f"\n  needing a revision  {rv['shareNeedingOne']}%")
    print(f"    with revision                median {rv['withRevisionMedianDays']:4} d   n={rv['nWith']}")
    print(f"    without                      median {rv['noRevisionMedianDays']:4} d   n={rv['nWithout']}")
    cc = out["concurrency"]
    print(f"\n  route -> last technical desk   median {cc['routeToLastTechnicalDeskMedianDays']:4} d"
          f"   n={cc['n']}")
    print(f"  last desk -> consolidation     median {cc['lastDeskToConsolidationMedianDays']:4} d"
          f"   n={cc['nConsolidate']}")
    print(f"  consolidation -> ready         median {cc['consolidationToReadyMedianDays']:4} d"
          f"   n={cc['nReady']}")
    print("\n  revision rate by desks crossed")
    for k, v in out["revisionRateByDeskCount"].items():
        print(f"    {k} desks   n={v['n']:3d}   {v['sharePct']}%")
    print("\n  construction type:", out["constructionType"])
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    if "--harvest" in sys.argv:
        harvest()
    analyse()
