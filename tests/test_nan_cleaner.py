import math
import pytest
from utils.helpers import clean_nan_values

def test_clean_nan_values_simple():
    assert clean_nan_values(1.0) == 1.0
    assert clean_nan_values(float('nan')) is None
    assert clean_nan_values(float('inf')) is None
    assert clean_nan_values(float('-inf')) is None
    assert clean_nan_values("string") == "string"
    assert clean_nan_values(None) is None

def test_clean_nan_values_nested():
    data = {
        "a": float('nan'),
        "b": [1.0, float('inf'), {"c": float('-inf')}],
        "d": (2.0, float('nan'))
    }
    expected = {
        "a": None,
        "b": [1.0, None, {"c": None}],
        "d": (2.0, None)
    }
    assert clean_nan_values(data) == expected
