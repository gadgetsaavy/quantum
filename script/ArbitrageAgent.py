import os
from web3 import Web3
import json

class ArbitrageAgent:
    def __init__(self, contract_address, provider_url):
        self.web3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract = self.web3.eth.contract(address=contract_address, abi=self.load_contract_abi())
        self.account = self.web3.eth.account.privateKeyToAccount(os.getenv("PRIVATE_KEY"))

    def load_contract_abi(self):
        try:
            with open('data/FlashArbitrageExecutor.sol') as f:
                return json.load(f)['abi']
        except FileNotFoundError:
            raise ValueError("ABI file not found")
        except json.JSONDecodeError:
            raise ValueError("Error decoding ABI file")

    def execute_arbitrage(self, amount, path, min_amount_out):
        nonce = self.web3.eth.getTransactionCount(self.account.address)
        tx = self.contract.functions.initiateArbitrage(amount, path, min_amount_out).buildTransaction({
            'chainId': 1,
            'gas': 2000000,
            'gasPrice': self.web3.toWei('50', 'gwei'),
            'nonce': nonce,
        })
        signed_tx = self.web3.eth.account.signTransaction(tx, private_key=os.getenv("PRIVATE_KEY"))
        try:
            tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
            return tx_hash
        except Exception as e:
            raise ValueError(f"Transaction failed: {e}")

if __name__ == "__main__":
    contract_address = "0xYourContractAddress"
    provider_url = "https://your.ethereum.node:8545"
    private_key = "YOUR_PRIVATE_KEY"
    
    CONFIG = initialize(contract_address, provider_url, private_key)
    agent = ArbitrageAgent(CONFIG["contract_address"], CONFIG["provider_url"])
    
    amount = ...  # Replace with the amount to borrow using the flash loan
    path = [...]  # Replace with the token swap path, e.g. [TOKEN_A_ADDRESS, TOKEN_B_ADDRESS]
    min_amount_out = ...  # Replace with minimum acceptable output amount after the token swap

    try:
        tx_hash = agent.execute_arbitrage(amount, path, min_amount_out)
        print(f'Arbitrage executed, transaction hash: {tx_hash.hex()}')
    except ValueError as e:
        print(e)
