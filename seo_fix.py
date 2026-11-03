#!/usr/bin/env python3
"""
GaijinHome - SEO normalizer (idempotent).

For every HTML page in the repo:
- canonical / og:url  -> https://gaijinhome.com/<clean path> (no www, no .html)
- internal links      -> absolute clean paths (no .html), duplicate guides mapped
                         to the single surviving page

Run after any generation step: python seo_fix.py
"""

import glob
import os
import re

BASE = "https://gaijinhome.com"

# Duplicate / removed pages -> surviving page (also mirrored in vercel.json)
PAGE_MAP = {
    "guide-complete": "full-guide",
    "guide-no-guarantor": "no-guarantor",
    "guide-rejection": "rejected",
    "guide-hidden-costs": "hidden-costs",
    "guide-osaka-kansai": "osaka",
    "guide-visa-breakdown": "visa-guide",
    "guide-germany-immigration": "",
    "guides": "articles",
    "listings": "articles",
    "index": "",
}


def page_paths():
    files = glob.glob("*.html") + glob.glob("articles/*.html")
    return sorted(f for f in files if not os.path.basename(f).startswith("google"))


def clean_path_for_file(filepath):
    """articles/foo.html -> /articles/foo ; index.html -> / ; articles/index.html -> /articles"""
    p = filepath.replace(os.sep, "/")
    p = re.sub(r"\.html$", "", p)
    if p == "index":
        return "/"
    if p.endswith("/index"):
        p = p[: -len("/index")]
    return "/" + p


def normalize_href(href, current_dir):
    """Return the cleaned internal href, or None to leave it untouched."""
    m = re.match(r"^(?:https?://(?:www\.)?gaijinhome\.com)?([^?#]*)([?#].*)?$", href)
    if not m:
        return None
    path, suffix = m.group(1), m.group(2) or ""
    is_abs_site = href.startswith("http")
    if not is_abs_site and re.match(r"^[a-z]+:", href):
        return None  # mailto:, tel:, javascript:, other schemes
    if href.startswith("//") or href.startswith("#") or path == "":
        return None
    if not is_abs_site and not path.startswith("/"):
        # relative link -> resolve against the current page directory
        path = "/" + os.path.normpath(os.path.join(current_dir, path)).replace(os.sep, "/").lstrip("./")
    if re.search(r"\.(css|js|png|jpe?g|svg|webp|ico|xml|txt|pdf)$", path, re.I):
        return None

    path = re.sub(r"\.html$", "", path)
    if path.endswith("/index"):
        path = path[: -len("/index")] or "/"
    parts = path.strip("/").split("/")
    if len(parts) == 1 and parts[0] in PAGE_MAP:
        target = PAGE_MAP[parts[0]]
        path = "/" + target if target else "/"
    if path != "/":
        path = path.rstrip("/")
    return (path or "/") + suffix


def fix_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        html = f.read()
    original = html
    current_dir = os.path.dirname(filepath)
    canonical = BASE + clean_path_for_file(filepath)
    if canonical.endswith("/") and canonical != BASE + "/":
        canonical = canonical.rstrip("/")

    # 1. canonical
    tag = f'<link rel="canonical" href="{canonical}">'
    if re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*>', html, re.I):
        html = re.sub(r'<link[^>]+rel=["\']canonical["\'][^>]*>', tag, html, flags=re.I)
    elif re.search(r"</head>", html, re.I):
        html = re.sub(r"</head>", f"  {tag}\n</head>", html, count=1, flags=re.I)

    # 2. og:url
    html = re.sub(
        r'(<meta[^>]+property=["\']og:url["\'][^>]+content=["\'])[^"\']*(["\'])',
        lambda m: m.group(1) + canonical + m.group(2),
        html,
        flags=re.I,
    )

    # 2b. JSON-LD page URLs pointing at this site
    html = re.sub(
        r'("(?:mainEntityOfPage|@id|url)"\s*:\s*")https?://(?:www\.)?gaijinhome\.com/[^"]*\.html(")',
        lambda m: m.group(1) + canonical + m.group(2),
        html,
    )

    # 3. internal links
    def repl(m):
        new = normalize_href(m.group(2), current_dir)
        return m.group(0) if new is None else f"{m.group(1)}{new}{m.group(3)}"

    html = re.sub(r'(<a\b[^>]*?\bhref=")([^"]*)(")', repl, html, flags=re.I)

    if html != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    return False


def run_all():
    changed = [p for p in page_paths() if fix_file(p)]
    print(f"seo_fix: {len(changed)} file(s) updated")
    return changed


if __name__ == "__main__":
    run_all()
