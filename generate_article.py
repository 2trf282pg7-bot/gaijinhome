#!/usr/bin/env python3
"""
GaijinHome - Automated SEO article generator.

Topic selection is area x problem-type based and driven entirely by
config/areas_config.json (see that file to add cities / angles / affiliates).

Flow:
  1. Build the set of already-used (area, problem_type) pairs from
     done_topics.json AND a best-effort scan of existing article slugs.
  2. Pick the next unused pair: Tier A -> Tier B -> Tokyo wards, rotating the
     problem type so the same angle never runs twice in a row. When every pair
     is used, start a fresh round through Tier A with a different angle.
  3. Generate English HTML with claude-haiku-4-5 using a quality-enforced prompt
     (real rent ranges, move-in cost breakdown, no-guarantor methods, step flow,
     FAQ, anti-hallucination rules).
  4. Post-process: strip code fences, inject Related articles, append the correct
     affiliate cards + disclosure for the area's tier (Tier B never gets housing
     affiliates), then write the file and update the sitemap.

Model and cadence are intentionally unchanged (claude-haiku-4-5, existing cron).
"""
import anthropic
import os
import re
import json
import glob
import random
from datetime import datetime

CONFIG_PATH = "config/areas_config.json"
STATE_PATH = "done_topics.json"

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-haiku-4-5-20251001"


# --------------------------------------------------------------------------- #
# Config / state
# --------------------------------------------------------------------------- #
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    """Return the list of used {area, problem_type} pairs."""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    return []


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def tier_of(area, config):
    for tier_name in config["selection_order"]:
        if area in config["tiers"][tier_name]:
            return tier_name
    return None


def is_tokyo_area(area, config):
    """Tokyo itself or any of its wards (drives CrossOneRoom placement)."""
    return area == "Tokyo" or area in config["tiers"]["tokyo_wards"]


def fill_title(problem_type, area):
    return problem_type["title"].replace("{Area}", area).replace("{City}", area)


def pair_key(area, ptype_id):
    return f"{area}::{ptype_id}"


# --------------------------------------------------------------------------- #
# Used-pair detection
# --------------------------------------------------------------------------- #
def scan_existing_pairs(config):
    """
    Best-effort: infer (area, problem_type) pairs already covered by existing
    HTML (root guides + articles/) so we never regenerate a topic that already
    exists on the site, even if it predates done_topics.json.
    """
    used = set()
    all_areas = (
        config["tiers"]["tier_a"]
        + config["tiers"]["tier_b"]
        + config["tiers"]["tokyo_wards"]
    )
    files = glob.glob("articles/*.html") + glob.glob("*.html")
    for path in files:
        slug = os.path.basename(path).lower().replace(".html", "")
        # Strip a leading YYYY-MM-DD- date prefix if present.
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
        for area in all_areas:
            if area.lower() not in slug:
                continue
            for ptype in config["problem_types"]:
                if any(kw in slug for kw in ptype["match_keywords"]):
                    used.add(pair_key(area, ptype["id"]))
    return used


def build_used_set(config, state):
    used = scan_existing_pairs(config)
    for entry in state:
        used.add(pair_key(entry["area"], entry["problem_type"]))
    return used


# --------------------------------------------------------------------------- #
# Selection algorithm
# --------------------------------------------------------------------------- #
def select_topic(config, state):
    """
    Tier A -> Tier B -> Tokyo wards (a tier is only entered once the previous
    one has no unused pairs left). Within a tier we spread geographically by
    picking the least-covered area first, and we rotate the problem type so the
    same angle never runs twice in a row.

    Returns (area, problem_type, is_fresh_round) or (None, None, False).
    """
    used = build_used_set(config, state)
    ptypes = config["problem_types"]
    last_ptype = state[-1]["problem_type"] if state else None

    def coverage(area):
        return sum(1 for p in ptypes if pair_key(area, p["id"]) in used)

    def ordered_ptypes(area):
        pts = [p for p in ptypes if pair_key(area, p["id"]) not in used]
        random.shuffle(pts)
        # De-prioritise repeating the previous angle.
        pts.sort(key=lambda p: 1 if p["id"] == last_ptype else 0)
        return pts

    # Pass 1: respect tier order; within the first tier that still has an unused
    # pair, choose the least-covered area, then a fresh angle for it.
    for tier_name in config["selection_order"]:
        areas = [a for a in config["tiers"][tier_name]
                 if coverage(a) < len(ptypes)]
        if not areas:
            continue
        areas.sort(key=lambda a: (coverage(a), config["tiers"][tier_name].index(a)))
        area = areas[0]
        return area, ordered_ptypes(area)[0], False

    # Pass 2: every pair used -> fresh round. Restart from Tier A, least-covered
    # area overall, varying the angle relative to the last article.
    for tier_name in config["selection_order"]:
        areas = config["tiers"][tier_name]
        if not areas:
            continue
        area = areas[0]
        choices = [p for p in ptypes if p["id"] != last_ptype] or ptypes
        return area, random.choice(choices), True

    # Absolute fallback.
    area = config["tiers"]["tier_a"][0]
    return area, ptypes[0], True


