#!/usr/bin/env python3
"""
GaijinHome - Traffic Monitor & Email Notifier
Uses OAuth2 credentials instead of service account.
"""

import os
import json
import requests
from datetime import datetime, timedelta

SITE_URL = "sc-domain:gaijinhome.com"
THRESHOLD_CLICKS = 1

def get_access_token():
    """Get access token using OAuth2 refresh token."""
    refresh_token = os.environ.get("GSC_REFRESH_TOKEN")
    client_id = os.environ.get("GSC_CLIENT_ID")
    client_secret = os.environ.get("GSC_CLIENT_SECRET")
    
    if not all([refresh_token, client_id, client_secret]):
        raise ValueError("GSC OAuth credentials not set in secrets")
    
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    return resp.json()["access_token"]

def get_traffic_data(token):
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    resp = requests.post(
        f"https://searchconsole.googleapis.com/webmasters/v3/sites/{SITE_URL.replace(':', '%3A')}/searchAnalytics/query",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query"],
            "rowLimit": 10,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}]
        }
    )
    
    data = resp.json()
    rows = data.get("rows", [])
    total_clicks = sum(row.get("clicks", 0) for row in rows)
    total_impressions = sum(row.get("impressions", 0) for row in rows)
    
    top_queries = [
        {
            "query": row["keys"][0],
            "clicks": int(row.get("clicks", 0)),
            "impressions": int(row.get("impressions", 0)),
            "position": round(row.get("position", 0), 1)
        }
        for row in rows[:5]
    ]
    
    return {
        "total_clicks": int(total_clicks),
        "total_impressions": int(total_impressions),
        "top_queries": top_queries,
        "period": f"{start_date} 〜 {end_date}"
    }

def should_notify(data, last_notified_file="last_traffic_notified.json"):
    clicks = data["total_clicks"]
    if clicks < THRESHOLD_CLICKS:
        print(f"No traffic yet. Clicks: {clicks}")
        return False
    if os.path.exists(last_notified_file):
        with open(last_notified_file) as f:
            last = json.load(f)
        if last.get("clicks", 0) >= clicks:
            print(f"Already notified for {clicks} clicks.")
            return False
    with open(last_notified_file, "w") as f:
        json.dump({"clicks": clicks, "date": datetime.now().isoformat()}, f)
    return True

def send_email_notification(data):
    api_key = os.environ.get("SENDGRID_API_KEY")
    notify_email = os.environ.get("NOTIFY_EMAIL")
    
    if not api_key or not notify_email:
        print("SendGrid credentials not set.")
        return
    
    top_queries_html = "".join([
        f"<tr><td style='padding:8px'>{q['query']}</td><td style='padding:8px;text-align:center'>{q['clicks']}</td><td style='padding:8px;text-align:center'>{q['impressions']}</td><td style='padding:8px;text-align:center'>{q['position']}</td></tr>"
        for q in data["top_queries"]
    ])
    
    html_body = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#E8372A;">🎉 GaijinHome に流入が始まりました！</h2>
      <p>期間: {data['period']}</p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0;">
        <tr>
          <td style="background:#E8372A;color:white;padding:16px;text-align:center;border-radius:8px 0 0 8px;">
            <div style="font-size:32px;font-weight:bold;">{data['total_clicks']}</div>
            <div>クリック数</div>
          </td>
          <td style="background:#333;color:white;padding:16px;text-align:center;border-radius:0 8px 8px 0;">
            <div style="font-size:32px;font-weight:bold;">{data['total_impressions']}</div>
            <div>表示回数</div>
          </td>
        </tr>
      </table>
      <h3>上位キーワード</h3>
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr style="background:#f5f5f5;">
          <th style="padding:8px;text-align:left;">検索ワード</th>
          <th style="padding:8px;">クリック</th>
          <th style="padding:8px;">表示</th>
          <th style="padding:8px;">順位</th>
        </tr></thead>
        <tbody>{top_queries_html}</tbody>
      </table>
      <p style="margin-top:24px;">
        <a href="https://search.google.com/search-console" style="background:#E8372A;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;">
          サーチコンソールで詳細を確認 →
        </a>
      </p>
    </div>
    """
    
    payload = {
        "personalizations": [{"to": [{"email": notify_email}]}],
        "from": {"email": notify_email, "name": "GaijinHome Bot"},
        "subject": f"🎉 GaijinHome 流入開始！ {data['total_clicks']}クリック / {data['total_impressions']}表示",
        "content": [{"type": "text/html", "value": html_body}]
    }
    
    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload
    )
    
    if resp.status_code == 202:
        print(f"✅ Email sent to {notify_email}")
    else:
        print(f"❌ Email failed: {resp.status_code} {resp.text}")

def print_report(data):
    print("=" * 50)
    print(f"GaijinHome Traffic Report ({data['period']})")
    print("=" * 50)
    print(f"Total clicks:      {data['total_clicks']}")
    print(f"Total impressions: {data['total_impressions']}")
    if data["top_queries"]:
        print("Top queries:")
        for q in data["top_queries"]:
            print(f"  {q['query']:<40} clicks:{q['clicks']}  impressions:{q['impressions']}  pos:{q['position']}")
    else:
        print("No search queries yet.")
    print("=" * 50)

if __name__ == "__main__":
    try:
        token = get_access_token()
        data = get_traffic_data(token)
        print_report(data)
        if should_notify(data):
            print("Traffic detected! Sending notification...")
            send_email_notification(data)
        else:
            print("No notification needed.")
    except Exception as e:
        print(f"Error: {e}")
        raise
