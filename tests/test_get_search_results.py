import pytest
from utils.get_search_results import get_search_results

def test_get_search_results_returns_list():
    results = get_search_results("odata", days=1, country="us")
    assert isinstance(results, list) 