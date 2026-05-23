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
    {"topic": "common mistakes foreigners make when apartment hunting in Japan", "url": "/guide-complete.html"},
    {"topic": "how to rent without a Japanese guarantor", "url": "/guide-no-guarantor.html"},
    {"topic": "why foreigners get rejected by Japanese landlords", "url": "/guide-rejection.html"},
    {"topic": "hidden costs when renting in Japan", "url": "/guide-hidden-costs.html"},
    {"topic": "renting in Osaka vs Tokyo as a foreigner", "url": "/guide-osaka-kansai.html"},
    {"topic": "which visa types Japanese landlords actually accept", "url": "/guide-visa-breakdown.html"},
    {"topic": "share houses vs apartments for foreigners in Japan", "url": "/guide-no-guarantor.html"},
    {"topic": "how to get your deposit back in Japan", "url": "/guide-hidden-costs.html"},
    {"topic": "best areas in Tokyo for English-speaking foreigners", "url": "/guide-complete.html"},
    {"topic": "working holiday visa apartment hunting Japan", "url": "/guide-visa-breakdown.html"},
]

TWEET_SYSTEM_PROMPT = """You are a social media manager for GaijinHome (gaijinhome.com).
Write helpful, practical tweets for foreigners renting in Japan.
- Genuine and human, not promotional
- 2-3 hashtags: #expatjapan #movingtojapan #japanlife #tokyoliving
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
    full_url = f"https://gaijinhome.com{url}"
    message = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=300,
        system=TWEET_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Write a tweet about: {topic}\nEnd with: {full_url}"}]
    )
    return message.content[0].text.strip()

def post_tweet(text):
    response = twitter.create_tweet(text=text)
    tweet_id = response.data["id"]
    print(f"Posted: https://twitter.com/GaijinHome/status/{tweet_id}")
    return tweet_id

def log_post(topic, tweet_text, tweet_id):
    log_file = "social_log.json"
    if os.path.exists(log_file):
        with open(log_file) as f:
            log = json.load(f)
    else:
        log = []
    log.append({"date": datetime.now().isoformat(), "topic": topic, "tweet": tweet_text, "tweet_id": str(tweet_id)})
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
