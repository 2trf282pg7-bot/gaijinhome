#!/usr/bin/env python3
import anthropic
import tweepy
import os
import json
from datetime import datetime

claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

twitter = tweepy.Client(
    consumer_key=os.environ["TWITTER_API_KEY"],
    consumer_secret=os.environ["TWITTER_API_SECRET"],
    access_token=os.environ["TWITTER_ACCESS_TOKEN"],
    access_token_secret=os.environ["TWITTER_ACCESS_SECRET"],
)

SOCIAL_TOPICS = [
    {"topic": "the Medicare Part B penalty trap that surprises Americans retiring abroad", "url": "/guide-medicare.html"},
    {"topic": "why Americans get rejected for the Portugal D7 visa and how to fix it", "url": "/guide-portugal.html"},
    {"topic": "FBAR filing requirements that most American retirees abroad don't know about", "url": "/guide-taxes-fbar.html"},
    {"topic": "what actually happens when your international health insurance claim is denied", "url": "/guide-insurance.html"},
    {"topic": "Social Security WEP reduction that blindsides retirees with government pensions", "url": "/guide-taxes-fbar.html"},
    {"topic": "the hidden costs of retiring in Portugal that expat blogs don't mention", "url": "/guide-portugal.html"},
    {"topic": "Mexico residente temporal visa mistakes that American retirees make", "url": "/guide-mexico.html"},
    {"topic": "how to transfer large sums abroad without triggering US bank holds", "url": "/guide-banking.html"},
    {"topic": "Portugal NHR tax regime — what it actually does for American retirees", "url": "/guide-taxes-fbar.html"},
    {"topic": "IMSS voluntary enrollment for American retirees in Mexico — honest cost breakdown", "url": "/guide-mexico.html"},
    {"topic": "the real cost of buying property in Portugal as an American retiree", "url": "/guide-portugal.html"},
    {"topic": "why Social Security direct deposit problems hit retirees moving to Portugal or Mexico", "url": "/guide-banking.html"},
]

TWEET_SYSTEM_PROMPT = """You are a social media manager for RetireAbroadHub (retireabroad-hub.com).
Write honest, direct tweets for Americans aged 55-70 who are seriously planning to retire in Portugal or Mexico.
- Tone: candid and practical, not cheerleader-ish — these readers distrust hype
- Lead with the problem or the surprising dollar consequence, not a lifestyle pitch
- 2-3 hashtags: #RetireAbroad #PortugalExpat #MexicoExpat #ExpatRetirement
- End with the provided URL
- Under 270 characters total
Output ONLY the tweet text."""


def get_next_topic():
    done_file = "done_social.json"
    if os.path.exists(done_file):
        with open(done_file) as f:
            data = json.load(f)
    else:
        data = {"index": 0}
    idx = data["index"] % len(SOCIAL_TOPICS)
    topic_data = SOCIAL_TOPICS[idx]
    data["index"] = idx + 1
    with open(done_file, "w") as f:
        json.dump(data, f)
    return topic_data


def generate_tweet(topic, url):
    full_url = f"https://retireabroad-hub.com{url}"
    message = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=300,
        system=TWEET_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Write a tweet about: {topic}\nEnd with: {full_url}"}],
    )
    return message.content[0].text.strip()


def post_tweet(text):
    response = twitter.create_tweet(text=text)
    tweet_id = response.data["id"]
    print(f"Posted: https://twitter.com/RetireAbroadHub/status/{tweet_id}")
    return tweet_id


def log_post(topic, tweet_text, tweet_id):
    log_file = "social_log.json"
    if os.path.exists(log_file):
        with open(log_file) as f:
            log = json.load(f)
    else:
        log = []
    log.append({
        "date": datetime.now().isoformat(),
        "topic": topic,
        "tweet": tweet_text,
        "tweet_id": str(tweet_id),
    })
    with open(log_file, "w") as f:
        json.dump(log, f, indent=2)


def main():
    topic_data = get_next_topic()
    tweet_text = generate_tweet(topic_data["topic"], topic_data["url"])
    print(f"Tweet: {tweet_text}")
    tweet_id = post_tweet(tweet_text)
    log_post(topic_data["topic"], tweet_text, tweet_id)
    print("✅ Done!")


if __name__ == "__main__":
    main()
