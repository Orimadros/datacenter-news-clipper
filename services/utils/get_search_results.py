"""
Google News RSS Feed Scraper

This script provides functionality to search Google News via RSS feeds,
using a constructed RSS URL with query, country, and UI language parameters,
and extracts result titles and links published within a given number of days.

Functions:
- collect_search_results_from_rss(feed, days):
    Extracts all items published in the last `days` days from a feedparser feed object.
    Each item is a dict containing 'title' and 'url'.

- build_google_news_rss_url(query, country='br', ui_lang='pt-BR'):
    Constructs the Google News RSS search URL for the given query and localization.

- get_search_results(query, days=7, country='br', ui_lang='pt-BR'):
    Fetches news articles matching `query` from Google News RSS,
    filters by the last `days` days, and returns a list of dicts with 'title', 'source', 'url', and 'pubDate'.

Requirements:
    feedparser
"""

import feedparser
from datetime import datetime, timedelta, timezone
import urllib.parse
from email.utils import parsedate_to_datetime

def collect_search_results_from_rss(feed, days):
    """
    Given a feedparser feed object, collect all items published
    within the last `days` days. Returns a list of dicts:
    [{"title": ..., "source": ..., "url": ..., "pubDate": datetime}, ...].
    
    The RSS title format is expected to be "title - source", which will be split.
    """
    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for entry in feed.entries:
        # Parse publication date using email.utils.parsedate_to_datetime
        try:
            pub_dt = parsedate_to_datetime(entry.published)
            # If pub_dt is naive, assume it's UTC and make it aware
            if pub_dt.tzinfo is None or pub_dt.tzinfo.utcoffset(pub_dt) is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except Exception:
            # Fallback to current UTC time if parsing fails
            pub_dt = datetime.now(timezone.utc)

        # Skip if older than cutoff
        if pub_dt < cutoff:
            continue

        # Extract and split title into title and source
        full_title = entry.title
        url = entry.link
        
        # Split title and source (format: "title - source")
        if " - " in full_title:
            title_parts = full_title.rsplit(" - ", 1)  # Split from the right, only once
            title = title_parts[0].strip()
            source = title_parts[1].strip()
        else:
            # Fallback if no " - " separator found
            title = full_title.strip()
            source = "Unknown"
        
        results.append({
            'title': title,
            'source': source,
            'url': url, 
            'pubDate': pub_dt
        })

    return results

def build_google_news_rss_url(query, country='br', ui_lang='pt-BR'):
    """
    Build a Google News RSS search URL for `query`, localized to `country` and `ui_lang`.
    """
    encoded_query = urllib.parse.quote_plus(query)
    ceid = f"{country.upper()}:{ui_lang}"
    return (
        f"https://news.google.com/rss/search?"
        f"q={encoded_query}&hl={ui_lang}&gl={country.upper()}&ceid={ceid}"
    )

def get_search_results(query, days=7, country='br', ui_lang='pt-BR'):
    """
    Fetch all news items matching `query` from Google News RSS,
    filtered to the last `days` days. Fallback to exact-quoted query if no results.
    Returns a list of dicts with 'title', 'source', 'url', and 'pubDate'.
    """
    # 1) Unquoted query
    rss_url = build_google_news_rss_url(query, country=country)
    feed = feedparser.parse(rss_url)
    results = collect_search_results_from_rss(feed, days)

    # 2) Fallback if no results
    if not results:
        quoted = f'"{query}"'
        rss_url = build_google_news_rss_url(quoted, country=country)
        feed = feedparser.parse(rss_url)
        results = collect_search_results_from_rss(feed, days)

    return results

if __name__ == '__main__':
    # Example usage
    query = 'datacenter brasil'
    results = get_search_results(query, days=7, country='br')
    for i, item in enumerate(results, 1):
        print(f"{i}. {item['title']} - {item['source']} - {item['url']} (Published: {item['pubDate']})")
