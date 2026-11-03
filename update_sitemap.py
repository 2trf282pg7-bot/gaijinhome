#!/usr/bin/env python3
"""
GaijinHome - Sitemap generator.
Rebuilds sitemap.xml from the files on disk using canonical URLs
(https://gaijinhome.com, no www, no .html). Called by generate_article.py.
"""

import glob
import os
import re

BASE = "https://gaijinhome.com"
LEGACY_LASTMOD = "2026-11-03"  # canonical/URL cleanup date for undated pages

STATIC_URLS = [
    ("/", "weekly", "1.0"),
    ("/full-guide", "monthly", "0.9"),
    ("/no-guarantor", "monthly", "0.8"),
    ("/rejected", "monthly", "0.8"),
    ("/hidden-costs", "monthly", "0.8"),
    ("/osaka", "monthly", "0.8"),
    ("/visa-guide", "monthly", "0.8"),
    ("/articles", "daily", "0.8"),
]


def article_files():
    files = glob.glob("articles/*.html")
    return sorted(f for f in files if os.path.basename(f) != "index.html")


def lastmod_for(filename):
    m = re.match(r"(\d{4}-\d{2}-\d{2})-", filename)
    return m.group(1) if m else LEGACY_LASTMOD


def newest_article_date(files):
    dates = [lastmod_for(os.path.basename(f)) for f in files]
    return max(dates) if dates else LEGACY_LASTMOD


def generate_sitemap():
    files = article_files()
    newest = newest_article_date(files)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    for path, freq, prio in STATIC_URLS:
        lastmod = newest if path in ("/", "/articles") else LEGACY_LASTMOD
        lines += ["  <url>", f"    <loc>{BASE}{path}</loc>", f"    <lastmod>{lastmod}</lastmod>",
                  f"    <changefreq>{freq}</changefreq>", f"    <priority>{prio}</priority>", "  </url>"]

    for f in files:
        name = os.path.basename(f)
        slug = re.sub(r"\.html$", "", name)
        lines += ["  <url>", f"    <loc>{BASE}/articles/{slug}</loc>",
                  f"    <lastmod>{lastmod_for(name)}</lastmod>", "    <priority>0.7</priority>", "  </url>"]

    lines.append("</urlset>")
    with open("sitemap.xml", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"sitemap.xml: {len(STATIC_URLS)} static + {len(files)} articles")
    return len(files)


if __name__ == "__main__":
    generate_sitemap()
