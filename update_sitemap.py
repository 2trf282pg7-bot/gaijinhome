#!/usr/bin/env python3
import os
import glob
from datetime import datetime

SITE_DOMAIN = "retireabroad-hub.com"

STATIC_URLS = [
    {"loc": f"https://{SITE_DOMAIN}/", "lastmod": "2026-05-01", "changefreq": "weekly", "priority": "1.0"},
    {"loc": f"https://{SITE_DOMAIN}/guide-medicare", "lastmod": "2026-05-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": f"https://{SITE_DOMAIN}/guide-taxes-fbar", "lastmod": "2026-05-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": f"https://{SITE_DOMAIN}/guide-portugal", "lastmod": "2026-05-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": f"https://{SITE_DOMAIN}/guide-mexico", "lastmod": "2026-05-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": f"https://{SITE_DOMAIN}/guide-insurance", "lastmod": "2026-05-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": f"https://{SITE_DOMAIN}/guide-banking", "lastmod": "2026-05-01", "changefreq": "monthly", "priority": "0.8"},
]


def get_article_files():
    articles = glob.glob("articles/*.html")
    articles.sort()
    return articles


def filename_to_url(filepath):
    filename = os.path.basename(filepath)
    return f"https://{SITE_DOMAIN}/articles/{filename}"


def get_file_date(filepath):
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def generate_sitemap():
    articles = get_article_files()

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for url in STATIC_URLS:
        lines.append("  <url>")
        lines.append(f'    <loc>{url["loc"]}</loc>')
        lines.append(f'    <lastmod>{url["lastmod"]}</lastmod>')
        lines.append(f'    <changefreq>{url["changefreq"]}</changefreq>')
        lines.append(f'    <priority>{url["priority"]}</priority>')
        lines.append("  </url>")

    for filepath in articles:
        url = filename_to_url(filepath)
        date = get_file_date(filepath)
        lines.append("  <url>")
        lines.append(f"    <loc>{url}</loc>")
        lines.append(f"    <lastmod>{date}</lastmod>")
        lines.append("    <priority>0.8</priority>")
        lines.append("  </url>")

    lines.append("</urlset>")

    content = "\n".join(lines)
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ sitemap.xml updated: {len(STATIC_URLS)} static + {len(articles)} articles = {len(STATIC_URLS) + len(articles)} total URLs")
    return len(articles)


if __name__ == "__main__":
    count = generate_sitemap()
    print(f"Total articles in sitemap: {count}")
