#!/usr/bin/env python3
"""
One-time script: update title and meta description of all existing articles
to the problem-solving format required by the new article strategy.
"""
import re
import os

ARTICLE_UPDATES = {
    "guide-apartment-hunting-japan-student-visa.html": {
        "title": "Student Visa Apartment Application Rejected in Japan? What to Do Next",
        "description": "If your apartment application was rejected while on a student visa in Japan, here are the exact reasons and alternatives that actually work for international students.",
    },
    "guide-apartment-japan-without-japanese-guarantor.html": {
        "title": "Guarantor Refused in Japan? How Foreigners Get Approved Without a Japanese Guarantor",
        "description": "If your apartment application was denied due to no Japanese guarantor, here are the exact alternatives and guarantor companies foreigners actually use.",
    },
    "guide-cheap-apartments-tokyo-foreigner.html": {
        "title": "Why Foreigners Struggle to Find Affordable Apartments in Tokyo — Real Solutions",
        "description": "Struggling to find an affordable apartment in Tokyo as a foreigner? Here are the exact methods and platforms that work for under ¥70,000/month.",
    },
    "guide-english-speaking-real-estate-agent-tokyo.html": {
        "title": "Real Estate Agents Refusing Foreigners in Tokyo? Finding English-Speaking Help That Works",
        "description": "Confused about finding an English-speaking real estate agent in Tokyo? Here's exactly who actually helps foreigners and how to avoid agents who refuse.",
    },
    "guide-foreigner-apartment-fukuoka-english-speaking.html": {
        "title": "Apartment Rejected in Fukuoka as a Foreigner? English-Speaking Solutions That Work",
        "description": "If your apartment application was rejected in Fukuoka, here are the exact English-speaking agencies and workarounds that foreigners actually use.",
    },
    "guide-foreigner-apartment-in-japan-without-bank-account.html": {
        "title": "Apartment Denied in Japan Because You Have No Bank Account? What to Do",
        "description": "If your apartment application was rejected due to no bank account in Japan, here are the exact alternatives and steps foreigners use to get approved.",
    },
    "guide-foreigner-apartment-kyoto-english-speaking-landlord.html": {
        "title": "Apartment Rejected in Kyoto as a Foreigner? Finding English-Speaking Landlords Who Say Yes",
        "description": "Struggling to find an apartment in Kyoto as a foreigner? Here's exactly which English-speaking landlords and agencies approve foreigners without the usual rejection.",
    },
    "guide-foreigner-apartment-nagoya-english-speaking.html": {
        "title": "Apartment Rejection Problems in Nagoya for Foreigners — What Actually Works",
        "description": "If your apartment application in Nagoya was rejected as a foreigner, here are the exact English-speaking agencies and steps that get foreigners approved.",
    },
    "guide-foreigner-apartment-tokyo-bike-parking.html": {
        "title": "Bike Parking Denied at Tokyo Apartments? What Foreigner Renters Need to Know",
        "description": "Confused about bike parking rules at Tokyo apartments as a foreigner? Here are the exact parking types, costs, and what to do when you're denied.",
    },
    "guide-foreigner-apartment-yokohama-english-speaking.html": {
        "title": "Apartment Rejected in Yokohama as a Foreigner? English-Speaking Fixes That Work",
        "description": "If your apartment application was rejected in Yokohama, here are the exact English-speaking agencies and workarounds that foreigners in Japan actually use.",
    },
    "guide-foreigner-friendly-apartments-osaka.html": {
        "title": "Why Foreigners Get Rejected for Apartments in Osaka — And What To Do Next",
        "description": "If your apartment application was rejected in Osaka, here are the exact reasons why and the foreigner-friendly agencies that actually approve foreigners.",
    },
    "guide-foreigner-friendly-apartments-tokyo-english-landlord.html": {
        "title": "Why Foreigners Get Rejected for Apartments in Tokyo — And What To Do Next",
        "description": "If your apartment application was rejected in Tokyo, here are the exact reasons why and the English-speaking landlords who actually approve foreigners.",
    },
    "guide-foreigner-renting-japan-self-employed.html": {
        "title": "Self-Employed Foreigner Rejected for Apartment in Japan? Exact Fixes and Workarounds",
        "description": "If your apartment application was rejected because you're self-employed in Japan, here are the exact documents and guarantor strategies that actually work.",
    },
    "guide-furnished-apartments-tokyo-short-term-foreigner.html": {
        "title": "Short-Term Furnished Apartments in Tokyo Denied? What Foreigners Actually Get Approved",
        "description": "Struggling to find a furnished short-term apartment in Tokyo as a foreigner? Here are the exact platforms and workarounds that bypass the usual rejection.",
    },
    "guide-how-to-pass-credit-check-japan-foreigner.html": {
        "title": "Credit Check Failed in Japan as a Foreigner? Exact Reasons and Step-by-Step Fixes",
        "description": "If your credit check failed for an apartment in Japan, here are the exact reasons why and the guarantor strategies that get foreigners approved.",
    },
    "guide-how-to-rent-apartment-japan-work-visa.html": {
        "title": "Apartment Rejected in Japan on a Work Visa? What You're Missing and What to Do",
        "description": "If your apartment application was rejected despite having a work visa in Japan, here are the exact missing documents and agencies that approve foreigners.",
    },
    "guide-japan-apartment-deposit-refund-tips.html": {
        "title": "Deposit Refund Denied in Japan? Fight Unfair Deductions and Get Your Money Back",
        "description": "If your apartment deposit was denied or deducted unfairly in Japan, here are the exact legal rights, dispute steps, and documents that get your shikikin back.",
    },
    "guide-monthly-mansion-japan-foreigner.html": {
        "title": "Monthly Mansion Application Rejected in Japan as a Foreigner? What Actually Works",
        "description": "If your monthly mansion application was rejected in Japan, here are the exact providers and requirements that foreigners use to get approved without a guarantor.",
    },
    "guide-no-guarantor-apartments-tokyo.html": {
        "title": "Apartment Rejected in Tokyo Because You Have No Guarantor? Here's What Foreigners Do",
        "description": "If your Tokyo apartment application was rejected due to no guarantor, here are the exact guarantor companies and foreigner-friendly agencies that solve this problem.",
    },
    "guide-osaka-foreigner-apartment-no-guarantor.html": {
        "title": "Apartment Denied in Osaka Because You Have No Guarantor? Exact Fixes for Foreigners",
        "description": "If your apartment application was denied in Osaka due to no guarantor, here are the exact guarantor companies and agencies that approve foreigners in Kansai.",
    },
    "guide-renting-apartment-japan-permanent-resident.html": {
        "title": "Permanent Resident Rejected for Apartment in Japan? Why It Still Happens and What to Do",
        "description": "Confused about why your apartment application was rejected despite having permanent residency in Japan? Here are the exact reasons and step-by-step fixes.",
    },
    "guide-share-house-tokyo-foreigner-english.html": {
        "title": "Share House Application Rejected in Tokyo as a Foreigner? What Actually Gets You In",
        "description": "If your share house application was rejected in Tokyo, here are the exact English-speaking options and requirements that foreigners use to get approved.",
    },
    "guide-ur-housing-foreigner-apply.html": {
        "title": "UR Housing Application Denied for Foreigners in Japan? Exact Reasons and Fixes",
        "description": "If your UR Housing application was denied in Japan, here are the exact income requirements, document checklist, and alternatives that work for foreigners.",
    },
}


