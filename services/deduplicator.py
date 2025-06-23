# services/deduplicator.py

import os
import json
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
from dateutil import parser

from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

# Enhanced system prompt for more accurate duplicate detection
BATCH_DEDUPLICATION_PROMPT = """You are an expert at identifying duplicate news coverage. Your task is to analyze a list of news articles and identify which ones are duplicates of the SAME story.

Two articles are DUPLICATES if they cover the EXACT SAME:
- Specific business announcement (same company, same investment amount, same location)
- Specific government policy or law (same legislation, same announcement)
- Specific study or report (same research, same findings, same organization)
- Specific event or incident (same date, same participants, same outcome)

Articles are NOT duplicates if they:
- Cover different companies or different investments (even if similar amounts)
- Cover different policies or different government announcements
- Cover different studies or different time periods of the same topic
- Cover related but separate events or decisions
- Are general industry analysis vs specific announcements

EXAMPLES:
- "TikTok invests R$55B in datacenter in Ceará" + "TikTok to build R$55B datacenter in Ceará" = DUPLICATE
- "Century invests R$150M in MG datacenter" + "Century announces R$150M datacenter in MG" = DUPLICATE
- "Century invests R$150M in MG" + "Google invests R$100M in SP" = NOT DUPLICATE
- "Government announces Policy X" + "Minister confirms Policy X will be launched" = DUPLICATE

INSTRUCTIONS:
Return a JSON array where each object has:
- All original fields (id, title, summary, source, pubDate)
- A new "duplicate" field set to "yes" or "no"

Process articles in order. An article is duplicate if ANY previous article covers the same story.

RESPOND WITH ONLY THE JSON ARRAY, NO OTHER TEXT."""

def deduplicate_by_summary(items: List[Dict], confidence_threshold: float = 0.7) -> List[Dict]:
    """
    Remove duplicate news articles using batch LLM-based semantic comparison.
    
    Args:
        items: List of news items, each containing 'summary', 'title', 'pubDate', etc.
        confidence_threshold: Not used in batch mode, kept for compatibility
    
    Returns:
        List of deduplicated news items
    """
    
    if not items or len(items) <= 1:
        return items
    
    print(f"Analyzing {len(items)} items for semantic duplicates (batch mode)...")
    
    # Initialize LLM with GPT-4o-mini for better cost efficiency
    llm = ChatOpenAI(
        temperature=0.0,
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        streaming=False,
        max_tokens=4096
        # Using gpt-4o-mini for better cost efficiency while maintaining good performance
    )
    
    # For larger datasets, we can still batch, but let's try processing all at once first
    if len(items) <= 25:  # Reduced from 50 to avoid token limits
        # Process all at once for better cross-article duplicate detection
        return process_single_batch(items, llm)
    else:
        # For very large datasets, use overlapping batches
        return process_overlapping_batches(items, llm)


def process_single_batch(items: List[Dict], llm) -> List[Dict]:
    """Process all items in a single batch for optimal duplicate detection."""
    
    print(f"Processing all {len(items)} articles in single batch...")
    
    # Create prompt template
    system_msg = SystemMessagePromptTemplate.from_template(BATCH_DEDUPLICATION_PROMPT)
    human_msg = HumanMessagePromptTemplate.from_template(
        """Analyze these articles for duplicates:

{articles_json}

Return JSON array with "duplicate" field added to each article:"""
    )
    prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])
    
    # Create chain
    chain = prompt | llm | StrOutputParser()
    
    # Prepare articles for LLM with key information
    articles_for_llm = []
    for i, item in enumerate(items):
        articles_for_llm.append({
            "id": i,
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "pubDate": item.get("pubDate", "")
        })
    
    try:
        # Get LLM response
        raw_result = chain.invoke({
            "articles_json": json.dumps(articles_for_llm, indent=2, ensure_ascii=False)
        })
        
        print(f"Raw LLM response (first 200 chars): {raw_result[:200]}")
        
        # Parse the response
        marked_articles = parse_batch_response(raw_result)
        
        if marked_articles is None:
            print("Failed to parse LLM response, keeping all articles")
            return items
        
        # Extract non-duplicate items
        deduplicated = []
        duplicates_found = 0
        
        for marked_article in marked_articles:
            article_id = marked_article.get("id")
            is_duplicate = marked_article.get("duplicate", "no").lower() == "yes"
            
            if not is_duplicate and article_id is not None and article_id < len(items):
                deduplicated.append(items[article_id])
            elif is_duplicate:
                duplicates_found += 1
                title = marked_article.get('title', items[article_id].get('title', 'Unknown') if article_id < len(items) else 'Unknown')
                print(f"  Article {article_id} marked as duplicate: '{title[:80]}...'")
        
        print(f"Single batch result: {len(items)} -> {len(deduplicated)} items ({duplicates_found} duplicates found)")
        return deduplicated
        
    except Exception as e:
        print(f"Error in single batch deduplication: {e}")
        print("Falling back to keeping all articles")
        return items


