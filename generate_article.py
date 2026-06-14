#!/usr/bin/env python3
import anthropic
import os
import re
import json
import glob
import sys
import html
from datetime import datetime

# In --dry-run mode no API key is required and no API calls are made.
DRY_RUN = "--dry-run" in sys.argv

client = None
if not DRY_RUN:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

ARTICLE_SYSTEM_PROMPT = """You are writing for foreigners who are CURRENTLY STUCK with a
specific bureaucratic or practical problem in Japan.
They are not browsing for information — they are frustrated
and searching for an immediate solution.

ALWAYS include:
- Specific failure cases and exact reasons why things go wrong
- Concrete workarounds and alternative options
- Document checklists with exact names
- City-specific differences where applicable (Tokyo vs Osaka etc)
- Real-world exceptions and edge cases that generic guides miss

NEVER write:
- Generic "overview of X in Japan" introductions
- "Top 10 best..." or "Best X for foreigners" lists
- Vague advice like "contact the relevant authority"
- Content that ChatGPT could answer in one sentence
- Broad keyword targeting (best / guide / how to find)

Tone: Direct, practical, empathetic to someone who is
frustrated and needs help right now.

Article structure (follow exactly):
H1: [Specific problem statement with "rejected" / "denied" /
     "problem" / "confusion" / "what to do"]

1. What actually happens
   (Describe the exact situation the reader is stuck in)
2. Why it happens
   (Structural reasons — not obvious, not generic)
3. Common mistakes
   (3-5 specific mistakes foreigners make)
4. Step-by-step fix
   (Exact steps, exact documents, exact alternatives)
5. Required documents
   (Checklist format)
6. City / region differences
   (Tokyo vs Osaka vs other cities where relevant)
7. Recommended services
   (Affiliate links placed naturally with [PR] disclosure)

Use red (#E8372A), dark ink (#0F0E0C), cream (#FDFAF5), Syne font.
Include internal links to /guide-complete.html, /guide-no-guarantor.html, /guide-rejection.html,
/guide-hidden-costs.html, /guide-osaka-kansai.html, /guide-visa-breakdown.html.
1500-2500 words. Output ONLY valid HTML."""

AFFILIATE_BY_CATEGORY = {
    "category_a_housing": ["Oakhouse (A8.net)", "CrossOneRoom (A8.net)"],
    "category_b_banking": ["Wise", "Revolut"],
    "category_c_phone": ["JAPAN&GLOBAL eSIM (A8.net)", "WiFiレンタル嬢さん (A8.net)"],
    "category_d_visa": ["JAPAN&GLOBAL eSIM (A8.net)"],
    "category_e_daily": ["JAPAN&GLOBAL eSIM (A8.net)", "WiFiレンタル嬢さん (A8.net)"],
}


def load_keywords():
    """Load keyword list from keywords.json."""
    with open("keywords.json", "r") as f:
        return json.load(f)


