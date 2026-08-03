# Working on the Housing Clock

Everything is in `index.html` — markup, CSS and the whole application, about
140KB. There is no build step, no framework and no server. `python3 -m http.server`
and open it. Read `README.md` first for what the page actually claims.

## Editing index.html

**Never edit this file with an unanchored string replace.** Both times it broke
badly, that was the cause. Once a `.replace("", new)` matched the empty string and
injected a block between every character, producing a 24MB file. Once a slice ran
to an anchor that occurred earlier than assumed and deleted five functions —
`node --check` still passed, because the result was valid JavaScript that was
simply missing things. Use Edit with enough surrounding context to be unique, and
if you must script a change, assert the anchor exists and appears exactly once
before writing.

After **every** edit:

```sh
python3 tools/check.py
```

It checks file size, JS syntax, per-section `<div>` balance, required element ids
and duplicates, hard-coded figures, and JSON validity. It runs in CI on push.

Static checks cannot tell you an element landed in the *wrong section* — that was
a real bug, where a stray `</div>` ended a `<section>` early and three elements
the renderer writes into ended up outside it. Nothing threw. So also load the page
and run this in the browser:

```js
const secOf = el => {
  const s = el?.closest("section"), h = s?.querySelector("h2[data-nav]");
  return h ? h.dataset.nav : (s ? "(unnamed)" : "OUTSIDE ANY SECTION");
};
["w-units","xclist","censorbox","corrlist","tierlist","findlist","zablist"]
  .map(id => ({id, where: secOf(document.getElementById(id))}));
```

Then look at it. Screenshot the sections you touched.

## Invariants that are easy to break

**`isStalled` is the single definition of "stalled."** It feeds the waiting room,
the corridor table, the attrition figure, the map and the README. There was a
period when "stalled" meant four different things and Shattuck read 74% in one
place and 48% in another. If you change the predicate, re-derive every dependent
figure and update the README in the same commit.

**HCD's file is incomplete in both directions, and the page must say so.** Some
occupied buildings have no permit recorded; some completions are missing. Never
write "no building permit" — write **"no building permit reported to the State."**
The Council cross-check panel in section 02 exists to quantify this: the City
records building permits for five of the nine downtown projects where HCD records
none. A completion always overrides a missing permit, because a building people
live in is not waiting to be built.

**Do not trust `APPLICATION_STATUS`.** Thirty parcels carry an approval date and a
`Pending` status simultaneously, including 2190 Shattuck, approved February 2019.
The date fields govern; the status column is only a note on the parcel card.

**Figures are computed, never typed.** The three exceptions are citations and are
labelled as such where they appear: Berkeley's RHNA allocation (ABAG plan), the
nine-project table (Council referral, 14 April 2026), and RAND's production times.
`tools/check.py` fails the build if a computed figure appears as a literal in the
markup.

**Two medians, deliberately.** Approval-to-permit is 1.6 years measured on projects
that got a permit and 3.3 years with the still-waiting ones treated as censored.
Both belong on the page — they answer different questions. Only the 1.6 figure is
comparable to the peer cities or to RAND, which measure completed projects the
same way. Do not quietly collapse them.

**`APN_SORT` is the join key**, not the parcel layer's own `APN` column, which uses
a different format and will not match HCD.

**`geo/` is cached on purpose.** Berkeley's ArcGIS server rate-limits hard — it
refused every request from this machine for about ten minutes after a few dozen
queries during development. Do not make the page fetch parcel geometry live.
`README.md` explains how to rebuild it.

**ZAB is parsed in CI, CEQAnet is fetched live.** `berkeleyca.gov` sends no CORS
header at all, so a browser cannot read the agenda PDFs however it asks;
`tools/fetch_zab.py` runs on a schedule and commits `data/zab.json`. CEQAnet sends
`Access-Control-Allow-Origin: *`, so that half is genuinely live.

## Colour

Run the dataviz palette validator before adding any series colour. Adjacent pairs
need ΔE ≥ 8 under colour-vision deficiency and ≥ 15 for normal vision. The bus
network and the "completed" series once collided at 5.9; every replacement hue
failed too, and the fix was to separate by lightness rather than hue, treating
buses as basemap context (`#3E6B78`, ΔE 26).

## Claims

This page is intended to withstand a hostile reading — the goal is to take it to
Berkeley City Council. Every number must be traceable to a public record, and
where the record is weak the page says so rather than rounding the doubt away.
Adding context has repeatedly moved figures *against* the page's own argument;
that is a good sign, and those corrections stay in. When a finding moves *for* the
argument, check it harder before shipping it.

Do not assert a source is unavailable without probing it. That has been wrong
repeatedly here — the error message is usually a hint, not a wall.
