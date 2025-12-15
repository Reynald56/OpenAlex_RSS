#!/usr/bin/env python3
"""
Ethical OpenAlex RSS Generator — using TOPICS (recommended)
✅ Compliant with OpenAlex ToU: attribution, User-Agent, minimal data
✅ Generates static RSS in /rss/ via GitHub Actions
"""

import os
import requests
from datetime import datetime, timedelta
from feedgen.feed import FeedGenerator

# 🔐 CONFIG — EDIT CONTACT_EMAIL & TOPICS BELOW
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "you@example.org")
PROJECT_NAME = "OpenAlexTopicRSS"

# ✅ Define feeds by TOPIC (not concept!)
# Find Topic IDs at: https://openalex.org/topics
FEEDS = {
    # Example 1: AI Ethics
    "ai-ethics": {
        "topic_id": "T10764",  # "AI ethics" — verify at https://openalex.org/topics/T10764
        "title": "AI Ethics & Responsible AI",
        "description": "Recent scholarly works on AI ethics, algorithmic fairness, and responsible AI systems."
    },
    # Example 2: Large Language Models
    "llms": {
        "topic_id": "T12128",  # "Large language models"
        "title": "Large Language Models (LLMs)",
        "description": "Cutting-edge research on LLMs, training, alignment, and applications."
    },
    # 🌟 Add your own! Format:
    # "your-topic-key": {
    #     "topic_id": "Txxxxx",
    #     "title": "Readable Title",
    #     "description": "1-sentence summary."
    # }
}

RSS_DIR = "rss"
os.makedirs(RSS_DIR, exist_ok=True)

def fetch_works_by_topic(topic_id: str, days_back: int = 30, max_results: int = 20):
    """
    Fetch recent works assigned to a specific OpenAlex Topic.
    ✅ Ethical: minimal select, attribution, rate-respectful (1 call/feed/day)
    """
    since_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    url = "https://api.openalex.org/works"
    params = {
        # ✅ TOPICS filter (recommended by OpenAlex)
        "filter": f"topics.id:{topic_id},from_publication_date:{since_date},is_paratext:false",
        "sort": "publication_date:desc",
        "per-page": max_results,
        # ✅ Minimal data (privacy + efficiency)
        "select": "id,title,doi,publication_date,authorships,primary_location"
    }
    headers = {
        # ✅ REQUIRED by OpenAlex API Policy
        "User-Agent": f"{PROJECT_NAME} ({CONTACT_EMAIL})"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"⚠️ Warning: Failed to fetch Topic {topic_id}: {e}")
        return []

def generate_rss(feed_key: str, config: dict):
    topic_id = config["topic_id"]
    works = fetch_works_by_topic(topic_id)
    
    # Initialize RSS feed
    fg = FeedGenerator()
    fg.id(f"https://openalex.org/topics/{topic_id}")
    fg.title(f"OpenAlex: {config['title']}")
    fg.link(href="https://openalex.org", rel="alternate")
    fg.description(
        f"{config['description']} "
        "Data from OpenAlex (https://openalex.org) — a free, open knowledge base. "
        "Data is CC0; attribution appreciated per OpenAlex Terms."
    )
    fg.language("en")
    fg.rights("CC0. Content sourced from OpenAlex (https://openalex.org).")
    fg.generator(PROJECT_NAME)
    fg.updated(datetime.utcnow())

    # Add entries
    for work in works:
        fe = fg.add_entry()
        title = work.get("title") or "Untitled Work"
        doi = work.get("doi")
        url = doi or work["id"]  # Prefer DOI, fallback to OpenAlex ID

        fe.id(work["id"])
        fe.title(title)
        fe.link(href=url)
        fe.guid(work["id"], permalink=True)

        # Publication date (RSS format)
        pub_date = work.get("publication_date")
        if pub_date:
            try:
                dt = datetime.strptime(pub_date, "%Y-%m-%d")
                fe.pubdate(dt)
            except ValueError:
                pass  # Skip invalid dates

        # Authors (max 5)
        authors = []
        for authorship in work.get("authorships", [])[:5]:
            name = authorship.get("author", {}).get("display_name")
            if name:
                authors.append(name)
        author_str = "; ".join(authors) if authors else "Anonymous"

        # Source (journal/conference)
        source = (
            work
            .get("primary_location", {})
            .get("source", {})
            .get("display_name", "Unknown venue")
        )

        # ✅ ETHICAL DESCRIPTION: no abstracts (copyright-safe)
        description = (
            f"<p><strong>Authors:</strong> {author_str}</p>"
            f"<p><strong>Venue:</strong> {source}</p>"
            f"<p><em>ℹ️ Topic: <a href='https://openalex.org/topics/{topic_id}'>{config['title']}</a> "
            f"(OpenAlex). Data CC0.</em></p>"
        )
        fe.description(description)

    # Write RSS file
    filepath = os.path.join(RSS_DIR, f"{feed_key}.xml")
    fg.rss_file(filepath, pretty=True)
    print(f"✅ Generated {filepath} ({len(works)} works)")


if __name__ == "__main__":
    print("📡 Starting OpenAlex Topic-based RSS generation...")
    for key, config in FEEDS.items():
        generate_rss(key, config)
    print("🎉 All feeds updated. Pushing to GitHub Pages.")
