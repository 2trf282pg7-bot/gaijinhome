#!/usr/bin/env python3
"""
GaijinHome - render an article page from a body fragment.

Usage: python build_article.py drafts/<filename>.html [more...]

Fragment format (UTF-8 HTML, no <html>/<head>/<body>):
  line 1: <!-- description: one sentence meta description -->
  then the article body: one <h1>, sections with <h2>/<h3>/<p>/<ul>/<ol>/<table>,
  and an FAQ section: <h2>Frequently Asked Questions</h2> followed by
  <div class="faq"><h3>Question?</h3><p>Answer</p> ... </div>

Output: articles/<filename>.html (same filename/URL as before).
"""

import html as htmllib
import json
import os
import re
import sys

BASE = "https://gaijinhome.com"

CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { background: #FAFAF7; }
  body { font-family: 'DM Sans', sans-serif; background: #FAFAF7; color: #1A1917; font-size: 16px; line-height: 1.75; -webkit-font-smoothing: antialiased; }
  nav { background: #fff; border-bottom: 1px solid #E4E2DC; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 60px; position: sticky; top: 0; z-index: 100; }
  .logo { font-weight: 600; font-size: 20px; color: #1A1917; letter-spacing: -0.5px; text-decoration: none; }
  .logo span { color: #1B4D3E; }
  .nav-links { display: flex; gap: 20px; list-style: none; }
  .nav-links a { text-decoration: none; color: #4A4845; font-size: 13px; font-weight: 500; white-space: nowrap; }
  article { max-width: 760px; margin: 0 auto; padding: 48px 24px 24px; }
  .meta { font-size: 13px; color: #8A8783; margin-bottom: 28px; }
  h1 { font-family: 'Literata', Georgia, serif; font-size: 34px; line-height: 1.25; font-weight: 600; margin-bottom: 12px; letter-spacing: -0.3px; }
  h2 { font-family: 'Literata', Georgia, serif; font-size: 24px; font-weight: 600; margin: 44px 0 14px; padding-top: 8px; border-top: 1px solid #E4E2DC; }
  h3 { font-size: 17px; font-weight: 600; margin: 24px 0 8px; }
  p { margin: 0 0 16px; }
  ul, ol { margin: 0 0 18px 22px; }
  li { margin-bottom: 6px; }
  a { color: #1B4D3E; }
  strong { font-weight: 600; }
  table { width: 100%; border-collapse: collapse; margin: 0 0 20px; font-size: 14.5px; background: #fff; }
  th, td { border: 1px solid #E4E2DC; padding: 9px 11px; text-align: left; vertical-align: top; }
  th { background: #EBF3F0; font-weight: 600; }
  .callout { background: #EBF3F0; border-left: 4px solid #1B4D3E; padding: 14px 18px; margin: 0 0 20px; border-radius: 4px; }
  .checklist li { list-style: none; margin-left: -22px; padding-left: 26px; position: relative; }
  .checklist li::before { content: "☐"; position: absolute; left: 0; color: #1B4D3E; }
  .faq h3 { margin-top: 20px; }
  footer { background: #fff; border-top: 1px solid #E4E2DC; padding: 32px 24px; margin-top: 48px; }
  .footer-inner { max-width: 760px; margin: 0 auto; display: flex; justify-content: space-between; gap: 24px; flex-wrap: wrap; font-size: 12.5px; color: #8A8783; }
  .footer-inner a { color: #4A4845; text-decoration: none; margin-right: 16px; }
  @media (max-width: 768px) { nav { padding: 0 16px; } .nav-links { display: none; } article { padding: 32px 16px 16px; } h1 { font-size: 27px; } h2 { font-size: 21px; } table { font-size: 13px; } }
"""

NAV = """<nav>
  <a href="/" class="logo">Gaijin<span>Home</span></a>
  <ul class="nav-links">
    <li><a href="/full-guide">Full Guide</a></li>
    <li><a href="/no-guarantor">No Guarantor</a></li>
    <li><a href="/rejected">Got Rejected?</a></li>
    <li><a href="/hidden-costs">Hidden Costs</a></li>
    <li><a href="/osaka">Osaka &amp; Kansai</a></li>
    <li><a href="/visa-guide">Visa Guide</a></li>
    <li><a href="/articles">All Articles</a></li>
  </ul>
</nav>"""

FOOTER = """<footer>
  <div class="footer-inner">
    <span>&copy; 2026 GaijinHome. Some links are affiliate links ([PR]).</span>
    <span><a href="/">Home</a><a href="/articles">All Articles</a><a href="/affiliate">Affiliate Disclosure</a><a href="/privacy">Privacy Policy</a></span>
  </div>
</footer>"""


def strip_tags(s):
    return htmllib.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def render(fragment_path):
    name = os.path.basename(fragment_path)
    slug = name[:-5]
    with open(fragment_path, encoding="utf-8") as f:
        frag = f.read().strip()

    m = re.match(r"<!--\s*description:\s*(.*?)\s*-->", frag, re.S)
    if not m:
        raise SystemExit(f"{name}: missing description comment")
    description = " ".join(m.group(1).split())
    body = frag[m.end():].strip()

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    if not h1:
        raise SystemExit(f"{name}: missing <h1>")
    title = strip_tags(h1.group(1))

    dm = re.match(r"(\d{4}-\d{2}-\d{2})-", name)
    published = dm.group(1) if dm else "2026-05-01"
    modified = "2026-11-03"
    canonical = f"{BASE}/articles/{slug}"

    faq = []
    fsec = re.search(r'<div class="faq">(.*?)</div>', body, re.S)
    if fsec:
        for q, a in re.findall(r"<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>", fsec.group(1), re.S):
            faq.append({"@type": "Question", "name": strip_tags(q),
                        "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}})

    schema = [{
        "@context": "https://schema.org", "@type": "Article", "headline": title,
        "description": description, "datePublished": published, "dateModified": modified,
        "author": {"@type": "Organization", "name": "GaijinHome"},
        "publisher": {"@type": "Organization", "name": "GaijinHome"},
        "mainEntityOfPage": canonical,
    }]
    if faq:
        schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq})

    body = body.replace(h1.group(0), h1.group(0) + '\n<p class="meta">Updated November 2026 · GaijinHome</p>', 1)
    e = htmllib.escape
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)} | GaijinHome</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{canonical}">
<meta property="article:published_time" content="{published}">
<meta property="article:modified_time" content="{modified}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Literata:wght@600&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
</head>
<body>
{NAV}
<main>
<article>
{body}
</article>
</main>
{FOOTER}
</body>
</html>
"""
    out = f"articles/{name}"
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("built", render(p))
