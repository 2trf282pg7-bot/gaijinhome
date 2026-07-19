#!/usr/bin/env python3
"""
GaijinHome - Internal link auto-updater

- Rebuilds articles/index.html (full article list, newest first)
- Refreshes the "Latest Articles" block in the root index.html
  (only the content between LATEST_ARTICLES_START/END markers is replaced)
- Keeps the "In-depth guides published" counter in sync with the
  actual number of articles
- insert_related_links() adds a "Related Articles" block to a newly
  generated article (same-category first, then most recent)

Called from generate_article.py after each new article, and safe to run
standalone: python update_links.py
"""

import glob
import html
import json
import os
import re
import subprocess
from datetime import datetime

ARTICLES_DIR = "articles"
ARTICLES_INDEX = os.path.join(ARTICLES_DIR, "index.html")
ROOT_INDEX = "index.html"
LATEST_COUNT = 6
RELATED_COUNT = 3
START_MARK = "<!-- LATEST_ARTICLES_START -->"
END_MARK = "<!-- LATEST_ARTICLES_END -->"

TAG_RULES = [
    ("guarantor", "No Guarantor"),
    ("share-house", "Share House"),
    ("deposit", "Costs"),
    ("key-money", "Costs"),
    ("hidden-cost", "Costs"),
    ("visa", "Visa"),
    ("osaka", "Osaka"),
    ("kyoto", "Kansai"),
    ("tokyo", "Tokyo"),
    ("eviction", "Legal"),
    ("credit-check", "Screening"),
    ("reject", "Screening"),
    ("denied", "Screening"),
    ("refus", "Screening"),
]


def article_files():
    files = glob.glob(os.path.join(ARTICLES_DIR, "*.html"))
    return [f for f in files if os.path.basename(f) != "index.html"]


