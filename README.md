# The Berkeley Housing Clock

How long it takes to build housing in Berkeley, California, and how much approved
housing is never built at all.

**Live: https://zubair-nabi.github.io/berkeley-housing-clock/**

A single static HTML page. No framework, no API keys, no server. Most of it fetches
its own data in the browser; one scheduled job parses the City's agenda PDFs, which
a browser is not allowed to read.

## What it shows

Berkeley approves an apartment building in a median of about **6 months**, then it
waits **1.6 years** for a building permit, or **3.3 years**, if you count the projects
that are still waiting rather than only the ones that made it. Around **5,636 approved homes**
across 97 sites have no building permit reported to the State and were never occupied,
and of the homes approved between 2018 and 2021, **34% are still in that state** four
or more years later.

Against its state allocation, Berkeley has permitted **30% of its market-rate
target and 10% of its combined affordable target** over the three years of the
cycle the State has published.

Berkeley needs **1,117 homes a year** and permits about **536**, so the rate would
have to roughly double. Measured against the other 538 jurisdictions doing the same
exercise, though, Berkeley is **ahead of most of California**: 18% of its allocation
against a statewide median of 16%, and 11% of the affordable half against a median
of 5%.

Three things the same file records and nobody prints: **75% of approved homes are in
projects that used a state density bonus**, **18% of permits issued are accessory dwelling
units**, and **97% of what gets built is rental**.

- **Address lookup** sits in a bar that follows you down the page, matching any
  Berkeley address to its parcel number and then to every housing record the State
  holds for it, including anything upcoming. Selecting a project anywhere on the page
  fills it in, and one control clears everything.
- **The Clock** measures each stage of the pipeline, split between multifamily and
  small projects. The small-project stages read "same day" between approval
  and permit, which is a reporting convention rather than a fast process: a ministerial ADU
  has no separate entitlement to record, so 512 of the 524 ADU rows carrying both dates carry
  them identical. Among small projects that are not ADUs the two dates diverge normally. It then runs the same measurement against five
  neighbouring cities, since without a baseline there is no way to judge 1.6 years.
  Berkeley comes third of six: slower than Oakland, faster than Alameda. Two blocks
  below it give that number the context it needs: a Kaplan-Meier estimate that keeps
  the still-waiting projects in the count, and RAND's 2025 production-time figures
  for California, Colorado and Texas with their estimate of what a month costs.
- **The waiting room** lists approved projects with no building permit reported to the
  State, aged, with a reason where the record gives one. A cross-check panel sets the
  nine downtown projects the City Council named as stalled in April 2026 against what
  Berkeley's own permit system actually holds for them, which is how the referral's
  claim that five had been permitted was tested, and found to be demolition permits.
- **Where it is stuck** breaks the same figure down by street.
- **The skyline that isn't there** draws every approved-but-unbuilt project on its
  real parcel, extruded by the number of homes it would contain.
- **What is happening now** is the only current section: upcoming ZAB agendas and
  environmental filings from the State clearinghouse, both reaching into 2026. Case
  numbers found there are matched against the waiting room, so a stalled project
  reappearing before the board is flagged.
- **The scoreboard** tracks progress against Berkeley's 8,934 home state allocation.

Agenda items and filings are matched back to parcels by case number, so they also
appear as markers on the map and as a "coming up" block in the address lookup. An
item that cannot be tied to a known parcel is left off the map rather than placed
approximately; it still appears in section 03.

## Sources