# --------------------------------------------------------------------------- #
# Affiliate resolution
# --------------------------------------------------------------------------- #
def resolve_affiliates(config, area, problem_type):
    """Return the ordered list of affiliate ids this article should feature."""
    tier_name = tier_of(area, config)
    rules = config["tier_affiliate_rules"][tier_name]
    contexts = set(problem_type["contexts"])

    aff_ids = []
    housing_contexts = {"housing", "sharehouse", "budget"}
    if contexts & housing_contexts:
        aff_ids.extend(rules["housing_affiliates"])
        if is_tokyo_area(area, config):
            aff_ids.extend(rules["tokyo_only_affiliates"])
    # Connectivity (eSIM/WiFi) applies to every article.
    aff_ids.extend(rules["connectivity_affiliates"])

    # De-dup, preserve order.
    seen = set()
    ordered = []
    for aid in aff_ids:
        if aid not in seen:
            seen.add(aid)
            ordered.append(aid)
    return ordered


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #
ARTICLE_SYSTEM_PROMPT = """You write English relocation/housing guides for foreigners moving to or living in Japan. The reader is making a real decision (where to live, how to rent) and needs concrete, trustworthy, locally specific information — not a generic overview.

DESIGN (match the GaijinHome brand exactly):
- Output a complete, standalone, valid HTML5 document (<!DOCTYPE html> ... </html>).
- Palette: red #E8372A, dark ink #0F0E0C, cream #FDFAF5. Headings in 'Syne', body in 'DM Sans' (load both from Google Fonts).
- Include a <nav> linking to / and the main guides, and a footer.
- Clean, readable, mobile-friendly CSS in a <style> block.

MANDATORY CONTENT (every article MUST contain all of these):
1. The area's real rent ranges as concrete amounts, e.g. "1K ¥50,000–¥80,000/month", with a small table covering at least 1K/1LDK/2LDK or studio/1BR/family.
2. A move-in cost breakdown in real numbers: deposit (敷金), key money (礼金), guarantor company fee, agency fee (仲介手数料), first month's rent — with typical multiples and a worked example total.
3. At least THREE concrete ways to rent without a personal guarantor (guarantor company, foreigner-focused services, share houses, UR housing, etc.).
4. A numbered, step-by-step flow from application to move-in.
5. An FAQ section of exactly 5 question/answer pairs written for "People Also Ask" (real questions a foreigner would type), plus matching FAQPage JSON-LD schema in the <head>.
6. A concrete description of the area: access/train lines, foreigner community, universities, daily-life feel.
7. Length: 1,200–1,800 words of body content. Not thinner, not padded.

ANTI-HALLUCINATION RULES (strict):
- NEVER invent specific property names, real-estate company addresses, or phone numbers.
- For uncertain proper nouns, hedge: "companies like…", "services such as our partner Oakhouse".
- Only state verifiable specifics: area names, station/line names, general cost structures, visa basics, and laws. Rent figures are typical ranges, not quotes for a specific unit — frame them as ranges/estimates.
- Do not promise availability, prices, or approval outcomes.

Write naturally and helpfully. Output ONLY the HTML document — no markdown, no code fences, no commentary."""


