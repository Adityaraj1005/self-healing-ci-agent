from src.math_helpers import percentage


def calculate_discounted_total(price: float, discount_percent: float) -> float:
  """Applies a discount to a price and returns the final payable total.

  Example: price = 100.0, discount_percent = 20.0 -> discount is 20.0, total is 80.0
  """
  discount_amount = percentage(price, discount_percent)
  final_total = price - discount_amount
  return final_total