| Source | Used for | Access |
|---|---|---|
| [HCD Annual Progress Reports](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year) | Applications, approvals, permits, completions, affordability | CKAN API, fetched live in the browser |
| [Berkeley GIS](https://gis.cityofberkeley.info/arcgis/rest/services) | 62,000 address points, parcels, Housing Element sites, city boundary | ArcGIS REST, live for lookup and cached in `geo/` for the map |
| [ZAB agendas](https://berkeleyca.gov/your-government/boards-commissions/zoning-adjustments-board) | What the board is hearing next | PDFs parsed in CI into `data/zab.json` |
| [CEQAnet](https://ceqanet.lci.ca.gov/) | Environmental filings, City and UC | HTML fetched live in the browser |
| [BART GTFS](https://www.bart.gov/dev/schedules/google_transit.zip) | Richmond line alignment and stations | Extracted once into `geo/bart.json` |
| [HCD RHNA Progress Report](https://data.ca.gov/dataset/rhna-progress-report) | Official allocation and progress for all 539 California jurisdictions | CKAN API, fetched live |
| [OpenStreetMap via Overpass](https://overpass-api.de/) | AC Transit bus routes, weighted by how many routes share each street; 17 landmarks with their real building footprints | Extracted once into `geo/bus.json`, `geo/landmarks.json` and `geo/landmark_shapes.json` |
| [Berkeley permit records (Accela via AgencyCounter)](https://berkeley.agencycounter.com/building) | Live permit status per address; and the waiting-room verification in `data/permits.json` | JSON API, live in the browser per parcel, plus a scripted sweep of all 97 sites |
| [RAND, *The High Cost of Producing Multifamily Housing in California*](https://www.rand.org/pubs/research_reports/RRA3743-1.html) | Production-time benchmark and cost per month of delay | Quoted, April 2025 |
| [OpenFreeMap](https://openfreemap.org) / OpenStreetMap | Basemap vector tiles | Live |
| Mapzen / AWS terrain tiles | Elevation for 3D terrain and hillshade | Live |

Every figure *about Berkeley* derives from HCD's filings and Berkeley's own GIS, and is
computed in the browser at load time from those records rather than hand entered. Three
things on the page are hand-entered citations instead, each labelled as such where it
appears: Berkeley's RHNA allocation from the ABAG plan, the nine-project table from the
City Council referral of 14 April 2026, and RAND's production-time figures. Everything
they are compared against is still computed live.

### Why ZAB is built in CI but CEQAnet is not

CEQAnet sends `Access-Control-Allow-Origin: *`, so the browser can fetch and parse
it directly and the section is genuinely live. `berkeleyca.gov` sends no CORS header
at all, so a browser cannot read the agenda PDFs however it asks. Those are parsed
by `tools/fetch_zab.py` in a scheduled GitHub Action, twice a week, which commits
`data/zab.json`. The Brown Act requires an agenda 72 hours before a meeting and ZAB
meets about monthly, so twice a week catches every agenda with room to spare.

The workflow refuses to commit if it parses fewer than three meetings or finds no
case numbers at all, so a broken parse cannot silently replace good data. The
script enforces the same rule itself rather than relying on the workflow, because
run by hand there is no gate: if no listing page answers it exits 75 and leaves
`data/zab.json` alone, and if the harvest comes back at less than half what is
already on disk it refuses to write. The workflow treats 75 as "Berkeley's server
is down, nothing to do" and ends cleanly with a warning; every other failure stays
red. A scheduled run on 3 August 2026 hit exactly this: both listing fetches timed out and the script wrote an empty file that only the workflow gate caught.

### Why `geo/` is cached rather than fetched live

Berkeley's ArcGIS server rate limits, and hard. During development it refused every
request from this machine for about ten minutes after a few dozen queries. Parcel
boundaries change on the order of years, so they are baked into `geo/` and refreshed
deliberately. A page that re-queried them on every visit would get itself blocked.

HCD's CKAN endpoint is CDN backed and sends `Access-Control-Allow-Origin: *`, so
that half stays live.

## Design

Light only. No theme toggle, no `prefers-color-scheme` branch. Bricolage
Grotesque and Azeret Mono on a bone surface, with black rules and hard offset
shadows instead of soft borders and radii.

The five data colours were produced by the dataviz palette validator rather than
chosen by eye. The three that carry identity, stalled `#EE3F12`, built `#3B6FA8` and BART `#00875A`, pass every categorical check on all pairs against the surface,
and the built ramp passes the ordinal checks. The bus network is deliberately a
grey (`#94A3A8`) separated by lightness, because it is basemap context and fails
the categorical checks against every series at any hue. The acid green is a
highlight background only; at 0.93 relative luminance it has no contrast against
anything except black. `CLAUDE.md` records what failed and why.

## Known limits

- **HCD data reaches CY2025.** Reports are filed each April for the prior year, so
  nothing from 2026 appears in the state file until roughly April 2027.
- **The state file drops real filings**, in both directions. Some completions Berkeley
  filed are absent from the state copy, and some occupied buildings have no permit
  recorded at all. A completion therefore overrides a missing permit everywhere on
  this page: a building people live in is not waiting to be built. A project shown as
  waiting may still hold a permit that was never reported upward. Corrections welcome.

  How big that gap is, though, was tested and turned out to be small. Nine projects the
  City's FY25 inclusionary report says reached building permit were checked against the
  state file: seven are in it and **six of those seven agree**. So the state copy is
  broadly reliable, and the page treats it as such.

  An earlier version of this section claimed the opposite, on the strength of the City
  Council referral of 14 April 2026, which lists nine stalled downtown projects and says
  five of them "went on to receive a building permit" while HCD records none. Checking
  those five against Berkeley's own permit system, the source the referral cites, showed HCD was right: what those projects hold is a demolition permit, a shoring
  package still in corrections, and repairs dating from 1992 to 2010. Accela files
  demolition under the record type "Building Permit", which is the likely origin of the
  claim. **None of the nine holds a permit to build the homes.** The cross-check panel
  in section 02 now shows that comparison, which is the more interesting one.

- **The state file cannot see 2026**, so it is checked against one that can. HCD's file
  runs to 19 December 2025, which would leave anything permitted this year still reading
  as waiting. `tools/check_permits.py` walks every site in the waiting room against
  Berkeley's own permit system and writes `data/permits.json`; the waiting room states
  the result and the date it was checked. On 3 August 2026 the answer was that **none of
  the 97 has been permitted** since the state file closed. The only four permits issued
  in that window are two demolitions, a shed relocation and a remodelled entry, none of
  which is permission to build. The parcel card resolves any individual project live.
- **Two addresses are counted twice**, 2015 Blake and 3233 Ellis, because HCD holds
  separate filings on adjacent parcel numbers that are probably one project apiece.
  At 2015 Blake the 219-home record approved in September 2023 matches Council's
  figure exactly and a 161-home record approved in September 2021 sits beside it,
  most likely the superseded earlier version. They are left as filed rather than
  merged on a guess. Together they overstate the waiting room by 164 homes, 2.9%.
- **The stage bars are a floor, not a median.** A stage can only be measured on
  projects that finished it, and the ones still waiting are excluded precisely because
  they are slow. Of 90 multifamily approvals since 2018, 41 got a permit and 47 have
  not; those 47 have been waiting a median of 38 months already. Treating them as
  censored rather than missing puts the approval-to-permit median at **3.3 years**
  against the **1.6** the bar shows. Both are on the page. Only the 1.6 is comparable
  to the peer cities or to RAND, which measure completed projects the same way.
- **The RAND figures are quoted, not computed here.** Production times and the
  $1,284-per-home-per-month estimate come from *The High Cost of Producing Multifamily
  Housing in California* (RRA3743-1, April 2025). That per-unit estimate is an
  association rather than a causal one and sits at p = 0.116, just outside significance
  at the 90% level; the per-square-foot version it derives from is significant at 95%.
- **Approved is not the same as still approved.** Under BMC 23.404.060(C) a Berkeley
  zoning permit lapses if it is not exercised within a year, but the City *may* decline
  to declare it lapsed and cannot do so where the applicant made a substantial good-faith
  effort to obtain a building permit. So whether these approvals remain live is a
  discretionary call the record does not show. Searching the permit history of all 97
  sites for a lapse turned up exactly one trace: 2128 Oxford, 485 homes, which filed a use
  permit modification in December 2025 "for permit not exercised". That is a floor, not a count, because a permit that simply expires generates no record, so only a project moving to
  revive one leaves a mark.
- **We can rarely say why a project is stalled.** Financing, interest rates and
  construction costs are in no public dataset. Where the record gives a reason, such
  as an incomplete financing stack or a closed application, it is shown.
- **Undecided projects are excluded** everywhere, not just from the waiting room, and
  "undecided" means the record carries no approval date. It used to mean HCD's
  `APPLICATION_STATUS` column read "Pending", which turned out to be unusable: thirty
  parcels carry an approval date and a Pending status at once, including 2190 Shattuck,
  approved in February 2019, and 3000 Shattuck, approved in September 2018. Nothing is
  under review for seven years. Filtering on that column also dropped three of the nine
  projects Council itself calls stalled. The date fields now govern and the status
  column survives only as a note on the parcel card. The same rule drives the corridor
  table, the attrition figure and the map, so "stalled" still means one thing
  throughout. It moved the waiting room from 3,243 homes to 5,636.
- **The scoreboard paces against published years, not the calendar.** Permits exist
  for 2023 to 2025; 2026 will not appear until HCD publishes in April 2027. Pacing
  to today's date would make every bar look further behind than the record shows.
- **UC Berkeley is not in this data.** Roughly 2,150 student beds are exempt from
  city permitting and appear in no source used here.
- **The map covers about 88% of waiting homes**, 82 of 97 sites. Some parcel numbers in the state
  file are not present in Berkeley's parcel layer, likely lot splits or mergers.
  The figures in the tables are the authoritative ones.
- **The extrusion scale is symbolic; the landmarks are not.** Projects are drawn at
  1.6 m per home, which is not a physical height. Landmarks use their real OSM
  footprints, so the Greek Theatre and the stadium bowl are the shapes they actually
  are. Only the Campanile has a recorded height, 93.6 m; the rest are derived from
  floor count and drawn translucent to say so. The tallest tower on the map is 739
  homes, roughly twelve Campaniles.
- **The moving train, the boats and the birds are decoration.** The BART alignment
  and station positions are real, taken from the agency's published GTFS feed, but
  the train's position is a loop, not a live feed.

## Running locally

```sh
git clone https://github.com/zubair-nabi/berkeley-housing-clock.git
cd berkeley-housing-clock
python3 -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` directly mostly works, since
HCD allows any origin, but the cached `geo/` files need to be served over HTTP.

After changing `index.html`, run `python3 tools/check.py`. It verifies JS syntax,
per-section `<div>` balance, required element ids and that no computed figure has
been hard-coded into the markup. The same script runs in CI on every push. It is a
static check, so it cannot tell you an element rendered into the wrong section. `CLAUDE.md` has a short browser snippet for that, and notes the invariants that are
easy to break.

## Refreshing the permit check

`data/permits.json` is the answer to "how do you know none of these got permitted after
the State stopped looking". Rebuild it when the waiting room changes:

```sh
# 1. export the current waiting room from the page, in a browser console:
#    copy(JSON.stringify(WAIT.map(w => ({apn:w.apn, addr:w.addr,
#      units:Math.round(w.units), ent:w.ent.toISOString().slice(0,10)}))))
#    then save it as data/waiting.json
python3 tools/check_permits.py
```

It makes one or two requests per site, paced, and refuses to publish if more than a
quarter of the sites were unreachable. Anything it finds that its keyword filter does not
recognise as minor work is written out with `looksMinor: false` so a person reads the
description before the headline number moves, because Accela files demolition and repairs under
the same record type as new construction, which is the trap that caught the City Council.

## The recommendations page

`what-could-change.html` is argument rather than measurement, which is why it is a
separate page behind its own disclaimer: disagreeing with it should cost the reader
nothing on the data. It makes three cases, and two of them were rewritten mid-draft
when the City's own records contradicted the first version. An earlier draft
recommended that Berkeley adopt preapproved plans for accessory units; it already has
them, because AB 1332 required every California city to by 1 January 2025.

It is also the one part of the site whose figures are not computed live in the browser.
They come from `tools/adu_review_times.py`, which reads the workflow milestones Accela
publishes on each permit record:

```sh
python3 tools/adu_review_times.py            # analyse data/adu-records.json
python3 tools/adu_review_times.py --harvest  # re-fetch from the City first, ~15 min
```

`data/adu-records.json` is committed so the numbers can be re-derived without
re-querying the City, and `data/adu-review.json` holds the computed output. The two
findings that matter:

- **Reaching completeness takes a median of 116 days; the decision that follows takes
  52.** Every statutory clock that binds Berkeley starts at completeness, not at
  submittal, so a city can report full compliance and have described a third of the
  wait.
- **Review is already concurrent.** The spread between the first technical desk
  finishing and the last is a median of 4 days and consolidation adds 1, so there is no
  queue to remove. What costs time is a revision: 78 days against 0 without one, on 63%
  of records.

The hard limit on both: only the final "Application Complete" event is stored, not the
round trips that got there, so the 116 days locates the delay without attributing it.
It may be applicant-side. The portal has a record-comment field that would say, and its
published config marks that field unavailable.

## Refreshing the cached geometry

`geo/` holds parcel polygons, Housing Element sites, the city boundary, the BART
alignment and the AC Transit network. AC Transit's own API needs a token and the
GTFS aggregators need keys, so the bus geometry comes from OpenStreetMap through
Overpass, which needs neither. Each segment carries `n`, the number of routes that
use it, which is what makes the trunk corridors draw heavier than a residential
loop. To rebuild it, query Berkeley's ArcGIS server for the parcels whose
`APN_SORT` matches the APNs in the current HCD extract, in small batches with a
pause between them. `APN_SORT` is byte identical to HCD's `APN` field, which is what
makes the join work at all; the parcel layer's own `APN` column uses a different
format and will not match.

## Licence

MIT for the code. The underlying data is public record and belongs to the agencies
that publish it, listed above.

Not affiliated with the City of Berkeley or the University of California.
