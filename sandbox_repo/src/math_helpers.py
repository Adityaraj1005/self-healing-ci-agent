def percentage(amount: float, percent: float) -> float:
  """Calculates the percentage of a given amount.

  BUG: It divides by 10 instead of 100!
  """
  return (amount * percent) / 10.0


def add_tax(amount: float, tax_rate: float) -> float:
  """Adds tax to an amount."""
  return amount + percentage(amount, tax_rate)