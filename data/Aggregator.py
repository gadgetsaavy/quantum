import requests
import numpy as np
import json
import math
from typing import List, Tuple, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DEXAggregator:
    def __init__(self, aggregator_url: str):
        self.aggregator_url = aggregator_url
        self.logger = logger

    def fetch_data(self) -> Dict:
        """Fetch data from the aggregator URL with improved error handling."""
        try:
            response = requests.get(self.aggregator_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch data: {e}")
            raise ValueError(f"Failed to fetch data: {e}")

    def bellman_ford_arbitrage(self, prices: List[float], liquidity: List[float]) -> Tuple[List[float], List[int], List[List[int]]]:
        """
        Detect arbitrage opportunities using Bellman-Ford algorithm with logarithmic transformation.
        
        Args:
            prices: List of token prices
            liquidity: List of token liquidity values
            
        Returns:
            Tuple of (distance array, predecessor array, arbitrage cycles)
        """
        num_tokens = len(prices)
        # Initialize distance array with negative infinity
        distance = [-float('inf')] * num_tokens
        # Initialize predecessor array for path reconstruction
        predecessor = [-1] * num_tokens
        # Initialize distance to starting node as 0
        distance[0] = 0
        
        # Store arbitrage cycles
        arbitrage_cycles = []
        
        # Relax edges |V|-1 times
        for _ in range(num_tokens - 1):
            for i in range(num_tokens):
                for j in range(num_tokens):
                    if i != j:
                        # Use logarithmic transformation for numerical stability
                        log_profit = math.log(prices[j] * liquidity[i] / (prices[i] * liquidity[i]))
                        if distance[i] + log_profit > distance[j]:
                            distance[j] = distance[i] + log_profit
                            predecessor[j] = i
        
        # Check for negative cycles (arbitrage opportunities)
        for i in range(num_tokens):
            for j in range(num_tokens):
                if i != j:
                    log_profit = math.log(prices[j] * liquidity[i] / (prices[i] * liquidity[i]))
                    if distance[i] + log_profit > distance[j]:
                        # Found an arbitrage opportunity
                        cycle = self._reconstruct_cycle(predecessor, i, j)
                        if cycle not in arbitrage_cycles:
                            arbitrage_cycles.append(cycle)
                            self.logger.info(f"Arbitrage opportunity detected: {cycle}")
        
        return distance, predecessor, arbitrage_cycles

    def _reconstruct_cycle(self, predecessor: List[int], start: int, end: int) -> List[int]:
        """Reconstruct cycle from predecessor array."""
        cycle = []
        current = start
        while current != -1:
            cycle.append(current)
            if current == end:
                break
            current = predecessor[current]
        return cycle[::-1]

    def calculate_optimal_loan_size(self, prices: List[float], liquidity: List[float], 
                                  distance: List[float], cycles: List[List[int]]) -> List[Tuple[int, float]]:
        """
        Calculate optimal loan sizes for detected arbitrage opportunities.
        
        Args:
            prices: List of token prices
            liquidity: List of token liquidity values
            distance: Distance array from Bellman-Ford
            cycles: List of detected arbitrage cycles
            
        Returns:
            List of tuples containing (token_index, optimal_loan_size)
        """
        optimal_loans = []
        
        for cycle in cycles:
            # Calculate maximum possible loan size based on liquidity constraints
            max_loan = float('inf')
            for token_idx in cycle:
                token_liquidity = liquidity[token_idx]
                # Consider 90% of available liquidity to account for slippage
                max_loan = min(max_loan, 0.9 * token_liquidity)
            
            # Calculate expected profit percentage
            profit_percentage = math.exp(distance[cycle[0]]) - 1
            
            if profit_percentage > 0.01:  # Minimum 1% profit threshold
                optimal_loans.append((cycle[0], max_loan))
                self.logger.info(f"Optimal loan opportunity: Token {cycle[0]}, Amount: {max_loan:.2f}, "
                               f"Expected Profit: {profit_percentage:.2%}")
        
        return optimal_loans

    def find_profitable_arbitrage(self, min_profit_threshold: float = 0.01) -> List[Tuple[int, float]]:
        """Find profitable arbitrage opportunities with visualization."""
        try:
            data = self.fetch_data()
            prices = [pair['price'] for pair in data['pairs']]
            liquidity = [pair['liquidity'] for pair in data['pairs']]
            
            # Run Bellman-Ford algorithm
            distance, predecessor, cycles = self.bellman_ford_arbitrage(prices, liquidity)
            
            # Calculate optimal loan sizes
            optimal_loans = self.calculate_optimal_loan_size(prices, liquidity, distance, cycles)
            
            # Visualize arbitrage opportunities
            if cycles:
                self._visualize_arbitrage(prices, liquidity, cycles)
            
            return optimal_loans
            
        except Exception as e:
            self.logger.error(f"Error finding arbitrage opportunities: {e}")
            raise ValueError(f"Error finding arbitrage opportunities: {e}")

    def _visualize_arbitrage(self, prices: List[float], liquidity: List[float], cycles: List[List[int]]):
        """Create a visualization of arbitrage opportunities using Mermaid."""
        # Create Mermaid diagram code
        diagram_code = "flowchart LR\n"
        
        # Add nodes
        for i, price in enumerate(prices):
            diagram_code += f"T{i}[Token {i}: ${price:.2f}]\n"
        
        # Add edges with weights
        for cycle in cycles:
            for i in range(len(cycle)):
                j = (i + 1) % len(cycle)
                token_i = cycle[i]
                token_j = cycle[j]
                # Calculate edge weight (profit percentage)
                profit = (prices[token_j] * liquidity[token_i] - prices[token_i] * liquidity[token_i]) / (prices[token_i] * liquidity[token_i]) * 100
                diagram_code += f"T{token_i} --> |{profit:.2f}%| T{token_j}\n"
        
        # Log the diagram code
        self.logger.info("Arbitrage opportunity visualization:")
        self.logger.info(diagram_code)