def build_user_prompt(area, problem_type, title, affiliates, config):
    aff_lines = []
    for aid in affiliates:
        a = config["affiliates"][aid]
        aff_lines.append(f'- {a["name"]}: {a["url"]} ({a["desc"]})')
    aff_block = "\n".join(aff_lines)

    tier_name = tier_of(area, config)
    if config["tier_affiliate_rules"][tier_name]["housing_affiliates"] or any(
        config["affiliates"][a]["name"] in ("Oakhouse", "CrossOneRoom") for a in affiliates
    ):
        housing_note = (
            "Place contextual inline affiliate links at genuine decision points in the body "
            "(e.g. when discussing share houses, low-budget options, or the no-guarantor route). "
            "If you include a 'share house vs standard rental' comparison, link the housing option there. "
            "Use the EXACT URLs above with rel=\"nofollow\". Do NOT only put links at the end."
        )
    else:
        housing_note = (
            "This area has NO housing affiliate. Do NOT mention or link Oakhouse or CrossOneRoom. "
            "Write the no-guarantor / foreigner-OK property section as neutral general guidance "
            "(how guarantor companies work, how to find foreigner-friendly listings). "
            "Place the eSIM/WiFi links inline where you discuss arriving, moving in, or staying connected, "
            "using the EXACT URLs above with rel=\"nofollow\"."
        )

    return (
        f'Write the complete HTML article now.\n'
        f'H1 / topic: "{title}"\n'
        f'Area: {area}\n'
        f'Year context: 2026.\n\n'
        f'The <head> must include a meta description that opens with a hook for someone '
        f'actively searching (e.g. "Looking for", "Renting in", "Struggling to"), relevant meta tags, '
        f'and FAQPage JSON-LD schema.\n\n'
        f'Affiliates available for THIS article (use these exact URLs only):\n{aff_block}\n\n'
        f'{housing_note}\n\n'
        f'Do NOT add a final "Related articles" list or an affiliate-disclosure paragraph — '
        f'those are appended automatically. Focus on the body, inline links, and the FAQ.'
    )


# --------------------------------------------------------------------------- #
# Generation + post-processing
# --------------------------------------------------------------------------- #
def strip_code_fences(text):
    """Remove a leading ```html / ``` fence and trailing ``` if present."""
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
    t = re.sub(r"\n```\s*$", "", t)
    return t.strip()


def affiliate_cards_html(affiliates, config):
    """Deterministic, correctly-tracked affiliate card block (self-styled)."""
    cards = []
    for aid in affiliates:
        a = config["affiliates"][aid]
        cards.append(
            '<div style="background:#fff;border:1px solid #e0d9cf;border-radius:12px;'
            'padding:18px 20px;margin:12px 0;display:flex;justify-content:space-between;'
            'align-items:center;gap:16px;flex-wrap:wrap">'
            f'<div style="flex:1;min-width:200px"><div style="font-family:\'Syne\',sans-serif;'
            f'font-weight:700;color:#0F0E0C;margin-bottom:4px">{a["name"]} '
            '<span style="font-size:0.7rem;color:#7a7570;font-weight:600">[PR]</span></div>'
            f'<div style="font-size:0.88rem;color:#555;line-height:1.5">{a["desc"]}</div></div>'
            f'<a href="{a["url"]}" rel="nofollow sponsored" '
            'style="background:#E8372A;color:#fff;text-decoration:none;font-family:\'Syne\',sans-serif;'
            f'font-weight:700;padding:10px 18px;border-radius:8px;white-space:nowrap">{a["cta"]} &rarr;</a>'
            f'<img width="1" height="1" style="display:none" alt="" src="{a["pixel"]}">'
            '</div>'
        )
    return (
        '<section style="margin:48px 0 8px">'
        '<h2 style="color:#E8372A;font-family:\'Syne\',sans-serif">Recommended Services</h2>'
        + "".join(cards)
        + "</section>"
    )


