# /home/uber/Desktop/quantum/data/Monitoring.py
import time
import os
from web3 import Web3
from scripts.ArbitrageAgent import ArbitrageAgent  # Corrected import statement

def initialize(contract_address, provider_url, private_key):
    """
    Initializes the configuration dictionary.
    """
    config = {
        "contract_address": contract_address,
        "provider_url": provider_url,
        "private_key": private_key
    }
    return config

def monitor_and_execute():
    contract_address = os.getenv("CONTRACT_ADDRESS")
    provider_url = os.getenv("PROVIDER_URL")
    private_key = os.getenv("PRIVATE_KEY")

    CONFIG = initialize(contract_address, provider_url, private_key)
    agent = ArbitrageAgent(CONFIG["contract_address"], CONFIG["provider_url"], private_key)  # Modified instantiation

    while True:
        # Build graph and detect arbitrage opportunities
        if agent.build_graph():
            arbitrage_paths = agent.detect_arbitrage()
            if arbitrage_paths:
                for path in arbitrage_paths:
                    print(f"⚡ Profitable Path Found: {path}")
                    try:
                        tx_hash = agent.execute_arbitrage(path)
                        if tx_hash:
                            print(f'Arbitrage executed, transaction hash: {tx_hash.hex()}')
                    except ValueError as e:
                        print(e)
                    time.sleep(10)  # Adjust the sleep time based on your monitoring needs
        time.sleep(60) # check again after a minute

if __name__ == "__main__":
    monitor_and_execute()