def update_article(filepath, new_title, new_description):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    old_title_match = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
    old_desc_match = re.search(r'<meta\s+name="description"\s+content="(.*?)"', content, re.DOTALL)

    old_title = old_title_match.group(1).strip() if old_title_match else "(not found)"
    old_desc = old_desc_match.group(1).strip() if old_desc_match else "(not found)"

    content = re.sub(r'<title>.*?</title>', f'<title>{new_title}</title>', content, flags=re.DOTALL)
    content = re.sub(
        r'(<meta\s+name="description"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_description + m.group(2),
        content
    )

    # Also update og:title and og:description if present
    content = re.sub(
        r'(<meta\s+property="og:title"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_title + m.group(2),
        content
    )
    content = re.sub(
        r'(<meta\s+property="og:description"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_description + m.group(2),
        content
    )
    # Also update twitter:title if present
    content = re.sub(
        r'(<meta\s+name="twitter:title"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_title + m.group(2),
        content
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return old_title, old_desc


def main():
    articles_dir = "articles"
    print("=" * 70)
    print("Article title/description update — before/after diff")
    print("=" * 70)

    updated = 0
    for filename, updates in ARTICLE_UPDATES.items():
        filepath = os.path.join(articles_dir, filename)
        if not os.path.exists(filepath):
            print(f"[SKIP] {filename} — file not found")
            continue

        old_title, old_desc = update_article(filepath, updates["title"], updates["description"])

        print(f"\n--- {filename}")
        print(f"  TITLE before : {old_title}")
        print(f"  TITLE after  : {updates['title']}")
        print(f"  DESC before  : {old_desc}")
        print(f"  DESC after   : {updates['description']}")
        updated += 1

    print(f"\n✅ Updated {updated} articles.")


if __name__ == "__main__":
    main()
