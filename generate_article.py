#!/usr/bin/env python3
import anthropic
import os
import re
import json
import glob
from datetime import datetime

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


def strip_code_fences(text):
    """Remove Markdown code fences the model sometimes wraps HTML output in.

    Strips a leading ```html or ``` fence and a trailing ``` fence so the
    saved file is clean HTML rather than a fenced code block.
    """
    text = text.strip()
    text = re.sub(r'^```(?:html)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


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
        max_tokens=16000,
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
    return strip_code_fences(message.content[0].text)


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
        with open(sitemap_path, "r") as f:
            content = f.read()
        if url not in content:
            content = content.replace("</urlset>", f"{new_entry}\n</urlset>")
            with open(sitemap_path, "w") as f:
                f.write(content)


def main():
    keywords_data = load_keywords()
    done_keywords = load_done_keywords()
    print(f"Done keywords: {len(done_keywords)}")

    keyword, category = get_next_keyword(keywords_data, done_keywords)
    if not keyword:
        print("All keywords have been processed.")
        return

    print(f"Next keyword: {keyword} (category: {category})")

    title = keyword_to_title(keyword)
    print(f"Title: {title}")

    filename = topic_to_filename(keyword)

    if os.path.exists(f"articles/{filename}"):
        print(f"Article already exists: {filename}, skipping.")
        return

    article_html = generate_article(keyword, category, title)
    save_article(filename, article_html)
    update_sitemap(filename)

    done_keywords.append(keyword)
    save_done_keywords(done_keywords)

    print(f"\n✅ Done! articles/{filename}")


if __name__ == "__main__":
    main()
