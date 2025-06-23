from services.classifier import classify_items

def test_classify_items_empty():
    assert classify_items([]) == [] 