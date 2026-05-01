#!/usr/bin/env python3
"""
GaijinHome - Sitemap Auto-Updater
Run this after generating new articles to keep sitemap.xml current.
This script is called automatically by generate-article.yml
"""

import os
import glob
from datetime import datetime

STATIC_URLS = [
    {"loc": "https://gaijinhome.com/", "lastmod": "2026-04-01", "changefreq": "weekly", "priority": "1.0"},
    {"loc": "https://gaijinhome.com/guide-complete", "lastmod": "2026-04-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": "https://gaijinhome.com/guide-no-guarantor", "lastmod": "2026-04-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": "https://gaijinhome.com/guide-rejection", "lastmod": "2026-04-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": "https://gaijinhome.com/guide-hidden-costs", "lastmod": "2026-04-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": "https://gaijinhome.com/guide-osaka-kansai", "lastmod": "2026-04-01", "changefreq": "monthly", "priority": "0.8"},
    {"loc": "https://gaijinhome.com/guide-visa-breakdown", "lastmod": "2026-04-01", "changefreq": "monthly", "priority": "0.8"},
]

def get_article_files():
    """Scan articles/ directory and return list of HTML files."""
    articles = glob.glob("articles/*.html")
    articles.sort()
    return articles

def filename_to_url(filepath):
    """Convert filepath like articles/guide-foo.html to full URL."""
    filename = os.path.basename(filepath)
    return f"https://gaijinhome.com/articles/{filename}"

def get_file_date(filepath):
    """Get file modification date in YYYY-MM-DD format."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def generate_sitemap():
    articles = get_article_files()
    
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    # Static pages
    for url in STATIC_URLS:
        lines.append('  <url>')
        lines.append(f'    <loc>{url["loc"]}</loc>')
        lines.append(f'    <lastmod>{url["lastmod"]}</lastmod>')
        lines.append(f'    <changefreq>{url["changefreq"]}</changefreq>')
        lines.append(f'    <priority>{url["priority"]}</priority>')
        lines.append('  </url>')
    
    # Auto-generated articles
    for filepath in articles:
        url = filename_to_url(filepath)
        date = get_file_date(filepath)
        lines.append('  <url>')
        lines.append(f'    <loc>{url}</loc>')
        lines.append(f'    <lastmod>{date}</lastmod>')
        lines.append(f'    <priority>0.8</priority>')
        lines.append('  </url>')
    
    lines.append('</urlset>')
    
    content = "\n".join(lines)
    
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ sitemap.xml updated: {len(STATIC_URLS)} static + {len(articles)} articles = {len(STATIC_URLS) + len(articles)} total URLs")
    return len(articles)

if __name__ == "__main__":
    count = generate_sitemap()
    print(f"Total articles in sitemap: {count}")
