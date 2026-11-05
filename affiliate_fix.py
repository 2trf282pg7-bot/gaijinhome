#!/usr/bin/env python3
"""
GaijinHome - affiliate link normalizer (idempotent).

- Rewrites untracked links to partner sites (oakhouse.jp, crossoneroom.com,
  placeholder a8.net/guide/... URLs) into tracked A8.net links.
- Inserts one [PR] "Recommended services" box per page (housing or
  connectivity set, chosen by topic), marked with <!-- gh-sponsor --> so it is
  only added once.

Run after generation: python affiliate_fix.py
"""

import glob
import os
import re

A8 = "https://px.a8.net/svt/ejp?a8mat="
LINKS = {
    "oakhouse": A8 + "4B1JDQ+DB9YR6+41A0+5Z6WX",
    "crossoneroom": A8 + "4B1JDQ+DCGTYQ+4EZ2+BYLJL",
    "wifi": A8 + "4B1JDQ+DOYXO2+42XQ+614CX",
    "esim": A8 + "4B1JDQ+DQ5SVM+5HZI+5YJRM",
    "italki": A8 + "4BGCF5+4KBNQQ+5NSE+5YRHE",
    "leopalace": A8 + "4BGCF5+4784FM+4YI4+5YJRM",
}

# href pattern -> partner key
REWRITES = [
    (r"https?://(?:www\.)?oakhouse\.(?:jp|co\.jp)[^\"]*", "oakhouse"),
    (r"https?://(?:www\.)?a8\.net/guide/oakhouse[^\"]*", "oakhouse"),
    (r"https?://(?:www\.)?crossoneroom\.com[^\"]*", "crossoneroom"),
    (r"https?://(?:www\.)?a8\.net/guide/crossoneroom[^\"]*", "crossoneroom"),
    (r"https?://(?:www\.)?italki\.com[^\"]*", "italki"),
]

HOUSING_BOX = [
    ("oakhouse", "Oakhouse — Share houses &amp; furnished rooms",
     "No Japanese guarantor needed, English support, short stays OK. Good fallback when a regular apartment rejects you."),
    ("crossoneroom", "CrossOneRoom — Furnished Tokyo apartments from ¥38,000",
     "Zero key money, zero agency fee, foreign residents welcome."),
    ("leopalace", "Leopalace21 — Furnished apartments, no agency fee",
     "One-room apartments with furniture and Wi-Fi nationwide; contracts from 30 days, paperwork can be done online."),
    ("italki", "italki — Japanese lessons with native tutors",
     "Learn the phrases you need for viewings, contracts and calls with your landlord."),
]
CONNECT_BOX = [
    ("esim", "JAPAN &amp; GLOBAL eSIM — Data from the day you land",
     "No contract or residence card needed. Useful while a phone contract is pending."),
    ("wifi", "WiFi Rental — Next-day delivery in Japan",
     "Unlimited data while you wait for home internet to be installed."),
    ("italki", "italki — Japanese lessons with native tutors",
     "Handle banks, ward offices and phone shops with more confidence."),
]
CONNECT_HINTS = ("bank", "credit", "card", "phone", "sim", "mobile", "internet",
                 "wifi", "visa", "residence", "tax", "pension", "insurance", "hospital")

MARK = "<!-- gh-sponsor -->"
QMARK = "<!-- gh-quickpick -->"

# Top-of-page picks for high-intent landing pages (page -> ordered partner keys)
QUICKPICK_PAGES = {"full-guide.html": ["crossoneroom", "oakhouse", "leopalace"]}
QUICKPICK_TEXT = {
    "oakhouse": ("Oakhouse", "Share houses &amp; furnished rooms across Japan. No Japanese guarantor, English support, short stays OK."),
    "crossoneroom": ("CrossOneRoom", "Furnished Tokyo apartments from about ¥38,000. Zero key money, zero agency fee, foreigners welcome."),
    "leopalace": ("Leopalace21", "Furnished one-room apartments nationwide, contracts from 30 days, no agency fee."),
}


