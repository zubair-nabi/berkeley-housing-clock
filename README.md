# The Berkeley Housing Clock

How long it takes to build housing in Berkeley, California, and how much approved
housing is never built at all.

**Live: https://zubair-nabi.github.io/berkeley-housing-clock/**

A single static HTML file. No build step, no framework, no API keys, no server.
Open `index.html` and it fetches its own data.

## What it shows

Berkeley approves an apartment building in a median of about **6 months**, then it
waits roughly **1.6 years** for a building permit. Around **3,594 approved homes**
currently have no building permit on record, and of the homes approved between 2018
and 2021, **43% still have no permit** four or more years later.

- **Address lookup** matches any Berkeley address to its parcel number, then to
  every housing record the State holds for that parcel.
- **The Clock** measures each stage of the pipeline, split between multifamily and
  small projects, because small projects are ministerial and are approved and
  permitted on the same day.
- **The waiting room** lists approved projects with no building permit, aged, with
  a reason where the record gives one.
- **Where it is stuck** breaks the same figure down by street.
- **The skyline that isn't there** draws every approved-but-unbuilt project on its
  real parcel, extruded by the number of homes it would contain.
- **The scoreboard** tracks progress against Berkeley's 8,934 home state allocation.

## Sources

| Source | Used for | Access |
|---|---|---|
| [HCD Annual Progress Reports](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year) | Applications, approvals, permits, completions, affordability | CKAN API, fetched live in the browser |
| [Berkeley GIS](https://gis.cityofberkeley.info/arcgis/rest/services) | 62,000 address points, parcels, Housing Element sites, city boundary | ArcGIS REST, live for lookup and cached in `geo/` for the map |
| [BART GTFS](https://www.bart.gov/dev/schedules/google_transit.zip) | Richmond line alignment and stations | Extracted once into `geo/bart.json` |
| [OpenFreeMap](https://openfreemap.org) / OpenStreetMap | Basemap vector tiles | Live |
| Mapzen / AWS terrain tiles | Elevation for 3D terrain and hillshade | Live |

Everything derives from HCD's filings and Berkeley's own GIS. Every figure on the
page is computed in the browser at load time from those records, not hand entered.

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
- **The state file drops real filings.** Some completions Berkeley filed are absent
  from the state copy, so a project shown as "waiting" may hold a permit that was
  never reported upward. Corrections are welcome.
- **We can rarely say why a project is stalled.** Financing, interest rates and
  construction costs are in no public dataset. Where the record gives a reason, such
  as an incomplete financing stack or a closed application, it is shown.
- **Projects still under review are excluded** from the waiting room. Counting them
  would overstate the figure by about 40%.
- **UC Berkeley is not in this data.** Roughly 2,150 student beds are exempt from
  city permitting and appear in no source used here.
- **The map covers about 86% of waiting homes.** Some parcel numbers in the state
  file are not present in Berkeley's parcel layer, likely lot splits or mergers.
  The figures in the tables are the authoritative ones.
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

`geo/` holds parcel polygons, Housing Element sites, the city boundary and the BART
alignment. To rebuild it, query Berkeley's ArcGIS server for the parcels whose
`APN_SORT` matches the APNs in the current HCD extract, in small batches with a
pause between them. `APN_SORT` is byte identical to HCD's `APN` field, which is what
makes the join work at all; the parcel layer's own `APN` column uses a different
format and will not match.

## Licence

MIT for the code. The underlying data is public record and belongs to the agencies
that publish it, listed above.

Not affiliated with the City of Berkeley or the University of California.