def process_overlapping_batches(items: List[Dict], llm) -> List[Dict]:
    """Process items in overlapping batches to catch cross-batch duplicates."""
    
    batch_size = 15  # Smaller batch size to avoid token limits
    overlap = 3  # Smaller overlap
    all_deduplicated = []
    processed_indices = set()
    
    for batch_start in range(0, len(items), batch_size - overlap):
        batch_end = min(batch_start + batch_size, len(items))
        batch_items = items[batch_start:batch_end]
        
        print(f"Processing overlapping batch: articles {batch_start+1}-{batch_end}")
        
        # Create the batch indices for tracking
        batch_indices = list(range(batch_start, batch_end))
        
        # Process this batch with process_single_batch logic inline
        # Create prompt template
        system_msg = SystemMessagePromptTemplate.from_template(BATCH_DEDUPLICATION_PROMPT)
        human_msg = HumanMessagePromptTemplate.from_template(
            """Analyze these articles for duplicates:

{articles_json}

Return JSON array with "duplicate" field added to each article:"""
        )
        prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])
        
        # Create chain
        chain = prompt | llm | StrOutputParser()
        
        # Prepare articles for LLM with key information
        articles_for_llm = []
        for i, item in enumerate(batch_items):
            articles_for_llm.append({
                "id": i,
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "pubDate": item.get("pubDate", "")
            })
        
        try:
            # Get LLM response
            raw_result = chain.invoke({
                "articles_json": json.dumps(articles_for_llm, indent=2, ensure_ascii=False)
            })
            
            # Parse the response
            marked_articles = parse_batch_response(raw_result)
            
            if marked_articles is None:
                print(f"Failed to parse LLM response for batch, keeping all articles in this batch")
                # Add items we haven't processed yet
                for i, item in enumerate(batch_items):
                    original_idx = batch_indices[i]
                    if original_idx not in processed_indices:
                        all_deduplicated.append(item)
                        processed_indices.add(original_idx)
                continue
            
            # Extract non-duplicate items from this batch
            duplicates_found = 0
            
            for marked_article in marked_articles:
                local_id = marked_article.get("id")
                is_duplicate = marked_article.get("duplicate", "no").lower() == "yes"
                
                if local_id is not None and local_id < len(batch_items):
                    original_idx = batch_indices[local_id]
                    
                    if not is_duplicate and original_idx not in processed_indices:
                        all_deduplicated.append(batch_items[local_id])
                        processed_indices.add(original_idx)
                    elif is_duplicate:
                        duplicates_found += 1
                        title = marked_article.get('title', batch_items[local_id].get('title', 'Unknown'))
                        print(f"  Article {original_idx} marked as duplicate: '{title[:60]}...'")
                        processed_indices.add(original_idx)  # Mark as processed even if duplicate
            
            print(f"Batch {batch_start+1}-{batch_end}: processed {len(batch_items)} articles, {duplicates_found} duplicates found")
            
        except Exception as e:
            print(f"Error in batch {batch_start+1}-{batch_end} deduplication: {e}")
            # Add items we haven't processed yet
            for i, item in enumerate(batch_items):
                original_idx = batch_indices[i]
                if original_idx not in processed_indices:
                    all_deduplicated.append(item)
                    processed_indices.add(original_idx)
    
    print(f"Final overlapping batch result: {len(items)} -> {len(all_deduplicated)} items")
    return all_deduplicated


