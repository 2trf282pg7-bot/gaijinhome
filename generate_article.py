#!/usr/bin/env python3
import anthropic
import os
import re
import sys
import json
import glob
from datetime import datetime

import update_links
import update_sitemap
import seo_fix
import affiliate_fix
import build_article

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

OUTPUT FORMAT (strict) — an HTML body fragment, nothing else:
- Line 1: <!-- description: ONE sentence, 140-160 chars, starting with "If your", "Confused about" or "Struggling with" -->
- Then exactly one <h1> with the given title, then the body.
- No <html>, <head>, <body>, <style>, <script>, no markdown, no code fences.
- Allowed tags: h1 h2 h3 p ul ol li table thead tbody tr th td strong em a,
  <div class="callout"> for one key tip, <ul class="checklist"> for documents.

Sections as h2, in this order:
1. What actually happens (the exact situation the reader is stuck in)
2. Why it happens (structural reasons — not obvious, not generic)
3. Common mistakes (3-5 specific mistakes foreigners make)
4. Step-by-step fix (numbered <ol>: exact steps, documents, alternatives)
5. Required documents (<ul class="checklist">, Japanese terms in parentheses)
6. City / region differences (Tokyo vs Osaka vs other cities where relevant)
7. <h2>Frequently Asked Questions</h2> then <div class="faq"> with 4-5 pairs of
   <h3>Question?</h3><p>Answer</p>, then </div>. The fragment ends with that </div>.

1500-2200 words. Use rough ranges instead of invented statistics; never invent
studies, quotes, law article numbers or company facts.
Include 3-5 internal links to /full-guide, /no-guarantor, /rejected,
/hidden-costs, /osaka, /visa-guide (absolute paths, no .html)."""

AFFILIATE_BY_CATEGORY = {
    "category_a_housing": ["Oakhouse (A8.net)", "CrossOneRoom (A8.net)"],
    "category_b_banking": ["Wise (no link)", "Revolut (no link)", "italki (A8.net)"],
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


# Weighted toward housing to keep topical authority (the site's core cluster)
TOPIC_CATEGORY_CYCLE = [
    "category_a_housing", "category_a_housing", "category_a_housing",
    "category_b_banking", "category_a_housing", "category_c_phone",
    "category_a_housing", "category_d_visa", "category_a_housing", "category_e_daily",
]
TIER_A_CITIES = ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Kyoto", "Kobe", "Fukuoka"]


def generate_new_topic(keywords_data, done_keywords):
    """Ask Haiku for a fresh, non-duplicate problem-type keyword and queue it.

    Used when the fixed keyword list is exhausted so daily generation never
    silently stops."""
    category = TOPIC_CATEGORY_CYCLE[len(done_keywords) % len(TOPIC_CATEGORY_CYCLE)]
    existing = sorted(set(done_keywords) | {
        re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(f))[:-5].replace("-", " ")
        for f in glob.glob("articles/*.html") if not f.endswith("index.html")
    })
    prompt = f"""You pick the next article topic for GaijinHome, a site for foreigners
renting housing and settling in Japan. Category for this topic: {category}
(a=housing/renting, b=banking/money, c=phone/SIM/internet, d=visa/residence card
as it affects housing and contracts, e=daily-life paperwork).

Rules:
- A specific problem a foreigner is stuck with RIGHT NOW (rejected, denied,
  refused, dispute, penalty, confusion, deadline), phrased like a real Google search.
- 5-9 words, lowercase, English, no punctuation, must mention japan or a city.
- For housing, you may target one of these cities: {", ".join(TIER_A_CITIES)}.
- Never generic "best / guide / how to find / tips / overview" topics.
- Must not overlap in intent with any existing topic below.

Existing topics:
{chr(10).join("- " + t for t in existing)}

