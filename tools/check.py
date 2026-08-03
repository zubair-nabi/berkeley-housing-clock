#!/usr/bin/env python3
"""
Static checks on index.html. Run after every edit; run it in CI too.

The page is one 140KB file with the whole application inline, which makes it
easy to break in ways that do not look broken. Every check here exists because
something actually went wrong:

  size      an unanchored str.replace() once matched the empty string and
            injected a block between every character, producing a 24MB file
  syntax    a slice that ran to the wrong anchor deleted five functions; the
            file still parsed, so only a runtime error revealed it
  divs      lifting a block cut to the wrong closing tag, leaving 23 open and
            24 closed, which terminated a <section> early and silently
            orphaned three elements the renderer writes into
  ids       the same bug: the elements existed in the DOM but under the wrong
            section, so nothing threw and the page just looked wrong
  literals  figures belong in code that computes them, not in prose that goes
            stale the next time the data moves

Static checks cannot tell you an element landed in the wrong section -- for
that, load the page and run the DOM audit in CLAUDE.md.
"""
import json, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"

# Elements the renderer writes into. If one goes missing the page fails quietly.
REQUIRED_IDS = [
    "q", "res", "card", "secnav", "lede", "status", "cover",
    "clock", "axis", "peerlist", "censorbox", "censornote", "benchnote",
    "w-units", "w-parcels", "w-old", "w-oldest", "w-pending", "w-never",
    "rbar", "rkey", "wlist", "wmore", "xclist", "xcnote",
    "corrlist", "map", "mapstatus",
    "years", "ylabels", "findlist", "tierlist", "tiernote", "ucbox",
    "zablist", "ceqalist",
]

# Figures that must be computed at load time. A literal here means someone
# pasted a number into prose, and it will be wrong after the next data refresh.
# Written split so this file does not trip its own check.
FORBIDDEN_LITERALS = ["5" + ",636", "3" + ",243", "97 sites", "77 sites"]

MAX_BYTES = 400_000


def fail(msg):
    print(f"FAIL  {msg}")
    return 1


def main():
    if not HTML.exists():
        sys.exit(fail(f"{HTML} not found"))
    src = HTML.read_text()
    bad = 0

    size = len(src.encode())
    if size > MAX_BYTES:
        bad |= fail(f"index.html is {size:,} bytes, over the {MAX_BYTES:,} ceiling -- "
                    "a replace almost certainly matched more than intended")
    else:
        print(f"ok    size {size:,} bytes")

    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S)
    if not scripts:
        bad |= fail("no inline <script> found")
    for i, block in enumerate(scripts):
        if len(block.strip()) < 40:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as fh:
            fh.write(block)
            tmp = fh.name
        res = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        pathlib.Path(tmp).unlink()
        if res.returncode:
            bad |= fail(f"script block {i} is not valid JS\n{res.stderr.strip()[:800]}")
        else:
            print(f"ok    script block {i} parses ({len(block):,} chars)")

    sections = re.findall(r"<section\b.*?</section>", src, re.S)
    print(f"ok    {len(sections)} sections")
    for sec in sections:
        name = re.search(r'data-nav="([^"]+)"', sec)
        name = name.group(1) if name else "(unnamed)"
        opened = len(re.findall(r"<div\b", sec))
        closed = len(re.findall(r"</div>", sec))
        if opened != closed:
            bad |= fail(f'section "{name}" has {opened} <div> and {closed} </div> -- '
                        "it will terminate early and orphan whatever follows")

    ids = re.findall(r'\bid="([^"]+)"', src)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        bad |= fail(f"duplicate id attributes: {', '.join(dupes)}")
    missing = [i for i in REQUIRED_IDS if i not in ids]
    if missing:
        bad |= fail(f"required elements missing: {', '.join(missing)}")
    else:
        print(f"ok    all {len(REQUIRED_IDS)} required ids present, no duplicates")

    prose = re.sub(r"<script.*?</script>", "", src, flags=re.S)
    for lit in FORBIDDEN_LITERALS:
        if lit in prose:
            bad |= fail(f'"{lit}" is hard-coded in markup -- compute it instead')

    zab = ROOT / "data" / "zab.json"
    if zab.exists():
        try:
            meetings = json.loads(zab.read_text()).get("meetings", [])
            print(f"ok    data/zab.json parses, {len(meetings)} meetings")
        except Exception as exc:
            bad |= fail(f"data/zab.json is not valid JSON: {exc}")

    for geo in sorted((ROOT / "geo").glob("*.json")):
        try:
            json.loads(geo.read_text())
        except Exception as exc:
            bad |= fail(f"{geo.name} is not valid JSON: {exc}")
    print(f"ok    geo/ files parse")

    print("\nFAILED" if bad else "\nAll static checks passed. Now load the page and "
                                "run the DOM audit in CLAUDE.md -- these checks cannot "
                                "tell you an element landed in the wrong section.")
    return bad


if __name__ == "__main__":
    sys.exit(main())
