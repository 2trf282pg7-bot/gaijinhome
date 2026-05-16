#!/usr/bin/env python3
import anthropic
import os
import re
import glob
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

ARTICLE_SYSTEM_PROMPT = """You are an expert content writer for GaijinHome (gaijinhome.com), 
a website helping foreigners rent apartments in Japan.
Write SEO-optimized HTML articles that are practical, honest, and detailed.
1500-2500 words. Use red (#E8372A), dark ink (#0F0E0C), cream (#FDFAF5), Syne font.
Include internal links to /guide-complete.html, /guide-no-guarantor.html, /guide-rejection.html,
/guide-hidden-costs.html, /guide-osaka-kansai.html, /guide-visa-breakdown.html.
Include affiliate CTAs for Best-Estate.jp, Oakhouse, CrossOneRoom.
Output ONLY valid HTML."""


def get_existing_topics():
    """Get list of existing article filenames to avoid duplicates."""
    files = glob.glob("articles/guide-*.html")
    topics = []
    for f in files:
        name = os.path.basename(f).replace(".html", "").replace("guide-", "").replace("-", " ")
        topics.append(name)
    return topics


def generate_new_topic(existing_topics):
    """Ask Claude to come up with a new unique article topic."""
    existing_list = "\n".join(f"- {t}" for t in existing_topics) if existing_topics else "(none yet)"
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"""You generate SEO keyword topics for GaijinHome, a site helping foreigners rent apartments in Japan.

Already covered topics:
{existing_list}

Generate ONE new keyword topic that:
- Targets foreigners searching for housing in Japan
- Is not already covered above
- Has good search volume potential (e.g. city names, visa types, apartment types, specific problems)
- Is in English, 3-7 words

Reply with ONLY the keyword phrase, nothing else."""
        }]
    )
    return response.content[0].text.strip().strip('"')


def topic_to_filename(topic):
    slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')
    return f"guide-{slug}.html"


def generate_article(topic):
    print(f"Generating article for: {topic}")
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f'Write a complete HTML article targeting: "{topic}". Include proper head, meta tags, TOC, sidebar with affiliate links, FAQ with schema markup. Year: 2026.'
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
    existing_topics = get_existing_topics()
    print(f"Existing articles: {len(existing_topics)}")

    topic = generate_new_topic(existing_topics)
    print(f"New topic: {topic}")

    filename = topic_to_filename(topic)

    # Avoid overwriting if somehow duplicate
    if os.path.exists(f"articles/{filename}"):
        print(f"Article already exists: {filename}, skipping.")
        return

    article_html = generate_article(topic)
    save_article(filename, article_html)
    update_sitemap(filename)
    print(f"\n✅ Done! articles/{filename}")


if __name__ == "__main__":
    main()
