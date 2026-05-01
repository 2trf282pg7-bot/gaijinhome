#!/usr/bin/env python3
"""
GaijinHome - API Cost Checker
Reads article generation logs and estimates total Anthropic API cost.
Run manually: python check_cost.py
"""

import json
import os
import glob
from datetime import datetime

# Pricing as of 2025 (per 1M tokens)
# claude-haiku-4-5: $1 input / $5 output
# claude-sonnet-4-6: $3 input / $15 output
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 1.0 / 1_000_000, "output": 5.0 / 1_000_000},
    "claude-haiku-4-5": {"input": 1.0 / 1_000_000, "output": 5.0 / 1_000_000},
    "claude-sonnet-4-6": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "claude-opus-4-6": {"input": 5.0 / 1_000_000, "output": 25.0 / 1_000_000},
    # fallback
    "default": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
}

def estimate_from_articles():
    """Estimate cost based on number of generated articles."""
    articles = glob.glob("articles/*.html")
    count = len(articles)
    
    # Rough estimate: each article ~500 input tokens + 3000 output tokens (Sonnet)
    input_tokens = count * 500
    output_tokens = count * 3000
    
    price = PRICING["claude-sonnet-4-6"]
    cost_usd = (input_tokens * price["input"]) + (output_tokens * price["output"])
    cost_jpy = cost_usd * 150  # approximate JPY rate
    
    print("=" * 50)
    print("GaijinHome API Cost Estimate")
    print("=" * 50)
    print(f"Articles generated: {count}")
    print(f"Estimated input tokens: {input_tokens:,}")
    print(f"Estimated output tokens: {output_tokens:,}")
    print(f"Estimated cost (USD): ${cost_usd:.4f}")
    print(f"Estimated cost (JPY): ¥{cost_jpy:.1f}")
    print()
    print("Monthly projection (30 articles/month):")
    monthly_cost_usd = (500 * 30 * price["input"]) + (3000 * 30 * price["output"])
    monthly_cost_jpy = monthly_cost_usd * 150
    print(f"  USD: ${monthly_cost_usd:.4f}/month")
    print(f"  JPY: ¥{monthly_cost_jpy:.1f}/month")
    print("=" * 50)
    
    return {
        "articles": count,
        "estimated_cost_usd": round(cost_usd, 4),
        "estimated_cost_jpy": round(cost_jpy, 1),
        "monthly_projection_usd": round(monthly_cost_usd, 4),
        "monthly_projection_jpy": round(monthly_cost_jpy, 1),
    }

def read_usage_log():
    """Read actual usage log if it exists."""
    log_file = "api_usage_log.json"
    if not os.path.exists(log_file):
        print(f"No usage log found at {log_file}. Using article count estimate instead.")
        return None
    
    with open(log_file) as f:
        logs = json.load(f)
    
    total_input = sum(entry.get("input_tokens", 0) for entry in logs)
    total_output = sum(entry.get("output_tokens", 0) for entry in logs)
    
    # group by model
    by_model = {}
    for entry in logs:
        model = entry.get("model", "default")
        by_model.setdefault(model, {"input": 0, "output": 0, "count": 0})
        by_model[model]["input"] += entry.get("input_tokens", 0)
        by_model[model]["output"] += entry.get("output_tokens", 0)
        by_model[model]["count"] += 1
    
    total_cost_usd = 0
    print("=" * 50)
    print("GaijinHome API Actual Usage")
    print("=" * 50)
    for model, usage in by_model.items():
        price = PRICING.get(model, PRICING["default"])
        cost = (usage["input"] * price["input"]) + (usage["output"] * price["output"])
        total_cost_usd += cost
        print(f"Model: {model}")
        print(f"  Runs: {usage['count']}")
        print(f"  Input tokens: {usage['input']:,}")
        print(f"  Output tokens: {usage['output']:,}")
        print(f"  Cost: ${cost:.4f}")
    
    total_cost_jpy = total_cost_usd * 150
    print(f"\nTotal cost (USD): ${total_cost_usd:.4f}")
    print(f"Total cost (JPY): ¥{total_cost_jpy:.1f}")
    print("=" * 50)
    
    return {"total_usd": total_cost_usd, "total_jpy": total_cost_jpy}

if __name__ == "__main__":
    result = read_usage_log()
    if result is None:
        estimate_from_articles()
