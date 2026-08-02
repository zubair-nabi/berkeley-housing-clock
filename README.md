# The Berkeley Housing Clock

How long it takes to build housing in Berkeley, California, and how much approved
housing is never built at all.

**Live: https://zubair-nabi.github.io/berkeley-housing-clock/**

A single static HTML page. No framework, no API keys, no server. Most of it fetches
its own data in the browser; one scheduled job parses the City's agenda PDFs, which
a browser is not allowed to read.

## What it shows

Berkeley approves an apartment building in a median of about **6 months**, then it
waits roughly **1.6 years** for a building permit. Around **3,243 approved homes**
currently have no building permit on record and were never occupied, and of the homes
approved between 2018 and 2021, **22% are still in that state** four or more years later.

Against its state allocation, Berkeley has permitted **30% of its market-rate
target and 10% of its combined affordable target** over the three years of the
cycle the State has published.

Three things the same file records and nobody prints: **75% of approved homes came
through a state density bonus**, **18% of permits issued are accessory dwelling
units**, and **97% of what gets built is rental**.

- **Address lookup** matches any Berkeley address to its parcel number, then to
  every housing record the State holds for that parcel.
- **The Clock** measures each stage of the pipeline, split between multifamily and
  small projects, because small projects are ministerial and are approved and
  permitted on the same day. It then runs the same measurement against five
  neighbouring cities, since without a baseline there is no way to judge 1.6 years.
  Berkeley comes third of six: slower than Oakland, faster than Alameda.
- **The waiting room** lists approved projects with no building permit, aged, with
  a reason where the record gives one.
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
| [OpenStreetMap via Overpass](https://overpass-api.de/) | AC Transit bus routes, weighted by how many routes share each street; 17 landmarks with their real building footprints | Extracted once into `geo/bus.json`, `geo/landmarks.json` and `geo/landmark_shapes.json` |
| [OpenFreeMap](https://openfreemap.org) / OpenStreetMap | Basemap vector tiles | Live |
| Mapzen / AWS terrain tiles | Elevation for 3D terrain and hillshade | Live |

Everything derives from HCD's filings and Berkeley's own GIS. Every figure on the
page is computed in the browser at load time from those records, not hand entered.

### Why ZAB is built in CI but CEQAnet is not

CEQAnet sends `Access-Control-Allow-Origin: *`, so the browser can fetch and parse
it directly and the section is genuinely live. `berkeleyca.gov` sends no CORS header
at all, so a browser cannot read the agenda PDFs however it asks. Those are parsed
by `tools/fetch_zab.py` in a scheduled GitHub Action, twice a week, which commits
`data/zab.json`. The Brown Act requires an agenda 72 hours before a meeting and ZAB
meets about monthly, so twice a week catches every agenda with room to spare.

The workflow refuses to commit if it parses fewer than three meetings or finds no
case numbers at all, so a broken parse cannot silently replace good data.

### Why `geo/` is cached rather than fetched live

Berkeley's ArcGIS server rate limits, and hard. During development it refused every
request from this machine for about ten minutes after a few dozen queries. Parcel
boundaries change on the order of years, so they are baked into `geo/` and refreshed
deliberately. A page that re-queried them on every visit would get itself blocked.

HCD's CKAN endpoint is CDN backed and sends `Access-Control-Allow-Origin: *`, so
that half stays live.

## Known limits

- **HCD data reaches CY2025.** Reports are filed each April for the prior year, so
  nothing from 2026 appears in the state file until roughly April 2027.
- **The state file drops real filings**, in both directions. Some completions Berkeley
  filed are absent from the state copy, and some occupied buildings have no permit
  recorded at all. A completion therefore overrides a missing permit everywhere on
  this page: a building people live in is not waiting to be built. A project shown as
  waiting may still hold a permit that was never reported upward. Corrections welcome.
- **We can rarely say why a project is stalled.** Financing, interest rates and
  construction costs are in no public dataset. Where the record gives a reason, such
  as an incomplete financing stack or a closed application, it is shown.
- **Projects still under review are excluded** everywhere, not just from the waiting
  room. A project the City has not decided on is not stalled. Counting them would
  overstate the waiting room by about 40%, and the same filter is applied to the
  corridor table, the attrition figure and the map so that "stalled" means one thing
  throughout.
- **The scoreboard paces against published years, not the calendar.** Permits exist
  for 2023 to 2025; 2026 will not appear until HCD publishes in April 2027. Pacing
  to today's date would make every bar look further behind than the record shows.
- **UC Berkeley is not in this data.** Roughly 2,150 student beds are exempt from
  city permitting and appear in no source used here.
- **The map covers about 86% of waiting homes.** Some parcel numbers in the state
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
