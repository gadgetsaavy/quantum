# /home/uber/Desktop/quantum/scripts/ArbitrageAgent.py
import networkx as nx
from web3 import Web3
import json
import time
import logging
import csv
import os
from decimal import Decimal
import pandas as pd
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from collections import deque
import numpy as np
import warnings

warnings.filterwarnings("ignore")

class ArbitrageAgent:
    def __init__(self, rpc_url, contract_address, private_key):
        # --- Basic Setup ---
        self.contract_address = contract_address
        self.rpc_url = rpc_url  # corrected to rpc_url
        self.private_key = private_key
        self.web3 = None  # Initialize web3 to None
        self.account = None  # Initialize account to None
        self.contract = None  # Initialize contract to None

        # --- Graph Setup ---
        self.arbitrage_graph = nx.DiGraph()

        # --- ML Setup ---
        self.agent = TradingAgent()
        self.scaler = StandardScaler()
        self.memory = deque(maxlen=1000)
        self.scaler_fitted = False  # Flag to track if scaler has been fitted

        # --- Logging ---
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # --- Initialize Web3 and Contract with Error Handling ---
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.account = self.web3.eth.account.from_key(self.private_key)

            # Load ABI
            with open("FlashArbitrage_ABI.json", 'r') as f:
                contract_abi = json.load(f)
            self.contract = self.web3.eth.contract(address=self.contract_address, abi=contract_abi)

            self.logger.info("Web3 connection and contract initialization successful.")
        except Exception as e:
            self.logger.error(f"Error initializing Web3 or contract: {str(e)}")
            raise  # Re-raise exception to prevent further execution if initialization fails

    def fetch_reserves(self):
        """
        Fetch token reserves from Uniswap/Sushiswap pools.
        Returns a dictionary of token pairs and their reserves.
        """
        try:
            token_pairs = self.contract.functions.getTokenPairs().call()
            reserves = {}
            for token0, token1 in token_pairs:
                try:
                    reserves[(token0, token1)] = self.contract.functions.getReserves(token0, token1).call()
                    self.logger.info(f"Fetched reserves for {token0} - {token1}")
                except Exception as e:
                    self.logger.error(f"Error fetching reserves for {token0} - {token1}: {str(e)}")
            return reserves
        except Exception as e:
            self.logger.error(f"Error fetching reserves: {str(e)}")
            return {}

    def build_graph(self):
        """
        Build the arbitrage graph using token pairs and their reserves.
        Uses log prices to prevent numerical overflow.
        """
        try:
            self.arbitrage_graph.clear()
            reserves = self.fetch_reserves()
            for (token0, token1), (reserve0, reserve1, _) in reserves.items():
                log_price = Decimal(reserve1) / Decimal(reserve0)
                log_price = log_price.ln()
                self.arbitrage_graph.add_edge(token0, token1, weight=-float(log_price))
                self.arbitrage_graph.add_edge(token1, token0, weight=float(log_price))
            self.logger.info("Graph built successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error building graph: {str(e)}")
            return False

    def detect_arbitrage(self):
        """
        Detect arbitrage opportunities using Bellman-Ford algorithm.
        Returns list of negative cycles.
        """
        try:
            negative_cycles = []
            for node in self.arbitrage_graph.nodes:
                try:
                    cycle = nx.find_negative_cycle(self.arbitrage_graph, source=node)
                    if cycle:
                        negative_cycles.append(cycle)
                except nx.NetworkXNoCycle:
                    continue
            return negative_cycles
        except Exception as e:
            self.logger.error(f"Error detecting arbitrage: {str(e)}")
            return []

    def get_current_state(self, path):
        """Get current state for ML agent"""
        # Features:
        # 1. Available liquidity
        # 2. Current gas prices
        # 3. Historical price impact
        # 4. Path complexity
        try:
            state = {
                'liquidity': self.get_path_liquidity(path),
                'gas_price': self.web3.eth.gasPrice,
                'price_impact': self.calculate_price_impact(path),
                'path_length': len(path)
            }
            return state
        except Exception as e:
            self.logger.error(f"Error getting current state: {str(e)}")
            return None

    def get_path_liquidity(self, path):
        """Calculate available liquidity for the path"""
        try:
            total_liquidity = 0
            for i in range(len(path) - 1):
                pair = (path[i], path[i + 1])
                if pair in self.arbitrage_graph.edges():
                    total_liquidity += self.arbitrage_graph.edges[pair]['weight']  # Corrected to 'weight' instead of 'liquidity'
            return total_liquidity
        except Exception as e:
            self.logger.error(f"Error calculating path liquidity: {str(e)}")
            return 0

    def calculate_price_impact(self, path):
        """Calculate expected price impact for the path"""
        try:
            impact = 0
            for i in range(len(path) - 1):
                pair = (path[i], path[i + 1])
                if pair in self.arbitrage_graph.edges():
                    impact += self.arbitrage_graph.edges[pair]['weight']
            return impact
        except Exception as e:
            self.logger.error(f"Error calculating price impact: {str(e)}")
            return 0

    def execute_arbitrage(self, path):
        """Execute arbitrage with ML-optimized amount"""
        try:
            # Get current state
            state = self.get_current_state(path)
            if state is None:
                self.logger.warning("Could not get current state. Aborting arbitrage.")
                return None

            # Get optimal trade amount from ML agent
            amount = self.agent.get_optimal_trade_amount(state)
            if amount is None:
                self.logger.warning("Could not get optimal trade amount. Aborting arbitrage.")
                return None

            # Execute transaction
            tx = self.contract.functions.executeArbitrage(
                path,
                int(amount)  # Amount has to be an integer
            ).build_transaction({
                'from': self.account.address,
                'gas': 500000,
                'gasPrice': self.web3.to_wei('30', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

            # Log trade data for ML training
            self.log_trade_data(path, amount, tx_hash)

            return tx_hash
        except Exception as e:
            self.logger.error(f"Error executing arbitrage: {str(e)}")
            return None

    def log_trade_data(self, path, amount, tx_hash):
        """Log trade data for ML training"""
        try:
            with open("arbitrage_logs.csv", "a", newline='') as f:
                writer = csv.writer(f)
                if f.tell() == 0:
                    writer.writerow(["path", "amount", "tx_hash", "gas_used", "profit"])
                writer.writerow([path, amount, tx_hash, 0, 0])
        except Exception as e:
            self.logger.error(f"Error logging trade data: {str(e)}")

    def train_model(self, epochs=10):
        """Train the model with historical data"""
        try:
            # Load data from CSV
            df = pd.read_csv("arbitrage_logs.csv")

            # Check if the DataFrame is empty or has no data
            if df.empty:
                self.logger.warning("No training data available in arbitrage_logs.csv.")
                return

            # Prepare training data
            states = []
            targets = []

            for index, row in df.iterrows():
                path = eval(row['path'])  # Convert string representation of list to actual list
                amount = row['amount']
                state = self.get_current_state(path)

                if state is None:
                    self.logger.warning(f"Skipping training data due to None state for path: {path}")
                    continue

                states.append(list(state.values()))
                targets.append(amount)

            if not states:
                self.logger.warning("No valid training data found after processing CSV.")
                return

            # Fit scaler only if it hasn't been fitted before
            if not self.scaler_fitted:
                self.scaler.fit(states)
                self.scaler_fitted = True
                self.logger.info("Scaler fitted with training data.")
            else:
                self.logger.info("Scaler already fitted, using existing scaler.")

            # Train the model
            self.agent.train(states, targets)
            self.logger.info("Model training complete.")

        except FileNotFoundError:
            self.logger.warning("The file 'arbitrage_logs.csv' was not found. Skipping model training.")
        except Exception as e:
            self.logger.error(f"Error during model training: {str(e)}")


class TradingAgent:
    def __init__(self):
        # Initialize ML model
        self.model = self.build_model()
        self.scaler = StandardScaler()
        self.memory = deque(maxlen=1000)

    def build_model(self):
        model = Sequential()
        model.add(Dense(64, input_dim=4, activation='relu'))
        model.add(Dense(32, activation='relu'))
        model.add(Dense(1, activation='linear'))
        model.compile(optimizer='adam', loss='mse')
        return model

    def get_optimal_trade_amount(self, state):
        """Get optimal trade amount based on the given state."""
        try:
            # Ensure the state is not None and has the correct keys
            if state is None:
                print("Warning: Received None state in get_optimal_trade_amount.")
                return None  # Or a default value if appropriate

            # Convert state to a list of values
            state_values = list(state.values())

            # Ensure the list has the expected length
            if len(state_values) != 4:
                print(f"Warning: Unexpected state length ({len(state_values)}). Expected 4.")
                return None  # Or a default value

            # Reshape the state values into a 2D array before scaling
            state_array = np.array(state_values).reshape(1, -1)

            # Transform the state using the scaler
            state_scaled = self.scaler.transform(state_array)

            # Make a prediction using the model
            prediction = self.model.predict(state_scaled)

            # Return the predicted trade amount (scalar value)
            return prediction[0][0]

        except Exception as e:
            print(f"Error in get_optimal_trade_amount: {e}")
            return None  # It's good to return None if something goes wrong

    def train(self, states, targets):
        try:
            # Check if there's any states data
            if not states:
                print("Warning: No states data provided for training.")
                return

            # Convert lists to numpy arrays
            states = np.array(states)
            targets = np.array(targets)

            # Check for mismatched dimensions
            if states.shape[0] != targets.shape[0]:
                print(f"Dimension mismatch: states shape {states.shape}, targets shape {targets.shape}")
                return

            # Scale the states
            states_scaled = self.scaler.transform(states)

            # Train the model
            self.model.fit(states_scaled, targets, epochs=10, verbose=0)

            print("Model training completed successfully.")

        except Exception as e:
            print(f"Error during model training: {e}")