def extract_title(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    m = re.search(r"<title>(.*?)</title>", content, re.S | re.I)
    if not m:
        return os.path.basename(filepath)
    title = html.unescape(m.group(1)).strip()
    # Drop "| Site Name" style suffixes for display
    return re.sub(r"\s*\|[^|]*$", "", title)


def article_date(filepath):
    """Date from the filename prefix, falling back to git / mtime."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})-", os.path.basename(filepath))
    if m:
        return m.group(1)
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%as", "--", filepath],
            capture_output=True, text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except OSError:
        pass
    return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")


def article_tag(filename):
    for needle, tag in TAG_RULES:
        if needle in filename:
            return tag
    return "Guide"


def format_date(iso_date):
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        return iso_date


def scan_articles():
    items = []
    for filepath in article_files():
        name = os.path.basename(filepath)
        items.append({
            "file": name,
            "title": extract_title(filepath),
            "date": article_date(filepath),
            "tag": article_tag(name),
        })
    items.sort(key=lambda a: (a["date"], a["file"]), reverse=True)
    return items


def load_category_map():
    """Map article slug -> keyword category, derived from keywords.json."""
    try:
        with open("keywords.json", "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    mapping = {}
    for category, keywords in data.items():
        for keyword in keywords:
            slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
            mapping[slug] = category
    return mapping


def article_slug(filename):
    name = re.sub(r"\.html$", "", filename)
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)


def render_card(article):
    return (
        f'<a href="/articles/{article["file"]}" class="article-card">'
        f'<span class="article-tag">{html.escape(article["tag"])}</span>'
        f'<h3>{html.escape(article["title"])}</h3>'
        f'<p class="date">{format_date(article["date"])}</p>'
        f'<span class="arrow">Read guide &rarr;</span></a>'
    )


def build_articles_index(articles):
    rows = "\n".join(
        '      <a href="/articles/{file}" class="list-row">'
        '<span class="list-tag">{tag}</span>'
        '<span class="list-title">{title}</span>'
        '<span class="list-date">{date}</span></a>'.format(
            file=a["file"],
            tag=html.escape(a["tag"]),
            title=html.escape(a["title"]),
            date=format_date(a["date"]),
        )
        for a in articles
    )
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>All Articles – GaijinHome</title>
<meta name="description" content="Every GaijinHome guide on renting in Japan as a foreigner — screening rejections, guarantor problems, deposits, key money, and more.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Literata:ital,wght@0,400;0,600;1,400&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{ --cream: #FAFAF7; --ink: #1A1917; --ink-mid: #4A4845; --ink-light: #8A8783; --border: #E4E2DC; --accent: #1B4D3E; --accent-light: #EBF3F0; color-scheme: light only; }}
  html {{ background: #FAFAF7; }}
  body {{ font-family: 'DM Sans', sans-serif; background: #FAFAF7; color: #1A1917; font-size: 15px; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
  nav {{ background: #fff; border-bottom: 1px solid #E4E2DC; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 60px; position: sticky; top: 0; z-index: 100; }}
  .logo {{ font-weight: 600; font-size: 20px; color: #1A1917; letter-spacing: -0.5px; text-decoration: none; flex-shrink: 0; }}
  .logo span {{ color: #1B4D3E; }}
  .nav-links {{ display: flex; gap: 20px; list-style: none; }}
  .nav-links a {{ text-decoration: none; color: #4A4845; font-size: 13px; font-weight: 500; white-space: nowrap; }}
  .nav-links a.active {{ color: #1B4D3E; font-weight: 600; }}
  .section {{ padding: 56px 40px 72px; max-width: 900px; margin: 0 auto; }}
  .section-label {{ font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #1B4D3E; margin-bottom: 8px; }}
  .section-title {{ font-family: 'Literata', Georgia, serif; font-size: 30px; font-weight: 600; color: #1A1917; letter-spacing: -0.3px; margin-bottom: 12px; }}
  .section-sub {{ color: #4A4845; font-size: 15px; margin-bottom: 36px; max-width: 520px; }}
  .article-list {{ background: #fff; border: 1px solid #E4E2DC; border-radius: 12px; overflow: hidden; }}
  .list-row {{ display: grid; grid-template-columns: 110px 1fr auto; gap: 16px; align-items: center; padding: 16px 20px; border-bottom: 1px solid #E4E2DC; text-decoration: none; }}
  .list-row:last-child {{ border-bottom: none; }}
  .list-row:hover {{ background: #FAFAF7; }}
  .list-tag {{ background: #EBF3F0; color: #1B4D3E; font-size: 10.5px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; padding: 3px 8px; border-radius: 4px; text-align: center; }}
  .list-title {{ font-size: 14px; font-weight: 600; color: #1A1917; line-height: 1.4; }}
  .list-date {{ font-size: 12.5px; color: #8A8783; white-space: nowrap; }}
  footer {{ background: #fff; border-top: 1px solid #E4E2DC; padding: 32px 40px; }}
  .footer-inner {{ max-width: 900px; margin: 0 auto; display: flex; justify-content: space-between; gap: 24px; flex-wrap: wrap; font-size: 12.5px; color: #8A8783; }}
  .footer-inner a {{ color: #4A4845; text-decoration: none; margin-right: 16px; }}
  @media (max-width: 768px) {{
    nav {{ padding: 0 16px; }}
    .nav-links {{ display: none; }}
    .section {{ padding: 40px 16px 56px; }}
    .section-title {{ font-size: 24px; }}
    .list-row {{ grid-template-columns: 1fr; gap: 6px; padding: 14px 16px; }}
    .list-tag {{ justify-self: start; }}
  }}
</style>
</head>
<body>
<nav>
  <a href="/" class="logo">Gaijin<span>Home</span></a>
  <ul class="nav-links">
    <li><a href="/full-guide.html">Full Guide</a></li>
    <li><a href="/no-guarantor.html">No Guarantor</a></li>
    <li><a href="/rejected.html">Got Rejected?</a></li>
    <li><a href="/hidden-costs.html">Hidden Costs</a></li>
    <li><a href="/osaka.html">Osaka &amp; Kansai</a></li>
    <li><a href="/visa-guide.html">Visa Guide</a></li>
    <li><a href="/articles/index.html" class="active">All Articles</a></li>
  </ul>
</nav>
<div class="section">
  <div class="section-label">Archive</div>
  <div class="section-title">All Articles</div>
  <div class="section-sub">{len(articles)} practical guides for foreigners renting in Japan — newest first.</div>
  <div class="article-list">
{rows}
  </div>
</div>
<footer>
  <div class="footer-inner">
    <span>&copy; 2026 GaijinHome. All rights reserved.</span>
    <span><a href="/">Home</a><a href="/articles/index.html">All Articles</a><a href="/privacy.html">Privacy Policy</a></span>
  </div>
</footer>
</body>
</html>
"""
    with open(ARTICLES_INDEX, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"✅ {ARTICLES_INDEX} rebuilt with {len(articles)} articles")


def update_root_index(articles):
    with open(ROOT_INDEX, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARK not in content or END_MARK not in content:
        print(f"⚠️  {ROOT_INDEX}: LATEST_ARTICLES markers not found, skipping latest-articles update")
    else:
        cards = "\n      ".join(render_card(a) for a in articles[:LATEST_COUNT])
        block = (
            f"{START_MARK}\n"
            f'    <div class="articles-grid">\n'
            f"      {cards}\n"
            f"    </div>\n"
            f"    {END_MARK}"
        )
        content = re.sub(
            re.escape(START_MARK) + r".*?" + re.escape(END_MARK),
            lambda _m: block,
            content,
            flags=re.S,
        )

    # Keep the "In-depth guides published" stat in sync
    content, n = re.subn(
        r'(<div class="stat-num">)\d+(</div><div class="stat-label">In-depth guides published)',
        lambda m: f"{m.group(1)}{len(articles)}{m.group(2)}",
        content,
    )
    if n == 0:
        print(f"⚠️  {ROOT_INDEX}: guide-count stat not found, skipping counter update")

    with open(ROOT_INDEX, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {ROOT_INDEX} updated (latest {min(LATEST_COUNT, len(articles))} articles, count={len(articles)})")


def insert_related_links(filepath, category=None, count=RELATED_COUNT):
    """Insert a "Related Articles" block (same category first, then most
    recent) before </body> of a newly generated article."""
    basename = os.path.basename(filepath)
    articles = [a for a in scan_articles() if a["file"] != basename]
    if not articles:
        return

    category_map = load_category_map()
    if category is None:
        category = category_map.get(article_slug(basename))

    same_cat = [a for a in articles if category and category_map.get(article_slug(a["file"])) == category]
    rest = [a for a in articles if a not in same_cat]
    related = (same_cat + rest)[:count]

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if 'class="related-articles"' in content:
        return

    items = "\n".join(
        f'    <li style="margin-bottom:8px;"><a href="/articles/{a["file"]}" '
        f'style="color:inherit;">{html.escape(a["title"])}</a> '
        f'<span style="opacity:0.6;font-size:0.85em;">({format_date(a["date"])})</span></li>'
        for a in related
    )
    block = (
        '\n<section class="related-articles" '
        'style="max-width:800px;margin:40px auto;padding:24px;'
        'border-top:1px solid rgba(0,0,0,0.15);">\n'
        "  <h2>Related Articles</h2>\n"
        f'  <ul style="margin-top:12px;padding-left:20px;">\n{items}\n  </ul>\n'
        "</section>\n"
    )

    idx = content.rfind("</body>")
    if idx == -1:
        content = content + block
    else:
        content = content[:idx] + block + content[idx:]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Related Articles block ({len(related)} links) inserted into {filepath}")


def update_all():
    articles = scan_articles()
    build_articles_index(articles)
    update_root_index(articles)
    return articles


if __name__ == "__main__":
    update_all()