def load_done_keywords():
    """Load already-processed keywords."""
    if os.path.exists("done_keywords.json"):
        with open("done_keywords.json", "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    return []


def save_done_keywords(done):
    with open("done_keywords.json", "w") as f:
        json.dump(done, f, ensure_ascii=False, indent=2)


def get_next_keyword(keywords_data, done_keywords):
    """Find the next unused keyword across all categories."""
    for category, keywords in keywords_data.items():
        for keyword in keywords:
            if keyword not in done_keywords:
                return keyword, category
    return None, None


VALID_CATEGORIES = {
    "category_a_housing",
    "category_b_banking",
    "category_c_phone",
    "category_d_visa",
    "category_e_daily",
}


def extract_title(html_content):
    """Pull the text inside the first <title> tag, if any."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html_content,
                      re.IGNORECASE | re.DOTALL)
    if match:
        return html.unescape(match.group(1).strip())
    return None


def collect_article_titles():
    """Scan articles/*.html (excluding index.html) and return their <title> text."""
    titles = []
    for filepath in sorted(glob.glob("articles/*.html")):
        if os.path.basename(filepath) == "index.html":
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                title = extract_title(f.read())
        except OSError:
            title = None
        if title:
            titles.append(title)
    return titles


def generate_new_topic():
    """Autonomously pick a brand-new topic once keywords.json is exhausted.

    Asks Haiku for a single problem-solving topic that does not overlap with
    existing articles, and returns (keyword, category).
    """
    existing_titles = collect_article_titles()
    existing_list = "\n".join(f"- {t}" for t in existing_titles) or "(none yet)"

    prompt = (
        "日本に住む外国人向けの問題解決記事のトピックを1つ生成してください。\n"
        f"すでに存在するトピック一覧:\n{existing_list}\n"
        "条件:\n"
        "- 必ず「rejected / denied / problem / confusion / what to do」のいずれかを含む\n"
        "- 住宅・銀行・電話/SIM・ビザ・日常生活のいずれかのカテゴリ\n"
        "- 既存トピックと重複しない\n"
        "- 英語で返答\n"
        'JSONで返答: {"keyword": "...", "category": "category_a_housing"}'
    )

    if DRY_RUN:
        # No API call in dry-run; return a deterministic placeholder.
        keyword = "[dry-run autonomous topic placeholder]"
        category = "category_a_housing"
        print("[dry-run] generate_new_topic() prompt:")
        print(prompt)
        print(f"[dry-run] would use keyword='{keyword}', category='{category}'")
        return keyword, category

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    # The model may wrap JSON in code fences; extract the JSON object.
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        raise ValueError(f"generate_new_topic: no JSON in response: {raw!r}")
    data = json.loads(json_match.group(0))

    keyword = data["keyword"].strip()
    category = data.get("category", "").strip()
    if category not in VALID_CATEGORIES:
        category = "category_e_daily"

    print(f"Autonomous topic: {keyword} (category: {category})")
    return keyword, category


def keyword_to_title(keyword):
    """Transform keyword into a problem-solving title."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"""Transform this keyword into a problem-solving article title for foreigners in Japan.
Keyword: {keyword}

Rules:
- Must include one of: "rejected" / "denied" / "problem" / "confusion" / "what to do"
- Use question form or problem statement
- NO "Best", "Guide", "How to Find", "Complete"

Examples:
OK: "Why Your Apartment Application Was Rejected in Japan"
OK: "Bank Account Denied in Japan? Here's What to Do"
OK: "Phone Contract Refused in Japan: Exact Reasons and Fixes"

Reply with ONLY the title, nothing else."""
        }]
    )
    return response.content[0].text.strip().strip('"')


def topic_to_filename(keyword):
    slug = re.sub(r'[^a-z0-9]+', '-', keyword.lower()).strip('-')
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    return f"{date_prefix}-{slug}.html"


def generate_article(keyword, category, title):
    affiliates = AFFILIATE_BY_CATEGORY.get(category, ["JAPAN&GLOBAL eSIM (A8.net)"])
    affiliate_note = (
        f"For the Recommended Services section, feature these affiliates naturally with [PR] disclosure: "
        f"{', '.join(affiliates)}. Place one affiliate mention inside the Step-by-step fix section "
        f"and up to 3 in the Recommended Services section."
    )

    print(f"Generating article for: {keyword} (category: {category})")
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f'Write a complete HTML article. Title: "{title}". '
                f'Target keyword: "{keyword}". '
                f'{affiliate_note} '
                f'Include proper head with meta description starting with "If your" or '
                f'"Confused about" or "Struggling with", meta tags, and FAQ with schema markup. '
                f'Year: 2026.'
            )
        }]
    )
    return message.content[0].text


def save_article(filename, content):
    os.makedirs("articles", exist_ok=True)
    filepath = f"articles/{filename}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved: {filepath}")
    return filepath


def update_sitemap(new_filename):
    url = f"https://gaijinhome.com/articles/{new_filename}"
    add_sitemap_url(url, priority="0.8")


DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def gather_articles():
    """Return list of dicts {filename, title, date} for all article pages.

    Date is parsed from the YYYY-MM-DD prefix in the filename when present;
    otherwise it falls back to the file modification date. Sorted by date desc.
    """
    articles = []
    for filepath in glob.glob("articles/*.html"):
        filename = os.path.basename(filepath)
        if filename == "index.html":
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                title = extract_title(f.read())
        except OSError:
            title = None
        if not title:
            title = filename.replace(".html", "").replace("-", " ").title()

        m = DATE_RE.search(filename)
        if m:
            date = m.group(1)
        else:
            date = datetime.fromtimestamp(
                os.path.getmtime(filepath)).strftime("%Y-%m-%d")

        articles.append({"filename": filename, "title": title, "date": date})

    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def render_article_index(articles):
    """Build the articles/index.html HTML string."""
    rows = []
    for a in articles:
        title = html.escape(a["title"])
        rows.append(
            '      <li class="article-item">\n'
            f'        <a class="article-link" href="/articles/{html.escape(a["filename"])}">\n'
            f'          <span class="article-date">{html.escape(a["date"])}</span>\n'
            f'          <span class="article-title">{title}</span>\n'
            '          <span class="article-arrow">&rarr;</span>\n'
            '        </a>\n'
            '      </li>'
        )
    items = "\n".join(rows) if rows else '      <li class="article-item">No articles yet.</li>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>All Articles — GaijinHome</title>
<meta name="description" content="Every problem-solving guide for foreigners living in Japan — housing, banking, phone, visa and daily life.">
<link rel="canonical" href="https://gaijinhome.com/articles/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{ --red: #E8372A; --ink: #0F0E0C; --cream: #FDFAF5; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'DM Sans', sans-serif; background: var(--cream); color: var(--ink); line-height: 1.6; -webkit-font-smoothing: antialiased; }}
  .wrap {{ max-width: 820px; margin: 0 auto; padding: 64px 24px 96px; }}
  .top {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 48px; }}
  .logo {{ font-family: 'Syne', sans-serif; font-weight: 800; font-size: 22px; color: var(--ink); text-decoration: none; letter-spacing: -0.5px; }}
  .logo span {{ color: var(--red); }}
  .back {{ font-size: 14px; font-weight: 600; color: var(--red); text-decoration: none; }}
  h1 {{ font-family: 'Syne', sans-serif; font-weight: 800; font-size: clamp(34px, 6vw, 52px); letter-spacing: -1px; margin-bottom: 12px; }}
  .lead {{ font-size: 17px; color: #5A5752; margin-bottom: 48px; max-width: 600px; }}
  .count {{ display: inline-block; background: var(--red); color: #fff; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 13px; padding: 4px 12px; border-radius: 999px; margin-bottom: 24px; }}
  ul {{ list-style: none; }}
  .article-item {{ border-top: 1px solid #E7E2D8; }}
  .article-item:last-child {{ border-bottom: 1px solid #E7E2D8; }}
  .article-link {{ display: flex; align-items: baseline; gap: 18px; padding: 20px 4px; text-decoration: none; color: var(--ink); transition: padding-left .18s ease, background .18s ease; }}
  .article-link:hover {{ padding-left: 14px; background: rgba(232,55,42,0.04); }}
  .article-date {{ font-family: 'Syne', sans-serif; font-weight: 600; font-size: 13px; color: var(--red); min-width: 96px; flex-shrink: 0; }}
  .article-title {{ font-family: 'Syne', sans-serif; font-weight: 600; font-size: 18px; flex: 1; letter-spacing: -0.3px; }}
  .article-arrow {{ color: var(--red); font-size: 18px; flex-shrink: 0; opacity: 0; transition: opacity .18s ease; }}
  .article-link:hover .article-arrow {{ opacity: 1; }}
  .foot {{ margin-top: 64px; font-size: 13px; color: #8A867E; }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <a class="logo" href="/">Gaijin<span>Home</span></a>
      <a class="back" href="/">&larr; Home</a>
    </div>
    <span class="count">{len(articles)} articles</span>
    <h1>All Articles</h1>
    <p class="lead">Every problem-solving guide for foreigners living in Japan — housing, banking, phone &amp; SIM, visa, and daily life.</p>
    <ul>
{items}
    </ul>
    <p class="foot">© GaijinHome — Updated {datetime.now().strftime('%Y-%m-%d')}</p>
  </div>
</body>
</html>
"""


def update_article_index():
    """Regenerate articles/index.html listing all articles, newest first."""
    articles = gather_articles()
    html_out = render_article_index(articles)

    if DRY_RUN:
        print(f"[dry-run] would write articles/index.html with {len(articles)} articles:")
        for a in articles:
            print(f"  {a['date']}  {a['title']}  ->  /articles/{a['filename']}")
        return

    os.makedirs("articles", exist_ok=True)
    with open("articles/index.html", "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Updated articles/index.html ({len(articles)} articles)")

    # Ensure the articles index itself is in the sitemap (with dedup check).
    add_sitemap_url("https://gaijinhome.com/articles/", priority="0.7")


def add_sitemap_url(url, priority="0.8"):
    """Append a <url> entry to sitemap.xml if not already present."""
    sitemap_path = "sitemap.xml"
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = (
        f"  <url>\n    <loc>{url}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <priority>{priority}</priority>\n  </url>"
    )
    if os.path.exists(sitemap_path):
        with open(sitemap_path, "r") as f:
            content = f.read()
        # Match the full <loc> tag to avoid substring collisions
        # (e.g. .../articles/ is a substring of .../articles/foo.html).
        if f"<loc>{url}</loc>" not in content:
            content = content.replace("</urlset>", f"{new_entry}\n</urlset>")
            with open(sitemap_path, "w") as f:
                f.write(content)


def count_articles():
    """Count article pages in articles/ excluding index.html."""
    return sum(
        1 for p in glob.glob("articles/*.html")
        if os.path.basename(p) != "index.html"
    )


def update_homepage_counter():
    """Overwrite the published-guides counter on the root index.html.

    Targets the number paired with the "In-depth guides published" label,
    tolerating either the metric-val/metric-lbl or stat-num/stat-label markup.
    """
    index_path = "index.html"
    if not os.path.exists(index_path):
        return
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    n = count_articles()

    # Match the digits inside the value div that precedes the label div.
    pattern = re.compile(
        r'(<div class="(?:metric-val|stat-num)">)\s*\d+\s*(</div>\s*'
        r'<div class="(?:metric-lbl|stat-label)">In-depth guides published</div>)'
    )
    new_content, count = pattern.subn(rf"\g<1>{n}\g<2>", content)

    if DRY_RUN:
        print(f"[dry-run] homepage counter -> {n} (matches found: {count})")
        return

    if count and new_content != content:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated homepage counter to {n}")
    else:
        print(f"Homepage counter unchanged ({n}); pattern matches: {count}")


def main():
    if DRY_RUN:
        print("=== DRY RUN: no API calls, no files written ===")

    keywords_data = load_keywords()
    done_keywords = load_done_keywords()
    print(f"Done keywords: {len(done_keywords)}")

    # 1. Prefer an unused static keyword from keywords.json.
    keyword, category = get_next_keyword(keywords_data, done_keywords)

    # 2. Once the static list is exhausted, autonomously generate a topic.
    autonomous = False
    if not keyword:
        print("All static keywords processed — generating a new topic autonomously.")
        keyword, category = generate_new_topic()
        autonomous = True

    print(f"Next keyword: {keyword} (category: {category})")

    filename = topic_to_filename(keyword)
    print(f"Filename: articles/{filename}")

    if DRY_RUN:
        # Dry-run: exercise selection, filename, and index logic only.
        print(f"[dry-run] would generate title via keyword_to_title('{keyword}')")
        print(f"[dry-run] would generate article and save to articles/{filename}")
        print(f"[dry-run] would append '{keyword}' to done_keywords.json")
        update_article_index()
        update_homepage_counter()
        print("\n[dry-run] complete.")
        return

    if os.path.exists(f"articles/{filename}"):
        print(f"Article already exists: {filename}, skipping.")
        return

    title = keyword_to_title(keyword)
    print(f"Title: {title}")

    article_html = generate_article(keyword, category, title)
    save_article(filename, article_html)
    update_sitemap(filename)
    update_article_index()
    update_homepage_counter()

    # Record the keyword as done (covers both static and autonomous topics).
    done_keywords.append(keyword)
    save_done_keywords(done_keywords)

    if autonomous:
        print("(autonomous topic recorded in done_keywords.json)")

    print(f"\n✅ Done! articles/{filename}")


if __name__ == "__main__":
    main()
