#!/usr/bin/env python3
import anthropic
import os
import re
import json
import glob
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SITE_DOMAIN = "retireabroad-hub.com"
SITE_NAME = "RetireAbroadHub"

INTERNAL_LINKS = [
    "/guide-medicare.html",
    "/guide-taxes-fbar.html",
    "/guide-portugal.html",
    "/guide-mexico.html",
    "/guide-insurance.html",
    "/guide-banking.html",
]

AFFILIATE_BY_CATEGORY = {
    "category_1_medicare_insurance": [
        "Cigna Global Health Insurance",
        "IMG International Insurance",
        "SafetyWing Nomad Insurance",
    ],
    "category_2_tax_fbar": [
        "Greenback Expat Tax Services",
        "Taxes for Expats",
    ],
    "category_3_visa_residency": [
        "VisaHQ International Services",
        "Portugal Residency Advisors",
    ],
    "category_4_banking_finance": [
        "Wise International Transfers",
        "Charles Schwab International Account",
    ],
    "category_5_real_estate": [
        "Portugal Property Guides",
        "Mexhomes International",
    ],
    "category_6_social_security": [
        "Maximize My Social Security",
        "Social Security Timing Advisors",
    ],
    "category_7_healthcare_local": [
        "IMSS Voluntary Enrollment Service",
        "SNS Portugal Registration Assistance",
    ],
    "category_8_cost_of_living": [
        "Wise International Transfers",
        "Cigna Global Health Insurance",
    ],
}


def load_revenue_insights():
    with open("revenue-insights.json", "r") as f:
        return json.load(f)


def load_trusted_domains():
    with open("trusted-domains.json", "r") as f:
        return json.load(f)


def load_failure_db():
    if os.path.exists("failure-db.json"):
        with open("failure-db.json", "r") as f:
            return json.load(f)
    return {"failures": []}


def load_keywords():
    with open("keywords.json", "r") as f:
        return json.load(f)