def related_articles_html(area, problem_type, config):
    """
    Internal links: same-city articles first, then same-angle articles in other
    cities, padded with evergreen guide seeds. Up to 4 links.
    """
    candidates = []
    files = sorted(glob.glob("articles/*.html"))
    for path in files:
        fname = os.path.basename(path)
        slug = fname.lower().replace(".html", "")
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
        title = extract_title(path) or slug.replace("-", " ").title()
        url = f"/articles/{fname}"

        same_city = area.lower() in slug
        same_angle = any(kw in slug for kw in problem_type["match_keywords"])
        # Skip a link to the page we are about to (re)create.
        if same_city and same_angle:
            continue
        if same_city:
            candidates.append((0, title, url))
        elif same_angle:
            candidates.append((1, title, url))

    candidates.sort(key=lambda c: c[0])
    links = []
    seen = set()
    for _, title, url in candidates:
        if url in seen:
            continue
        seen.add(url)
        links.append((title, url))
        if len(links) >= 4:
            break

    for seed in config.get("internal_link_seeds", []):
        if len(links) >= 4:
            break
        if seed["url"] in seen:
            continue
        seen.add(seed["url"])
        links.append((seed["title"], seed["url"]))

    items = "".join(
        f'<li style="margin-bottom:8px"><a href="{url}" '
        f'style="color:#E8372A;text-decoration:none;font-weight:600">{title}</a></li>'
        for title, url in links
    )
    return (
        '<section style="margin:48px 0 8px">'
        '<h2 style="color:#E8372A;font-family:\'Syne\',sans-serif">Related Articles</h2>'
        f'<ul style="padding-left:20px;line-height:1.8">{items}</ul>'
        "</section>"
    )


def disclosure_html(config):
    return (
        '<aside style="margin:32px 0 0;padding:16px 20px;background:#F5F0E8;'
        'border-left:3px solid #E8372A;border-radius:0 8px 8px 0;font-size:0.85rem;color:#555">'
        f'{config["affiliate_disclosure"]}</aside>'
    )


def extract_title(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(4000)
        m = re.search(r"<title>(.*?)</title>", head, re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"\s*\|\s*GaijinHome.*$", "", m.group(1).strip())
    except OSError:
        pass
    return None


def strip_housing_affiliates(html, config):
    """Safety net: ensure Tier B articles carry no housing affiliate links."""
    for aid in ("oakhouse", "crossoneroom"):
        a = config["affiliates"][aid]
        if a["url"] in html:
            html = html.replace(a["url"], "#")
        if a["pixel"] in html:
            html = html.replace(a["pixel"], "")
    return html


def assemble(html, area, problem_type, affiliates, config):
    html = strip_code_fences(html)

    tier_name = tier_of(area, config)
    housing_allowed = bool(config["tier_affiliate_rules"][tier_name]["housing_affiliates"])
    if not housing_allowed:
        html = strip_housing_affiliates(html, config)

    blocks = (
        related_articles_html(area, problem_type, config)
        + affiliate_cards_html(affiliates, config)
        + disclosure_html(config)
    )
    if "</body>" in html:
        html = html.replace("</body>", blocks + "\n</body>", 1)
    else:
        html = html + blocks
    return html


def generate(area, problem_type, title, affiliates, config):
    user_prompt = build_user_prompt(area, problem_type, title, affiliates, config)
    print(f"Generating: {title}  [area={area}, type={problem_type['id']}, "
          f"affiliates={affiliates}]")
    message = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def save_article(filename, content):
    os.makedirs("articles", exist_ok=True)
    filepath = f"articles/{filename}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved: {filepath}")
    return filepath


def update_sitemap(new_filename):
    sitemap_path = "sitemap.xml"
    url = f"https://gaijinhome.com/articles/{new_filename}"
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = (
        f"  <url>\n    <loc>{url}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <priority>0.8</priority>\n  </url>"
    )
    if os.path.exists(sitemap_path):
        with open(sitemap_path, "r", encoding="utf-8") as f:
            content = f.read()
        if url not in content:
            content = content.replace("</urlset>", f"{new_entry}\n</urlset>")
            with open(sitemap_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Sitemap updated: {url}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    config = load_config()
    state = load_state()
    print(f"Recorded topics: {len(state)}")

    area, problem_type, fresh = select_topic(config, state)
    if not area:
        print("No topic could be selected.")
        return
    if fresh:
        print("All pairs used — starting a fresh round.")

    title = fill_title(problem_type, area)
    affiliates = resolve_affiliates(config, area, problem_type)

    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{slugify(title)}.html"
    if os.path.exists(f"articles/{filename}"):
        print(f"Article already exists: {filename}, skipping.")
        return

    raw = generate(area, problem_type, title, affiliates, config)
    html = assemble(raw, area, problem_type, affiliates, config)
    save_article(filename, html)
    update_sitemap(filename)

    state.append({
        "area": area,
        "problem_type": problem_type["id"],
        "title": title,
        "filename": filename,
        "tier": tier_of(area, config),
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    save_state(state)

    print(f"\n✅ Done: articles/{filename}")


if __name__ == "__main__":
    main()
