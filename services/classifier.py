import os
import json
from datetime import datetime, timezone
from typing import List, Dict

from dotenv import load_dotenv, find_dotenv
from langchain.prompts.chat import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Load environment exactly as in the notebook
_ = load_dotenv(find_dotenv())

# Load the system prompt template from file
with open("configs/classification_prompt.txt", "r", encoding="utf-8") as f:
    CLASSIFICATION_PROMPT_TEMPLATE = f.read().strip()

def add_classifications(items):
    system_msg = SystemMessagePromptTemplate.from_template(CLASSIFICATION_PROMPT_TEMPLATE)
    human_msg = HumanMessagePromptTemplate.from_template("News Piece Title: {title}\nURL: {url}")
    prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])

    # Initialize exactly as in the notebook
    llm = ChatOpenAI(
        temperature=0.0,
        model_name="gpt-4o-mini"
    )
    parser = StrOutputParser() | json.loads
    chain = prompt | llm | parser

    for item in items:
        result = chain.invoke({"title": item.get("title", ""), "url": item.get("url", "")})
        label = result.get("label", "irrelevant").lower()
        category = result.get("category", "") if label == "relevant" else ""
        item["class"] = label
        item["category"] = category

    return items


def drop_irrelevant(items: List[Dict]) -> List[Dict]:
    """
    Filter the list of items to include only those classified as "relevant".
    """
    return [item for item in items if item.get("class", "").lower() == "relevant"]


if __name__ == "__main__":
    # Sample test items
    test_items = [
        {
            "title": "Bitfarms forçada a interromper mineração de criptomoedas em seu data center na Argentina",
            "source": "Data Center Dynamics",
            "url": "https://www.datacenterdynamics.com/br/not%C3%ADcias/bitfarms-for%C3%A7ada-a-interromper-minera%C3%A7%C3%A3o-de-criptomoedas-em-seu-data-center-na-argentina/",
            "pubDate": datetime.now(timezone.utc),
        },
        {
            "title": "Equinix investe em datacenters no Rio Grande do Norte",
            "source": "Tech News Brasil",
            "url": "https://example.com/equinix-rio-grande-do-norte",
            "pubDate": datetime.now(timezone.utc),
        },
    ]

    # Run classification
    annotated_items = add_classifications(test_items)

    # Display results
    print("=== Classification Results ===")
    for idx, item in enumerate(annotated_items, start=1):
        print(f"Item {idx}:")
        print(f"  Title: {item['title']}")
        print(f"  URL: {item['url']}")
        print(f"  Class: {item['class']}")
        print(f"  Category: {item['category']}\n")