Reply with ONLY the keyword."""
    for _ in range(3):
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=40,
            messages=[{"role": "user", "content": prompt}],
        )
        kw = re.sub(r"[^a-z0-9 ]", "", resp.content[0].text.strip().lower()).strip()
        kw = re.sub(r"\s+", " ", kw)
        if 3 <= len(kw.split()) <= 12 and kw not in existing and kw not in done_keywords:
            keywords_data.setdefault(category, []).append(kw)
            with open("keywords.json", "w") as f:
                json.dump(keywords_data, f, ensure_ascii=False, indent=2)
            print(f"🆕 Auto-generated topic: {kw} ({category})")
            return kw, category
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


def generate_article(keyword, category, title):
    affiliates = AFFILIATE_BY_CATEGORY.get(category, ["JAPAN&GLOBAL eSIM (A8.net)"])
    urls = {k: v for k, v in affiliate_fix.LINKS.items()}
    affiliate_note = (
        f"Optionally mention ONE of these affiliates inside the Step-by-step fix, with \"[PR]\" right before "
        f"the link and rel=\"nofollow sponsored noopener\": {', '.join(affiliates)}. "
        f"(A sponsor box is added automatically — do not add a Recommended Services section.) Use ONLY these exact tracked URLs "
        f"(never the advertiser's own domain, never invent URLs): Oakhouse {urls['oakhouse']} ; "
        f"CrossOneRoom {urls['crossoneroom']} ; JAPAN&GLOBAL eSIM {urls['esim']} ; "
        f"WiFi rental {urls['wifi']} ; italki (Japanese lessons) {urls['italki']} ; "
        f"Leopalace21 furnished apartments nationwide {urls['leopalace']} ; "
        f"Village House zero-deposit apartments (residents of Japan only) {urls['villagehouse']}. "
        f"Wise/Revolut have no tracked link: mention them without a link."
    )

    print(f"Generating article for: {keyword} (category: {category})")
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f'Write the article fragment. Title (use as the h1): "{title}". '
                f'Target keyword: "{keyword}". '
                f'{affiliate_note} '
                f'Year: 2026.'
            )
        }]
    )
    return message.content[0].text


def strip_code_fences(content):
    """Remove markdown code fences and any preamble before the fragment."""
    text = re.sub(r"^```[a-zA-Z]*[ \t]*\n?", "", content.strip())
    text = re.sub(r"\n?```\s*$", "", text)
    idx = text.find("<!-- description")
    if idx > 0:
        text = text[idx:]
    return text.strip()


def validate_article(content):
    """Return a list of problems (empty list = valid)."""
    problems = []
    if not content.startswith("<!-- description:"):
        problems.append("missing description comment")
    if len(re.findall(r"<h1[\s>]", content)) != 1:
        problems.append("needs exactly one <h1>")
    if '<div class="faq">' not in content or not content.rstrip().endswith("</div>"):
        problems.append("missing or unterminated FAQ (likely truncated)")
    if re.search(r"<(html|head|body|style|script)[\s>]", content, re.I):
        problems.append("contains page-level tags")
    words = len(re.sub(r"<[^>]+>", " ", content).split())
    if words < 1000:
        problems.append(f"too short ({words} words)")
    return problems


def save_article(filename, content):
    """Save the fragment to drafts/ and render the full page into articles/."""
    os.makedirs("drafts", exist_ok=True)
    os.makedirs("articles", exist_ok=True)
    draft = f"drafts/{filename}"
    with open(draft, "w", encoding="utf-8") as f:
        f.write(content)
    filepath = build_article.render(draft)
    print(f"Saved: {filepath}")
    return filepath


REPAIR_PER_RUN = 3


def repair_truncated(limit=REPAIR_PER_RUN):
    """Regenerate up to `limit` articles listed in repair_queue.json (truncated
    by an old max_tokens bug). Keeps the same filename/URL."""
    if not os.path.exists("repair_queue.json"):
        return []
    with open("repair_queue.json") as f:
        queue = json.load(f)
    cat_map = update_links.load_category_map()
    repaired = []
    for name in list(queue)[:limit]:
        path = f"articles/{name}"
        if not os.path.exists(path):
            queue.remove(name)
            continue
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name[:-5])
        keyword = re.sub(r"^guide-", "", slug).replace("-", " ")
        category = cat_map.get(slug, "category_a_housing")
        with open(path, encoding="utf-8") as f:
            m = re.search(r"<title>([^<|]+)", f.read())
        title = m.group(1).strip() if m else keyword_to_title(keyword)
        html_out = None
        for _ in (1, 2):
            cand = strip_code_fences(generate_article(keyword, category, title))
            if not validate_article(cand):
                html_out = cand
                break
        if html_out is None:
            print(f"⚠️  Repair failed validation: {name} (kept in queue)")
            continue
        save_article(name, html_out)
        update_links.insert_related_links(path, category=category)
        queue.remove(name)
        repaired.append(name)
        print(f"🔧 Repaired: {name}")
    with open("repair_queue.json", "w") as f:
        json.dump(queue, f, indent=2)
    return repaired


def main():
    keywords_data = load_keywords()
    done_keywords = load_done_keywords()
    print(f"Done keywords: {len(done_keywords)}")

    keyword, category = get_next_keyword(keywords_data, done_keywords)
    if not keyword:
        keyword, category = generate_new_topic(keywords_data, done_keywords)
    if not keyword:
        print("❌ Could not obtain a new topic.")
        sys.exit(1)

    print(f"Next keyword: {keyword} (category: {category})")

    title = keyword_to_title(keyword)
    print(f"Title: {title}")

    filename = topic_to_filename(keyword)

    if os.path.exists(f"articles/{filename}"):
        print(f"Article already exists: {filename}, skipping.")
        return

    article_html = None
    for attempt in (1, 2):
        candidate = strip_code_fences(generate_article(keyword, category, title))
        problems = validate_article(candidate)
        if not problems:
            article_html = candidate
            break
        print(f"⚠️  Attempt {attempt} failed validation: {'; '.join(problems)}")

    if article_html is None:
        print("❌ Article failed validation after retry. Not saving.")
        sys.exit(1)

    filepath = save_article(filename, article_html)

    done_keywords.append(keyword)
    save_done_keywords(done_keywords)

    # Internal linking: related links in the new article, then rebuild
    # articles/index.html and the root Latest Articles section.
    update_links.insert_related_links(filepath, category=category)
    repair_truncated()
    update_links.update_all()

    # Canonical URLs, clean internal links, sitemap
    seo_fix.run_all()
    affiliate_fix.run_all()
    update_sitemap.generate_sitemap()

    print(f"\n✅ Done! articles/{filename}")


if __name__ == "__main__":
    main()