def load_done_keywords():
    if os.path.exists("done_keywords.json"):
        with open("done_keywords.json", "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    return []


def save_done_keywords(done):
    with open("done_keywords.json", "w") as f:
        json.dump(done, f, ensure_ascii=False, indent=2)


def get_next_keyword(keywords_data, done_keywords):
    done_set = set(
        k if isinstance(k, str) else k.get("keyword", k)
        for k in done_keywords
    )
    for category, keywords in keywords_data.items():
        for entry in keywords:
            kw = entry["keyword"] if isinstance(entry, dict) else entry
            if kw not in done_set:
                intent = entry.get("intent", "informational") if isinstance(entry, dict) else "informational"
                return kw, category, intent
    return None, None, None


def get_category_failures(failure_db, category):
    cat_key = category.replace("category_", "").split("_", 1)[-1] if "_" in category else category
    return [
        f for f in failure_db.get("failures", [])
        if cat_key in f.get("category", "")
    ][:3]


def build_system_prompt(revenue_insights, trusted_domains, failure_db, category, intent):
    high_ctr = ", ".join(revenue_insights["high_ctr_topics"])
    conversion_patterns = "\n".join(
        f"  - {p}" for p in revenue_insights["high_conversion_patterns"]
    )
    high_epc = ", ".join(revenue_insights["high_epc_affiliates"])
    low_performing = ", ".join(revenue_insights["low_performing_topics"])
    intent_guidance = revenue_insights["search_intent"].get(intent, "structured explanation with official sources")

    domain_list = "\n".join(
        f"  - {d['name']}: {d['url']} (topics: {', '.join(d['topics'])})"
        for d in trusted_domains["domains"]
    )

    category_failures = get_category_failures(failure_db, category)
    failures_text = ""
    if category_failures:
        failures_text = "\n\nFAILURE CASES TO REFERENCE (anonymized — use in article body):\n"
        for fail in category_failures:
            failures_text += (
                f"  Case: {fail['situation']}\n"
                f"  Outcome: {fail['outcome']}\n"
                f"  Cost range: {fail['cost_range']}\n"
                f"  Source: {fail['source']}\n\n"
            )

    last_verified = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year

    internal_link_list = "\n".join(
        f"  - https://{SITE_DOMAIN}{link}" for link in INTERNAL_LINKS
    )

    return f"""You are writing for Americans aged 55-70 who are seriously
planning to retire in Portugal or Mexico and are currently
stuck on a specific practical problem.

They are not browsing for inspiration. They have already
decided to retire abroad and are dealing with hard realities.

They have read International Living and found it too optimistic.
They want honest, specific, actionable information.

REVENUE INTELLIGENCE (auto-injected from revenue-insights.json):
Priority keywords to naturally weave in: {high_ctr}
Title/heading patterns that convert well:
{conversion_patterns}
High-EPC affiliates to feature naturally: {high_epc}
Topics to AVOID (low-performing): {low_performing}
Search intent for this article: {intent} → {intent_guidance}

TRUSTED SOURCES — use ONLY these domains for external links:
{domain_list}
{failures_text}
ALWAYS include:
- Specific dollar amounts and financial consequences
- Real failure cases referenced from expat communities
  (anonymized and summarized, not verbatim)
  Format: "Cases reported in expat communities show: [situation].
           The typical outcome: [result]. The cost range: [amount]."
- Reddit community references:
  "Multiple expats in r/PortugalExpats reported that..."
- Exact document names and where to obtain them
- Links to official government sources (IRS, CMS, US Embassy)
  Use sources from trusted-domains.json only
- Portugal vs Mexico specific differences
- Step-by-step recovery instructions
- last_verified_at date: {last_verified} for all regulatory information
- "as of {current_year}" qualifier for all legal / tax / visa claims
- "requirements may change – consult official sources" for
  visa / residency / taxation / healthcare eligibility topics

NEVER write:
- Optimistic "retiring abroad is wonderful" openings
- Generic top-10 country lists
- Year-specific titles like "{current_year} Guide to X"
- Vague advice like "consult a professional"
  (instead: "a FATCA-specialized CPA typically charges
   $300-600 for this filing")
- Anything AI Overview could answer in one sentence
- Topics listed in low-performing: {low_performing}
- "always", "guaranteed", "definitely" for legal/tax/visa topics
- Exact tax calculations presented as definitive
- Legal guarantees or immigration certainty claims

Title format:
OK: "Why Americans Get Rejected for the Portugal D7 Visa"
OK: "The Medicare Penalty Trap That Costs Retirees $48,000"
OK: "What Happens When Your Insurance Claim Is Denied Abroad"
NG: "Portugal D7 Visa Guide {current_year}"
NG: "Best Health Insurance for American Retirees"
NG: "Top 10 Tips for Retiring in Mexico"

Article structure:
1. What actually happens (with dollar amounts)
2. Why it happens (structural / institutional reasons)
3. Real failure cases (anonymized, from the cases listed above)
4. Step-by-step fix (exact documents, exact steps)
5. Document checklist
6. Portugal vs Mexico differences
7. Recommended services ([PR] disclosure required)
   Priority affiliates: {high_epc}

Internal links to include naturally:
{internal_link_list}

Article header (auto-insert at the very top of the article body):
"[PR] This article contains affiliate links.
 We may earn a commission at no extra cost to you."

Article footer (auto-insert at the very bottom of the article body):
"This article is for informational purposes only and does
not constitute legal, tax, or financial advice. Always
consult a qualified professional before making decisions
about retirement abroad, health insurance, or visa applications.
Last verified: {last_verified}. Regulatory information
may change."

Use navy (#1B2E5E), cream (#FDFAF5), gold (#B8962E), dark ink (#0F0E0C).
Use Merriweather or Georgia for headings, system-ui for body text.
Include internal links listed above.
1500-2500 words. Output ONLY valid HTML."""


def keyword_to_title(keyword, intent):
    intent_instruction = {
        "informational": "Start with 'Why' or 'What Happens When' or 'The Truth About'.",
        "emotional": "Start with 'The [X] Trap' or describe the painful consequence first.",
        "commercial": "Frame as a comparison or decision ('vs', 'Which Is', 'Before You Choose').",
        "transactional": "Start with an action verb like 'How to' but frame the problem first.",
    }.get(intent, "Start with 'Why' or frame as a specific problem.")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        messages=[{
            "role": "user",
            "content": f"""Transform this keyword into an article title for Americans aged 55-70 planning to retire in Portugal or Mexico.
Keyword: {keyword}
Intent: {intent}
Instruction: {intent_instruction}

Rules:
- Do NOT include a year number (e.g., "2025", "2026")
- Do NOT use "Best", "Complete Guide", "Top 10"
- MUST feel like a real problem the reader is facing right now
- Dollar amounts in title are encouraged if relevant

Examples:
OK: "Why Americans Get Rejected for the Portugal D7 Visa"
OK: "The Medicare Penalty Trap That Costs Retirees $48,000"
OK: "What Happens When Your Health Insurance Claim Is Denied in Portugal"
OK: "Cigna Global vs IMG: Which Actually Covers American Retirees Abroad"
NG: "Portugal D7 Visa Guide 2026"
NG: "Best Insurance for Expat Retirees"

Reply with ONLY the title, nothing else."""
        }]
    )
    return response.content[0].text.strip().strip('"')


