#!/usr/bin/env python3
"""Capture real result screenshots for DIY9lives tools.

Run from the repo root with a local server on port 8765:
    python3 -m http.server 8765
    python3 scripts/capture_screens.py

Requires Playwright and Pillow. Uses the installed Chrome channel when available.
Screenshots are written to img/screens/<slug>.webp at 1000 px wide.
"""
import os, sys
from playwright.sync_api import sync_playwright
from PIL import Image

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8765")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "img", "screens")
os.makedirs(OUT, exist_ok=True)

# slug: (selector, setup steps, alt text, caption)
# setup steps are (kind, selector, value). kind = fill | select | click
TOOLS = {
 "tire-size-calculator": ("#results", [], "Tire size calculator showing equivalent sizes for a 225/60R16 stock tire, with diameter differences and the speedometer reading at 60 mph", "Stock 225/60R16, result table for every wheel diameter."),
 "mortgage-calculator": (".result-big", [], "Mortgage calculator showing a $2,255 monthly payment on a $350,000 home with 20% down at 7%", "$350,000 home, 20% down, 7% for 30 years, $3,500 tax and $1,200 insurance."),
 "loan-calculator": (".result-big", [], "Loan calculator showing a $332 monthly payment on a $10,000 loan at 12% for 36 months", "$10,000 at 12% for 36 months."),
 "car-payment-calculator": (".result-big", [], "Car payment calculator showing a $634 monthly payment on a $35,000 car with $5,000 down at 6.9% for 60 months", "$35,000 car, $5,000 down, 6.9% for 60 months, including tax."),
 "home-affordability-calculator": (".result-hero", [], "Home affordability calculator showing a $300,242 affordable home price on a $90,000 income with $400 in monthly debts", "$90,000 income, $400 monthly debt, $30,000 down, 6.5%."),
 "debt-payoff-planner": ("#compareGrid", [], "Debt payoff planner comparing snowball and avalanche for three debts with an extra $200 a month", "Three debts, $200 extra per month, snowball versus avalanche."),
 "salary-calculator": (".result-big", [], "Salary calculator showing $3,665 monthly take-home pay on a $65,000 salary", "$65,000 salary, single filer, 6% 401(k), $150 monthly health premium."),
 "retirement-calculator": (".result-hero", [], "Retirement calculator projecting a $1,130,650 balance at 65 from $20,000 saved and $500 a month", "Age 30, retire at 65, $20,000 saved, $500 monthly, 7% return, 3% inflation."),
 "paint-calculator": (".result-big", [], "Paint calculator showing 2 gallons needed for a 12 by 10 foot room with 9 foot ceilings, two coats", "12 x 10 x 9 ft room, 2 doors, 1 window, two coats."),
 "concrete-calculator": (".result-big", [], "Concrete calculator showing 1.36 cubic yards for a 10 by 10 foot slab 4 inches thick with 10% extra", "10 x 10 ft slab, 4 inches thick, 10% extra."),
 "flooring-calculator": (".result-big", [], "Flooring calculator showing 15 boxes for a 16 by 14 living room and a 12 by 4 hallway with 10% waste", "16 x 14 ft living room plus 12 x 4 ft hallway, 10% waste, 20 sq ft per box."),
 "mulch-soil-gravel-calculator": (".result-big", [], "Mulch calculator showing 1.56 cubic yards for a 20 by 8 foot bed 3 inches deep", "20 x 8 ft bed, 3 inches deep, 2 cu ft bags, 5% extra."),
 "btu-calculator": (".result-big", [], "BTU calculator recommending an 8,000 BTU air conditioner for a 350 square foot room", "350 sq ft, 8 ft ceiling, two people, average sun, not a kitchen."),
 "recipe-scaler": ("#resultBox", [("fill", "#origServings", "4"), ("fill", "#newServings", "8"), ("dispatch", "#newServings", "input")], "Recipe scaler showing a recipe for four scaled to eight servings", "A four-serving recipe scaled to eight."),
 "unit-price-comparator": ("#productList", [("fill", "#prod1 input[type=text]", "12 oz jar"), ("fill", "#prod1 input[type=number] >> nth=0", "4.29"), ("fill", "#prod1 input[type=number] >> nth=1", "12"), ("fill", "#prod2 input[type=text]", "32 oz jar"), ("fill", "#prod2 input[type=number] >> nth=0", "9.49"), ("fill", "#prod2 input[type=number] >> nth=1", "32")], "Unit price comparator showing a 32 ounce jar at $0.297 per ounce beating a 12 ounce jar at $0.358 per ounce", "12 oz for $4.29 versus 32 oz for $9.49."),
 "cooking-measurement-converter": (".result-big", [], "Cooking measurement converter showing 1 cup of all-purpose flour equals 120 grams", "1 cup all-purpose flour to grams."),
 "compound-interest": (".result-big", [], "Compound interest calculator showing $44,665 after 10 years from $5,000 plus $200 a month at 7%", "$5,000 start, $200 monthly, 7%, 10 years, monthly compounding."),
 "rent-vs-buy-calculator": (".result-big", [], "Rent versus buy calculator showing buying cheaper by about $3,730 over seven years on a $400,000 house", "$400,000 house, 20% down, 6.5%, seven years, $2,200 rent."),
 "student-loan-calculator": ("#compareGrid", [], "Student loan calculator comparing a $350 payment with $100 extra on a $30,000 balance at 6%", "$30,000 at 6%, $350 payment, $100 extra."),
 "tip-calculator": (".result-big", [], "Tip calculator showing an $11.70 tip on a $65 bill at 18%, split two ways", "$65 bill, 18% tip, split two ways."),
 "percentage-calculator": (".big-grid", [], "Percentage calculator showing 15% of 200, 30 as a percent of 200, and a 25% increase", "15% of 200; 30 of 200; 80 to 100; add or remove 20%."),
 "out-the-door-price-calculator": (".result-big", [], "Out-the-door price calculator showing $34,590 on a $32,000 car with 5.75% tax and fees", "$32,000 car, no trade, 5.75% tax, $500 doc fee, $250 registration."),
}