def parse_batch_response(raw_response: str) -> List[Dict]:
    """
    Parse the LLM batch response and extract the marked articles.
    Enhanced with better error handling and JSON extraction.
    """
    # Clean the response
    cleaned_response = raw_response.strip()
    
    # Try direct JSON parsing first (expecting array)
    try:
        result = json.loads(cleaned_response)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "articles" in result:
            return result["articles"]
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    if '```json' in cleaned_response or '```' in cleaned_response:
        try:
            start = cleaned_response.find('```')
            if cleaned_response[start:start+7] == '```json':
                start += 7
            else:
                start += 3
            end = cleaned_response.find('```', start)
            if end > start:
                json_str = cleaned_response[start:end].strip()
                result = json.loads(json_str)
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and "articles" in result:
                    return result["articles"]
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON array within the response (most likely)
    try:
        start = cleaned_response.find('[')
        end = cleaned_response.rfind(']') + 1
        
        if start >= 0 and end > start:
            json_str = cleaned_response[start:end]
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON object within the response (fallback)
    try:
        start = cleaned_response.find('{')
        if start >= 0:
            # Find matching closing brace
            brace_count = 0
            end = start
            for i, char in enumerate(cleaned_response[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if end > start:
                json_str = cleaned_response[start:end]
                result = json.loads(json_str)
                if isinstance(result, dict) and "articles" in result:
                    return result["articles"]
    except json.JSONDecodeError:
        pass
    
    print("Could not parse LLM response as JSON. Raw response:")
    print(cleaned_response[:500] + "..." if len(cleaned_response) > 500 else cleaned_response)
    return None


def select_best_from_group(group_items: List[Dict]) -> int:
    """
    Select the best item from a group of duplicates based on:
    1. Most recent publication date
    2. Longest summary (most comprehensive coverage)
    3. Title length as tiebreaker
    
    Returns:
        Index of the best item in the group
    """
    
    def get_date_score(item):
        """Convert date to timestamp for comparison (more recent = higher score)"""
        try:
            pub_date = item.get('pubDate', '')
            if isinstance(pub_date, str):
                # Try to parse the formatted date string
                dt = parser.parse(pub_date)
            else:
                dt = pub_date
            return dt.timestamp()
        except:
            return 0
    
    def get_summary_score(item):
        """Return summary length"""
        return len(item.get('summary', ''))
    
    def get_title_score(item):
        """Return title length as tiebreaker"""
        return len(item.get('title', ''))
    
    best_idx = 0
    best_date_score = get_date_score(group_items[0])
    best_summary_score = get_summary_score(group_items[0])
    best_title_score = get_title_score(group_items[0])
    
    for i, item in enumerate(group_items[1:], 1):
        date_score = get_date_score(item)
        summary_score = get_summary_score(item)
        title_score = get_title_score(item)
        
        # Prioritize by: 1) Date, 2) Summary length, 3) Title length
        if (date_score > best_date_score or 
            (date_score == best_date_score and summary_score > best_summary_score) or
            (date_score == best_date_score and summary_score == best_summary_score and title_score > best_title_score)):
            
            best_idx = i
            best_date_score = date_score
            best_summary_score = summary_score
            best_title_score = title_score
    
    return best_idx


if __name__ == "__main__":
    print("=== Testing Deduplication with Real Data ===")
    
    # Load actual clippings.json for testing
    try:
        with open("output/clippings.json", "r", encoding="utf-8") as f:
            real_items = json.load(f)
        
        print(f"Loaded {len(real_items)} real articles from clippings.json")
        
        # Show some examples of obvious duplicates for verification
        print("\n=== Sample of articles (to spot obvious duplicates) ===")
        for i, item in enumerate(real_items[:15]):
            print(f"{i+1:2d}: {item['title'][:80]}...")
        
        print("\n=== Running deduplication ===")
        deduplicated = deduplicate_by_summary(real_items)
        
        print(f"\n=== Results ===")
        print(f"Original articles: {len(real_items)}")
        print(f"After deduplication: {len(deduplicated)}")
        print(f"Duplicates removed: {len(real_items) - len(deduplicated)}")
        
        # Show remaining articles
        print(f"\n=== Remaining articles after deduplication ===")
        for i, item in enumerate(deduplicated):
            print(f"{i+1:2d}: {item['title']}")
            
    except FileNotFoundError:
        print("clippings.json not found, using sample data instead")
        
        # Fallback to sample data
        sample_items = [
            {
                "title": "TikTok construirá datacenter de R$ 55 bilhões no interior do Ceará",
                "source": "Canal Solar",
                "url": "https://example.com/1",
                "pubDate": "06 Jun",
                "summary": "O TikTok investirá R$ 55 bilhões na construção de um datacenter em Caucaia (CE), já com licença prévia aprovada; o projeto contará com o suporte da Casa dos Ventos para fornecimento de energia renovável.",
                "class": "relevant",
                "category": "clientes"
            },
            {
                "title": "TikTok to build R$55 billion data center in Ceará state",
                "source": "Canal Solar EN",
                "url": "https://example.com/2", 
                "pubDate": "06 Jun",
                "summary": "A TikTok anunciou um investimento de aproximadamente R$55 bilhões na construção de um mega data center em Caucaia (CE), já com licença de construção preliminar aprovada.",
                "class": "relevant",
                "category": "clientes"
            },
            {
                "title": "Century anuncia data center de R$ 150 milhões em MG para 2026",
                "source": "Mobile Time",
                "url": "https://example.com/3",
                "pubDate": "06 Jun",
                "summary": "A Century anunciou um investimento de R$ 150 milhões para a construção de um data center em Contagem, MG, com previsão de início das operações no primeiro trimestre de 2026.",
                "class": "relevant", 
                "category": "competidores"
            },
            {
                "title": "Empresa de tecnologia vai investir R$ 150 milhões em novo data center na Região Metropolitana de BH",
                "source": "Hoje em Dia",
                "url": "https://example.com/4",
                "pubDate": "06 Jun", 
                "summary": "A Century anunciou um investimento de R$ 150 milhões na construção de um novo data center em Contagem, na Região Metropolitana de Belo Horizonte, com operação prevista para o primeiro semestre de 2026.",
                "class": "relevant",
                "category": "competidores"
            },
            {
                "title": "NVIDIA unveils new AI chip for data centers",
                "source": "Hardware Today",
                "url": "https://example.com/5",
                "pubDate": "17 Jun", 
                "summary": "NVIDIA unveiled its latest AI processing chip designed for data center workloads with improved performance and energy efficiency. The new H200 chip offers 2x faster processing.",
                "class": "relevant",
                "category": "hardware"
            }
        ]
        
        print("=== Original sample items ===")
        for i, item in enumerate(sample_items):
            print(f"{i+1}: {item['title']}")
        
        deduplicated = deduplicate_by_summary(sample_items)
        
        print("\n=== After deduplication ===")
        for i, item in enumerate(deduplicated):
            print(f"{i+1}: {item['title']}")
    
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc() 