def keyword_to_filename(keyword):
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    return f"{date_prefix}-{slug}.html"


def generate_article(keyword, category, title, intent, revenue_insights, trusted_domains, failure_db):
    affiliates = AFFILIATE_BY_CATEGORY.get(category, revenue_insights["high_epc_affiliates"][:2])
    affiliate_note = (
        f"For the Recommended Services section, feature these affiliates naturally with [PR] disclosure: "
        f"{', '.join(affiliates)}. Place one affiliate mention inside the Step-by-step fix section "
        f"and up to 3 in the Recommended Services section at the end."
    )

    system_prompt = build_system_prompt(revenue_insights, trusted_domains, failure_db, category, intent)

    print(f"Generating article for: {keyword} (category: {category}, intent: {intent})")
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8000,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                f'Write a complete HTML article. Title: "{title}". '
                f'Target keyword: "{keyword}". '
                f'Search intent: {intent}. '
                f'{affiliate_note} '
                f'Include a proper <head> with meta description starting with "If your" or '
                f'"Confused about" or "Struggling with" or "Facing", meta tags, '
                f'and FAQ schema markup (at least 3 questions). '
                f'Do NOT include a year in the title or meta title.'
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
    sitemap_path = "sitemap.xml"
    url = f"https://{SITE_DOMAIN}/articles/{new_filename}"
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
    revenue_insights = load_revenue_insights()
    trusted_domains = load_trusted_domains()
    failure_db = load_failure_db()

    keywords_data = load_keywords()
    done_keywords = load_done_keywords()
    print(f"Done keywords: {len(done_keywords)}")

    keyword, category, intent = get_next_keyword(keywords_data, done_keywords)
    if not keyword:
        print("All keywords have been processed.")
        return

    print(f"Next keyword: {keyword} (category: {category}, intent: {intent})")

    title = keyword_to_title(keyword, intent)
    print(f"Title: {title}")

    filename = keyword_to_filename(keyword)

    if os.path.exists(f"articles/{filename}"):
        print(f"Article already exists: {filename}, skipping.")
        done_keywords.append(keyword)
        save_done_keywords(done_keywords)
        return

    article_html = generate_article(keyword, category, title, intent, revenue_insights, trusted_domains, failure_db)
    save_article(filename, article_html)
    update_sitemap(filename)

    done_keywords.append(keyword)
    save_done_keywords(done_keywords)

    print(f"\n✅ Done! articles/{filename}")


if __name__ == "__main__":
    main()