def quickpick_for(filepath):
    keys = [k for k in QUICKPICK_PAGES.get(os.path.basename(filepath), []) if k in LINKS]
    if not keys:
        return None
    cards = "\n".join(
        f'    <a href="{LINKS[k]}" rel="nofollow sponsored noopener" target="_blank" '
        f'style="flex:1 1 200px;display:block;padding:12px 14px;border:1px solid #E4E2DC;border-radius:8px;'
        f'background:#fff;color:#1A1917;text-decoration:none;">'
        f'<strong style="color:#1B4D3E;">{QUICKPICK_TEXT[k][0]} →</strong><br>'
        f'<span style="font-size:0.88em;">{QUICKPICK_TEXT[k][1]}</span></a>'
        for k in keys)
    return (f"{QMARK}\n<div class=\"gh-quickpick\" style=\"margin:0 0 28px;padding:16px;background:#EBF3F0;"
            f"border-radius:10px;\">\n"
            f"  <p style=\"margin:0 0 4px;font-size:0.78em;color:#4A4845;\">[PR] Sponsored — we may earn a commission</p>\n"
            f"  <p style=\"margin:0 0 10px;font-weight:600;\">Need a gaijin-friendly apartment now? Start here:</p>\n"
            f"  <div style=\"display:flex;flex-wrap:wrap;gap:10px;\">\n{cards}\n  </div>\n</div>\n{QMARK}")


def page_paths():
    files = glob.glob("articles/*.html") + [
        f for f in ("full-guide.html", "no-guarantor.html", "rejected.html",
                    "hidden-costs.html", "osaka.html", "visa-guide.html") if os.path.exists(f)]
    return sorted(f for f in files if os.path.basename(f) != "index.html")


def box_for(filepath):
    name = os.path.basename(filepath).lower()
    items = CONNECT_BOX if any(h in name for h in CONNECT_HINTS) and "apartment" not in name else HOUSING_BOX
    cards = "\n".join(
        f'    <a href="{LINKS[key]}" rel="nofollow sponsored noopener" target="_blank" '
        f'style="display:block;padding:14px 16px;margin:10px 0;border:1px solid #e5ddd0;border-radius:8px;'
        f'background:#fff;color:#0F0E0C;text-decoration:none;">'
        f'<strong style="color:#E8372A;">{title} →</strong><br>'
        f'<span style="font-size:0.92em;">{desc}</span></a>'
        for key, title, desc in items)
    return (f"{MARK}\n<aside class=\"gh-sponsor\" style=\"max-width:760px;margin:40px auto;padding:20px;"
            f"background:#FDFAF5;border-left:4px solid #E8372A;font-family:inherit;\">\n"
            f"  <p style=\"margin:0 0 6px;font-size:0.8em;letter-spacing:.05em;color:#777;\">[PR] Sponsored — "
            f"we may earn a commission if you sign up</p>\n"
            f"  <h2 style=\"margin:0 0 8px;font-size:1.25em;\">Services that help in this situation</h2>\n"
            f"{cards}\n</aside>\n{MARK}")


def fix_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        html = f.read()
    original = html

    for pattern, key in REWRITES:
        html = re.sub(r'href="' + pattern + r'"', f'href="{LINKS[key]}"', html, flags=re.I)

    # sponsored rel on every tracked link
    def add_rel(m):
        tag = m.group(0)
        if "rel=" in tag:
            return re.sub(r'rel="[^"]*"', 'rel="nofollow sponsored noopener"', tag)
        return tag[:-1] + ' rel="nofollow sponsored noopener">'
    html = re.sub(r'<a\b[^>]*href="https://px\.a8\.net/[^"]*"[^>]*>', add_rel, html)

    # one sponsor box per page (replace if present so wording stays current)
    box = box_for(filepath)
    if MARK in html:
        html = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK), lambda _: box, html, flags=re.S)
    else:
        for anchor in ("<footer", "</main>", "</body>"):
            idx = html.lower().rfind(anchor.lower())
            if idx != -1:
                html = html[:idx] + box + "\n" + html[idx:]
                break
        else:
            # truncated page (no closing tags): close it so the box renders
            html = html.rstrip() + "\n</p></div></div></article>\n" + box + "\n</body>\n</html>\n"

    # quick picks at the top of selected landing pages
    qp = quickpick_for(filepath)
    if qp:
        if QMARK in html:
            html = re.sub(re.escape(QMARK) + r".*?" + re.escape(QMARK), lambda _: qp, html, flags=re.S)
        else:
            idx = html.find('<div class="article-body">')
            if idx != -1:
                idx += len('<div class="article-body">')
                html = html[:idx] + "\n" + qp + "\n" + html[idx:]

    if html != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    return False


def run_all():
    changed = [p for p in page_paths() if fix_file(p)]
    print(f"affiliate_fix: {len(changed)} file(s) updated")
    return changed


if __name__ == "__main__":
    run_all()
