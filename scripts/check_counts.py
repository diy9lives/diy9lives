#!/usr/bin/env python3
"""Check the numbers that go stale when a tool or guide is added or removed.

Run from the project root before every push:

    python scripts/check_counts.py

It answers four questions and exits 1 if any answer is wrong:

  1. Does every "N free tools" claim match the number of indexable tool pages?
  2. Do the homepage section labels ("5 tools") match the cards in that section?
  3. Is every indexable tool page linked from the homepage, and is every
     homepage tool card pointing at a real, indexable page?
  4. Does sitemap.xml contain exactly the indexable pages (no more, no less)?

It also checks the guide count sentence on guides.html.

When you add a tool:
  - create the page without <meta name="robots" content="noindex">
  - add a card to index.html inside the right data-cat section
  - bump that section's cat-count, the search placeholder, the search count,
    the "Free tools" stat, "All (n)", and the og:image:alt line on the page
  - add the URL to sitemap.xml
Then run this script; it names whatever you missed.

The social preview image (og-image.png) has the count drawn into it by hand,
so the script cannot read it: regenerate it when the number changes.
"""

import json
import os
import re
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Pages that are not tools: site pages, category hubs, error page.
NON_TOOL = {
    "index.html", "about.html", "contact.html", "privacy.html", "terms.html",
    "disclaimer.html", "editorial.html", "guides.html", "home-tools.html",
    "money-tools.html", "car-tools.html", "kitchen-tools.html", "404.html",
}

WORDS = {20: "Twenty", 21: "Twenty-one", 22: "Twenty-two", 23: "Twenty-three",
         24: "Twenty-four", 25: "Twenty-five", 26: "Twenty-six", 27: "Twenty-seven",
         28: "Twenty-eight", 29: "Twenty-nine", 30: "Thirty"}

problems = []
checks = 0


def fail(msg):
    problems.append(msg)


def ok(msg):
    global checks
    checks += 1


def read(path):
    return open(path, encoding="utf-8", errors="ignore").read()


pages = [x.replace(os.sep, "/") for x in sorted(glob.glob("*.html")) + sorted(glob.glob("guides/*.html"))]
noindex = {p for p in pages if re.search(r'name="robots"[^>]*noindex', read(p)[:6000], re.I)}
tools = sorted(p for p in pages if "/" not in p and p not in NON_TOOL and p not in noindex)
guides = sorted(p for p in pages if p.startswith("guides/"))
guide_count = len(guides)

# 1. every "N free tools" claim
claims = {}
for p in pages:
    for m in re.finditer(r"(\d+)\s+free tools", read(p)):
        claims.setdefault(int(m.group(1)), set()).add(p)
for n, where in claims.items():
    if n != len(tools):
        sample = ", ".join(sorted(where)[:4])
        fail('"%d free tools" appears in %d files but there are %d indexable tools (e.g. %s)'
             % (n, len(where), len(tools), sample))
if claims:
    ok("free-tool claims match %d tools" % len(tools))

# 2. homepage section labels and cards
idx = read("index.html")
sections = re.findall(
    r'<div class="cat-section" data-cat="([a-z]+)">(.*?)\n</div>\n</div>', idx, re.S)
section_total = 0
for cat, body in sections:
    cards = len(re.findall(r'class="tc"', body))
    section_total += cards
    label = re.search(r'cat-count">(\d+)', body)
    if label and int(label.group(1)) != cards:
        fail("homepage section '%s' says %s but holds %d cards" % (cat, label.group(1), cards))
    for href in re.findall(r'<a class="tc" href="(/[^"]+)"', body):
        target = href.lstrip("/")
        if target in NON_TOOL or target in noindex or not os.path.exists(target):
            fail("homepage card points at %s, which is not an indexable page" % href)
    cats = set(re.findall(r'data-cat="([a-z]+)"', body))
    if cats - {cat}:
        fail("card inside '%s' declares data-cat %s" % (cat, cats - {cat}))
ok("homepage sections parsed")

search_n = re.search(r'>(\d+) free tools available<', idx)
if search_n and int(search_n.group(1)) != len(tools):
    fail('search counter says %s, tools are %d' % (search_n.group(1), len(tools)))
placeholder = re.search(r'placeholder="Search (\d+) free tools', idx)
if placeholder and int(placeholder.group(1)) != len(tools):
    fail('search placeholder says %s, tools are %d' % (placeholder.group(1), len(tools)))
all_tab = re.search(r'All \((\d+)\)', idx)
cards_total = len(re.findall(r'class="tc"', idx))
if all_tab and int(all_tab.group(1)) != cards_total:
    fail('"All (%s)" tab does not match %d cards' % (all_tab.group(1), cards_total))

# 3. every indexable tool linked from the homepage
for t in tools:
    if 'href="/%s"' % t not in idx:
        fail("%s is indexable but has no homepage card" % t)

# 4. sitemap = indexable pages, exactly
sitemap = read("sitemap.xml")
locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
listed = {u.split("diy9lives.com")[-1].lstrip("/") or "index.html" for u in locs}
expected = {p for p in pages if p not in noindex}
for missing in sorted(expected - listed):
    fail("indexable page missing from sitemap: %s" % missing)
for extra in sorted(listed - expected):
    fail("sitemap lists a page that is missing or noindexed: %s" % extra)
if len(locs) != len(listed):
    fail("sitemap has duplicate URLs (%d entries, %d unique)" % (len(locs), len(listed)))

# guides sentence on guides.html
g = read("guides.html")
m = re.search(r"<p class=\"sub\">([A-Za-z-]+) guides", g)
if m:
    expected_word = WORDS.get(guide_count)
    if expected_word and m.group(1) != expected_word:
        fail('guides.html says "%s guides" but there are %d' % (m.group(1), guide_count))
    elif expected_word:
        ok("guides.html says %d guides" % guide_count)
tw = re.search(r'content="([A-Za-z-]+) guides that take', g)
if tw and WORDS.get(guide_count) and tw.group(1) != WORDS[guide_count]:
    fail('guides.html twitter description says "%s guides", there are %d' % (tw.group(1), guide_count))

print("indexable tools: %d | guides: %d | sitemap URLs: %d | homepage cards: %d"
      % (len(tools), guide_count, len(locs), cards_total))
if problems:
    print("\n%d problem(s):" % len(problems))
    for p in problems:
        print("  - " + p)
    print("\nReminder: og-image.png has the tool count drawn into it. Regenerate it if the number changed.")
    sys.exit(1)
print("All counts consistent.")
