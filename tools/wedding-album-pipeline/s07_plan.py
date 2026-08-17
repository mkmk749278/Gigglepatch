"""STAGE 7-8: STORY ORDER + ALBUM PAGE PLANNING.

Builds the page-by-page plan before any expensive editing happens, so only the
photographs that actually reach a page get processed.

Layout is chosen from the content of each group -- orientation mix, score spread
and role -- not from a fixed template rotation, and consecutive pages are pushed
apart so the book has rhythm instead of repeating one grid.

Writes analysis/album_plan.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import layout as L
from config import ANALYSIS
from curation import CROP_HINTS

# how many supporting frames a page should carry, cycled for rhythm
GROUP_CYCLE = [3, 2, 4, 2, 3, 5, 2, 3]


def effective_aspect(p):
    """Source aspect after any manual crop hint is applied."""
    w, h = p["width"], p["height"]
    hint = CROP_HINTS.get(p["file"])
    if hint:
        x0, y0, x1, y1 = hint
        w *= max(x1 - x0, 1e-6)
        h *= max(y1 - y0, 1e-6)
    return w / h


def pick(items, last_layout):
    """Delegate to the layout engine, which assigns photographs to cells by
    aspect fit rather than by hand-written orientation rules."""
    stubs = [{"aspect": effective_aspect(p), "final_score": p["final_score"]} for p in items]
    return L.choose_layout(stubs, last_layout=last_layout)


def main():
    sel = json.loads((ANALYSIS / "selections.json").read_text())
    photos = sel["selected"]
    chapters = {c["key"]: c for c in sel["chapters"]}
    by_file = {p["file"]: p for p in photos}

    pages = []          # each: {page numbers, layout, photos, purpose}
    page_no = 1

    def add_page(layout, items, purpose, chapter, title=None, subtitle=None, spread=False,
                 order=None):
        nonlocal page_no
        rec = {
            "pages": [page_no, page_no + 1] if spread else [page_no],
            "layout": layout,
            "chapter": chapter,
            "storytelling_purpose": purpose,
            "is_spread": spread,
            "hero": layout in ("full_bleed", "portrait_showcase", "spread") and len(items) == 1,
            "title": title, "subtitle": subtitle,
            "cell_order": order,
            "photos": [{"file": i["file"], "role": i["role"], "category": i["category"],
                        "orientation": i["orientation"],
                        "final_score": i["final_score"],
                        "crop_hint": CROP_HINTS.get(i["file"]),
                        "treatment": ("portrait" if (i["orientation"] == "portrait" or
                                                     layout in ("portrait_showcase", "portrait_pair"))
                                      else "landscape"),
                        "note": i["note"]} for i in items],
        }
        pages.append(rec)
        page_no += 2 if spread else 1
        return rec

    # ------------------------------------------------ cover
    cover_file = sel["cover"]["file"]
    add_page("cover", [by_file[cover_file]], "cover: introduce the couple", "front_matter",
             title="A Wedding in Telangana", subtitle=sel["cover"]["note"])

    # ------------------------------------------------ chapters
    last_layout = None
    for ch in sel["chapters"]:
        key = ch["key"]
        group = [p for p in photos if p["chapter"] == key
                 and p["role"] not in ("cover", "closing")]
        if not group:
            continue

        # Chapter opener: strongest hero, carrying the title. Frames marked as
        # spreads are deliberately NOT eligible -- a spread is the biggest
        # gesture available and must not be spent as a single-page opener.
        openers = [p for p in group if p["role"] == "hero"]
        if not openers:
            openers = [p for p in group if p["role"] not in ("spread",)]
        opener = max(openers, key=lambda p: p["final_score"])
        rest = [p for p in group if p is not opener]

        # A two-photograph chapter should not burn two consecutive full pages:
        # fold the single remaining supporting frame into the opener spread.
        fold = None
        if len(rest) == 1 and rest[0]["role"] in ("support", "detail"):
            fold = rest[0]
            rest = []

        if fold is not None:
            pair = [opener, fold]
            lay, order = pick(pair, last_layout)
            add_page(lay, pair, f"chapter opener: {ch['title']}", key,
                     title=ch["title"], subtitle=ch["dateline"], order=order)
            last_layout = lay
        else:
            lay, order = pick([opener], last_layout)
            add_page(lay, [opener], f"chapter opener: {ch['title']}", key,
                     title=ch["title"], subtitle=ch["dateline"], order=order)
            last_layout = lay

        # spreads next (they are the widest gestures in the chapter)
        for p in [x for x in rest if x["role"] == "spread"]:
            add_page("spread", [p], "double-page spread: hold on the moment", key,
                     title=ch["title"], spread=True)
            last_layout = "spread"
        rest = [x for x in rest if x["role"] != "spread"]

        # remaining heroes get their own page
        heroes = [x for x in rest if x["role"] == "hero"]
        rest = [x for x in rest if x["role"] != "hero"]

        # very strong close-ups earn a solo portrait page
        solo_portraits = [x for x in rest
                          if x["role"] == "portrait" and x["album_suitability"] >= 10]
        rest = [x for x in rest if x not in solo_portraits]

        # interleave singles with grouped pages for rhythm
        singles = sorted(heroes + solo_portraits, key=lambda p: p["datetime"] or "")
        rest.sort(key=lambda p: p["datetime"] or "")

        groups = []
        ci = 0
        i = 0
        while i < len(rest):
            size = GROUP_CYCLE[ci % len(GROUP_CYCLE)]
            ci += 1
            chunk = rest[i:i + size]
            if len(chunk) == 1 and groups:       # never leave an orphan
                groups[-1].extend(chunk)
            else:
                groups.append(chunk)
            i += size

        # Alternate single pages with grouped pages for rhythm. If the opener was
        # already a full-page single, lead with a grouped page so the book does
        # not show two consecutive full-bleed pages.
        if last_layout in ("full_bleed", "portrait_showcase") and groups:
            g = groups.pop(0)
            lay, order = pick(g, last_layout)
            add_page(lay, g, f"{len(g)}-photo editorial page", key, order=order)
            last_layout = lay

        while singles or groups:
            if singles:
                p = singles.pop(0)
                lay, order = pick([p], last_layout)
                add_page(lay, [p],
                         "hero page" if p["role"] == "hero" else "portrait treatment",
                         key, subtitle=None, order=order)
                last_layout = lay
            if groups:
                g = groups.pop(0)
                lay, order = pick(g, last_layout)
                add_page(lay, g, f"{len(g)}-photo editorial page", key, order=order)
                last_layout = lay

    # ------------------------------------------------ closing
    closing = by_file[sel["closing"]["file"]]
    add_page("closing", [closing], "closing image", "back_matter",
             title="With love")

    total_pages = page_no - 1
    plan = {
        "page_count": total_pages,
        "sheet_count": len(pages),
        "photo_count": sum(len(p["photos"]) for p in pages),
        "pages": pages,
    }
    (ANALYSIS / "album_plan.json").write_text(json.dumps(plan, indent=1))

    from collections import Counter
    print(f"planned {total_pages} pages ({len(pages)} layout sheets), "
          f"{plan['photo_count']} photo placements")
    print("\nlayouts used:", dict(Counter(p["layout"] for p in pages)))
    print("photos per sheet:", dict(sorted(Counter(len(p["photos"]) for p in pages).items())))
    print("\nplan:")
    for p in pages:
        rng = f"{p['pages'][0]:>3}" + (f"-{p['pages'][1]}" if p["is_spread"] else "   ")
        files = ",".join(x["file"][4:8] for x in p["photos"])
        print(f"  p{rng} {p['layout']:18} {p['chapter']:17} {files}")


if __name__ == "__main__":
    main()
