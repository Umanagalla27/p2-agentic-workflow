"""LeetCode 121: Best Time to Buy and Sell Stock (Easy)

You are given an array prices where prices[i] is the price of a given stock on the ith day.
You want to maximize your profit by choosing a single day to buy one stock and choosing
a different day in the future to sell that stock.

Return the maximum profit you can achieve from this transaction. If you cannot achieve
any profit, return 0.

Time Complexity: O(N) single-pass.
Space Complexity: O(1) constant extra space.
"""


def max_profit(prices: list[int]) -> int:
    min_price = float("inf")
    max_p = 0

    for price in prices:
        if price < min_price:
            min_price = price
        elif price - min_price > max_p:
            max_p = price - min_price

    return max_p


if __name__ == "__main__":
    test_cases = [
        [7, 1, 5, 3, 6, 4],  # Expected: 5 (buy at 1, sell at 6)
        [7, 6, 4, 3, 1],  # Expected: 0
    ]
    for prices in test_cases:
        print(f"Prices: {prices} -> Max Profit: {max_profit(prices)}")
