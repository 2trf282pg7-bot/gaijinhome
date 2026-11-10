#!/usr/bin/env python3
"""
GaijinHome - publish a hand-written article draft (no API needed).

  python publish_draft.py next
      -> prints JSON {keyword, category, filename} for the next unused keyword
         (or {"keyword": null} when the list is exhausted)

  python publish_draft.py add-keyword "<keyword>" <category>
      -> appends a new keyword to keywords.json (use when the list is exhausted)

  python publish_draft.py publish drafts/<filename>.html "<keyword>" <category>
      -> validates the fragment, renders articles/<filename>.html, adds related
         links, records the keyword as done, rebuilds indexes, canonical/links,
         affiliate box and sitemap.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import affiliate_fix
import build_article
import seo_fix
import update_links
import update_sitemap

JST = timezone(timedelta(hours=9))


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def slugify(keyword):
    return re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")


# Housing drives search traffic and the high-value affiliates: ~60% housing.
CATEGORY_CYCLE = [
    "category_a_housing", "category_b_banking", "category_a_housing", "category_c_phone",
    "category_a_housing", "category_d_visa", "category_a_housing", "category_e_daily",
    "category_a_housing", "category_a_housing",
]


def cmd_next():
    keywords = load("keywords.json", {})
    done = load("done_keywords.json", [])
    date = datetime.now(JST).strftime("%Y-%m-%d")
    category = CATEGORY_CYCLE[len(done) % len(CATEGORY_CYCLE)]
    for kw in keywords.get(category, []):
        if kw not in done:
            print(json.dumps({"keyword": kw, "category": category,
                              "filename": f"{date}-{slugify(kw)}.html"}))
            return
    # Category exhausted: the caller must invent a new keyword in this category
    print(json.dumps({"keyword": None, "category": category, "existing_topics": done}))


def cmd_add_keyword(keyword, category):
    keywords = load("keywords.json", {})
    keyword = " ".join(keyword.lower().split())
    if any(keyword in v for v in keywords.values()):
        sys.exit(f"keyword already exists: {keyword}")
    keywords.setdefault(category, []).append(keyword)
    with open("keywords.json", "w") as f:
        json.dump(keywords, f, ensure_ascii=False, indent=2)
    print(f"added: {keyword} ({category})")


def validate(fragment):
    problems = []
    if not fragment.startswith("<!-- description:"):
        problems.append("missing description comment on line 1")
    if len(re.findall(r"<h1[\s>]", fragment)) != 1:
        problems.append("needs exactly one <h1>")
    if '<div class="faq">' not in fragment or not fragment.rstrip().endswith("</div>"):
        problems.append("missing or unterminated FAQ block")
    if re.search(r"<(html|head|body|style|script)[\s>]", fragment, re.I):
        problems.append("contains page-level tags")
    if re.search(r'href="https?://(?!px\.a8\.net/)', fragment):
        problems.append("external link other than px.a8.net")
    words = len(re.sub(r"<[^>]+>", " ", fragment).split())
    if words < 1400:
        problems.append(f"too short ({words} words)")
    return problems


def cmd_publish(draft, keyword, category):
    with open(draft, encoding="utf-8") as f:
        fragment = f.read().strip()
    problems = validate(fragment)
    if problems:
        sys.exit("NOT PUBLISHED: " + "; ".join(problems))
    path = build_article.render(draft)
    update_links.insert_related_links(path, category=category)
    done = load("done_keywords.json", [])
    if keyword not in done:
        done.append(keyword)
        with open("done_keywords.json", "w") as f:
            json.dump(done, f, ensure_ascii=False, indent=2)
    update_links.update_all()
    seo_fix.run_all()
    affiliate_fix.run_all()
    update_sitemap.generate_sitemap()
    print(f"published: {path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["next"]:
        cmd_next()
    elif args[:1] == ["add-keyword"] and len(args) == 3:
        cmd_add_keyword(args[1], args[2])
    elif args[:1] == ["publish"] and len(args) == 4:
        cmd_publish(args[1], args[2], args[3])
    else:
        sys.exit(__doc__)
