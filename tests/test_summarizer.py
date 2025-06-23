from services.summarizer import summarize_items

def test_summarize_items_empty():
    assert summarize_items([]) == [] 