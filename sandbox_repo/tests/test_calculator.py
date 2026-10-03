import pytest
from src.calculator import calculate_discounted_total


def test_calculate_discounted_total():
  # 100 with a 20% discount should equal 80.0
  # Because of the bug (dividing by 10), discount will be 200, returning -100!
  result = calculate_discounted_total(100.0, 20.0)
  assert result == 80.0, f"Expected 80.0, but got {result}"