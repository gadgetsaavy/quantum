import requests
import numpy as np
import json

class DEXAggregator:
    def __init__(self, aggregator_url):
        self.aggregator_url = aggregator_url

    def fetch_data(self):
        try:
            response = requests.get(self.aggregator_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch data: {e}")
        return response.json()

    def bellman_ford_arbitrage(self, prices, liquidity):
        num_tokens = len(prices)
        # Create a distance array for profit calculation
        distance = np.zeros(num_tokens)  # Start with zero profit
        path = [-1] * num_tokens  # Initialize path tracking

        for _ in range(num_tokens - 1):  # Relax edges
            for i in range(num_tokens):
                for j in range(num_tokens):
                    if i != j:
                        # Calculate profit using constant product formula
                        trade_amount = liquidity[i]
                        profit = prices[j] * trade_amount - prices[i] * trade_amount
                        if profit > 0 and distance[i] + profit > distance[j]:
                            distance[j] = distance[i] + profit
                            path[j] = i

        # Check for arbitrage opportunity
        for i in range(num_tokens):
            for j in range(num_tokens):
                if i != j:
                    trade_amount = liquidity[i]
                    if distance[i] + (prices[j] * trade_amount - prices[i] * trade_amount) > distance[j]:
                        raise ValueError("Arbitrage opportunity detected!")

        return distance, path

    def calculate_optimal_loan_size(self, prices, liquidity, distance):
        # Constant product formula to determine optimal loan size
        optimal_sizes = []
        for i in range(len(prices)):
            if distance[i] > 0:  # Only consider profitable paths
                optimal_size = liquidity[i] * distance[i] / (prices[i] + 1)  # Example formula
                optimal_sizes.append((i, optimal_size))
        return optimal_sizes

    def find_profitable_arbitrage(self, min_profit_threshold):
        data = self.fetch_data()
        prices = [pair['price'] for pair in data['pairs']]  # Extract prices
        liquidity = [pair['liquidity'] for pair in data['pairs']]  # Extract liquidity

        # Run Bellman-Ford for arbitrage detection
        distance, path = self.bellman_ford_arbitrage(prices, liquidity)

        optimal_sizes = self.calculate_optimal_loan_size(prices, liquidity, distance)
        
        return optimal_sizes

if __name__ == "__main__":
    aggregator = DEXAggregator("https://your-aggregator-url.com")
    optimal_loans = aggregator.find_profitable_arbitrage(min_profit_threshold=0.01)
    
    print(json.dumps(optimal_loans, indent=2))