def run():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 1100}, device_scale_factor=2)
        page.route("**/*", lambda route: route.abort()
                   if any(d in route.request.url for d in
                          ("googletagmanager", "googlesyndication", "google-analytics", "doubleclick"))
                   else route.continue_())
        for slug, (selector, steps, alt, caption) in TOOLS.items():
            page.goto(f"{BASE}/{slug}.html", wait_until="load")
            page.wait_for_timeout(400)
            for step in steps:
                kind, sel, val = step
                try:
                    if kind == "fill":
                        page.locator(sel).fill(val)
                    elif kind == "select":
                        page.locator(sel).select_option(val)
                    elif kind == "click":
                        page.locator(sel).click()
                    elif kind == "dispatch":
                        page.locator(sel).dispatch_event(val)
                    page.wait_for_timeout(120)
                except Exception as e:
                    errors.append(f"{slug}: step {step}: {e}")
            page.wait_for_timeout(300)
            png = os.path.join(OUT, slug + ".png")
            try:
                if slug == "tire-size-calculator":
                    # Capture the stock 16" group and the 18" upgrade group, stacked.
                    parts = [page.locator("#results .rim-group").nth(2),
                             page.locator("#results .rim-group").nth(4)]
                    widths, heights = [], []
                    for i, part in enumerate(parts):
                        part.screenshot(path=f"/tmp/tire_part_{i}.png")
                        pi = Image.open(f"/tmp/tire_part_{i}.png").convert("RGB")
                        widths.append(pi.width); heights.append(pi.height)
                    canvas = Image.new("RGB", (max(widths), sum(heights) + 20), (10, 10, 10))
                    y = 0
                    for i in range(len(parts)):
                        pi = Image.open(f"/tmp/tire_part_{i}.png").convert("RGB")
                        canvas.paste(pi, (0, y)); y += pi.height + 20
                    canvas.save(png)
                else:
                    page.locator(selector).first.screenshot(path=png)
            except Exception as e:
                errors.append(f"{slug}: screenshot {selector}: {e}")
                continue
            im = Image.open(png).convert("RGB")
            w, h = im.size
            if w > 1000:
                im = im.resize((1000, round(h * 1000 / w)), Image.LANCZOS)
            im.save(os.path.join(OUT, slug + ".webp"), "WEBP", quality=82, method=6)
            os.remove(png)
            print(f"{slug}: {im.size[0]}x{im.size[1]}")
        browser.close()
    for e in errors:
        print("ERROR", e, file=sys.stderr)
    if errors:
        sys.exit(1)

if __name__ == "__main__":
    run()
