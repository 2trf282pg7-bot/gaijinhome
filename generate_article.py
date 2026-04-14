#!/usr/bin/env python3
import anthropic
import json
import os
import re
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

KEYWORD_QUEUE = [
    "no guarantor apartments Tokyo",
    "foreigner friendly apartments Osaka",
    "how to rent apartment Japan work visa",
    "cheap apartments Tokyo foreigner",
    "share house Tokyo foreigner English",
    "apartment hunting Japan student visa",
    "furnished apartments Tokyo short term foreigner",
    "how to pass credit check Japan foreigner",
    "monthly mansion Japan foreigner",
    "UR housing foreigner apply",
    "apartment Japan without Japanese guarantor",
    "renting apartment Japan permanent resident",
    "Osaka foreigner apartment no guarantor",
    "Japan apartment deposit refund tips",
    "foreigner renting Japan self employed",
]

ARTICLE_SYSTEM_PROMPT = """You are an expert content writer for GaijinHome (gaijinhome.com), 
a website helping foreigners rent apartments in Japan.
Write SEO-optimized HTML articles that are practical, honest, and detailed.
1500-2500 words. Use red (#E8372A), dark ink (#0F0E0C), cream (#FDFAF5), Syne font.
Include internal links to /guide-complete.html, /guide-no-guarantor.html, /guide-rejection.html,
/guide-hidden-costs.html, /guide-osaka-kansai.html, /guide-visa-breakdown.html.
Include affiliate CTAs for Best-Estate.jp, Oakhouse, CrossOneRoom.
Output ONLY valid HTML."""

def get_next_keyword():
    done_file = "done_keywords.json"
    if os.path.exists(done_file):
        with open(done_file) as f:
            done = json.load(f)
    else:
        done = []
    remaining = [k for k in KEYWORD_QUEUE if k not in done]
    if not remaining:
        print("All keywords done!")
        return None
    keyword = remaining[0]
    done.append(keyword)
    with open(done_file, "w") as f:
        json.dump(done, f)
    return keyword

def keyword_to_filename(keyword):
    slug = re.sub(r'[^a-z0-9]+', '-', keyword.lower()).strip('-')
    return f"guide-{slug}.html"

def generate_article(keyword):
    print(f"Generating article for: {keyword}")
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Write a complete HTML article targeting: \"{keyword}\". Include proper head, meta tags, TOC, sidebar with affiliate links, FAQ with schema markup. Year: 2026."}]
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
    sitemap_path = "sitemap.xml"
    url = f"https://gaijinhome.com/articles/{new_filename}"
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n    <priority>0.8</priority>\n  </url>"
    if os.path.exists(sitemap_path):
        with open(sitemap_path, "r") as f:
            content = f.read()
        if url not in content:
            content = content.replace("</urlset>", f"{new_entry}\n</urlset>")
            with open(sitemap_path, "w") as f:
                f.write(content)

def main():
    keyword = get_next_keyword()
    if not keyword:
        return
    filename = keyword_to_filename(keyword)
    article_html = generate_article(keyword)
    save_article(filename, article_html)
    update_sitemap(filename)
    print(f"\n✅ Done! articles/{filename}")

if __name__ == "__main__":
    main()
