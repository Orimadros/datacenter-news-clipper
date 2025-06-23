# services/scraper.py

import time
import tempfile
import os
from typing import List, Dict, Tuple

from docling.document_converter import DocumentConverter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def scrape_article_text(
    url: str,
    headless: bool = True,
    page_load_wait: float = 2.0
) -> Tuple[str, str]:
    """
    1) Launch headless Chrome via Selenium.
    2) Navigate to the RSS‐wrapper URL.
    3) Sleep briefly (allow Google's JS/injection to finish loading).
    4) Grab driver.page_source (the on‐screen HTML that Docling can parse).
    5) Write that HTML to a temp .html file and pass its path to Docling.
    6) Delete the temp file and return Docling's Markdown.
    """

    # 1) Configure ChromeOptions
    chrome_opts = Options()
    if headless:
        chrome_opts.add_argument("--headless")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    # A realistic User-Agent sometimes helps Google serve full content:
    chrome_opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts
    )

    try:
        # 2) Navigate to the Google News RSS article URL (wrapper)
        driver.get(url)

        # 3) Wait a moment so that any JS/meta-refresh can finish loading
        time.sleep(page_load_wait)

        # Capture the real URL after redirects
        real_url = driver.current_url

        # 4) Grab the full HTML of whatever is on-screen now
        final_html = driver.page_source

    finally:
        driver.quit()

    # 5) Write that HTML into a temporary .html file on disk
    tmp_file = tempfile.NamedTemporaryFile(
        suffix=".html",
        delete=False,
        mode="w",
        encoding="utf-8"
    )
    try:
        tmp_path = tmp_file.name
        tmp_file.write(final_html)
        tmp_file.flush()
        tmp_file.close()

        # 6) Feed the file path into Docling's converter
        converter = DocumentConverter()
        result = converter.convert(tmp_path)
        content_md = result.document.export_to_markdown()

    finally:
        # 7) Always delete the temp file afterward
        os.unlink(tmp_path)

    return content_md, real_url


def scrape_articles(items: List[Dict]) -> List[Dict]:
    """
    For each item (which must have 'url'), call scrape_article_text()
    and store the Markdown in item['body'].
    """
    scraped = []
    for item in items:
        try:
            # Scrape and get real URL
            body, real_url = scrape_article_text(item["url"])
            # Update item URL to the actual article URL
            item["url"] = real_url
        except Exception as e:
            print(f"[Warning] Failed to scrape {item['url']}: {e}")
            body = ""
        item["body"] = body
        scraped.append(item)
    return scraped


if __name__ == "__main__":
    # Quick test: pass a Google‐RSS wrapper URL and print the Markdown
    test_url = (
        "https://news.google.com/rss/articles/CBMi7AFBVV95cUxQa0lBUXo4THktUVBNQ3JTZ0d3dWpwWEJuc3EzaEFV"
        "bndtX1JwY1NVOEZ2U3pBMl9zYUJRdU1WOTN5bGxMdG02OEdzZjZvOU9ieVY4eHV3X2Z1X2FWdmRjWC1VSkZfMFRHOWRjcUdw"
        "ZDJ3REFZMzBTZjVmY2pEM1BRNjZqS3hWYmJwWEJBLWhZV1hPTTQyYWY2UWk4d2ZmdDJWNXJPT2VXOEkzempKLXphaGpvVHBE"
        "SEVFaEV5VkdzOHRzdWl3RkhMMFMxOW9TNWQxamlCZXVnZFNSQVRTdENkem9OYWFCLXNta0dqeQ?oc=5"
    )
    md, real_url = scrape_article_text(test_url)
    print("\n=== Extracted Markdown ===\n")
    print(md)
    print("\n=== Real URL ===\n")
    print(real_url)
