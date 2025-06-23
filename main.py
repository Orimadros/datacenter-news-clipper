import os
import json
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from datetime import datetime
from dotenv import load_dotenv
from services.utils.get_search_results import get_search_results
from services.classifier import add_classifications, drop_irrelevant
from services.scraper import scrape_articles
from services.summarizer import add_summaries
from services.deduplicator import deduplicate_by_summary
from services.pdf_builder import build_pdf

"""
Entry point for the DC News pipeline:
1. Load query configs
2. Fetch RSS search results
3. Deduplicate by URL
4. Classify items as relevant or irrelevant (adds 'class' key)
5. Filter only relevant news pieces
6. Scrape article bodies via Selenium + Docling
7. Summarize bodies via LangChain
8. Remove duplicate coverage based on summary similarity
9. Store news piece metadata and summaries in output.json
10. Generate PDF clipping
"""

def main():
    # Load environment variables
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # 1) Load query configurations
    with open("configs/queries.json", "r", encoding="utf-8") as f:
        configs = json.load(f)

    # 2) Fetch all search results
    all_items = []
    for cfg in configs:
        query = cfg.get("query")
        days = cfg.get("days", 7)
        country = cfg.get("country", "br")
        print(f"[{datetime.now()}] Searching for '{query}' (last {days} days, country={country})...")
        results = get_search_results(query, days=days, country=country)
        all_items.extend(results)
    print(f"Fetched {len(all_items)} items from RSS feeds")

    # 3) Deduplicate by URL
    seen = set()
    unique_items = []
    for item in all_items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique_items.append(item)
    print(f"{len(unique_items)} unique items after deduplication")

    if not unique_items:
        print("No items fetched. Exiting.")
        return

    # 4) Classify (annotate with 'class')
    annotated = add_classifications(unique_items)
    print(f"Annotated {len(annotated)} items with class labels")

    # 5) Filter only relevant items
    relevant_items = drop_irrelevant(annotated)
    print(f"{len(relevant_items)} relevant items remain after filtering")
    if not relevant_items:
        print("No relevant articles. Exiting.")
        return

    # 6) Scrape article bodies
    scraped_items = scrape_articles(relevant_items)
    print(f"Scraped bodies for {len(scraped_items)} items")

    # 7) Summarize
    summarized_items = add_summaries(scraped_items)
    print(f"Generated summaries for {len(summarized_items)} items")

    # 8) Remove duplicate coverage based on summary similarity
    deduplicated_items = deduplicate_by_summary(summarized_items)
    print(f"Final count after semantic deduplication: {len(deduplicated_items)} items")

    # 9) Write output file
    output_file = "output/clippings.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as out_f:
        json.dump(deduplicated_items, out_f, ensure_ascii=False, indent=2)
    print(f"Wrote clippings JSON to {output_file}")

    # 10) Generate PDF
    pdf_path = build_pdf()
    print(f"Generated PDF clipping at {pdf_path}")

if __name__ == "__main__":
    main() 