import os
from web3 import Web3
import json
from dotenv import load_dotenv
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArbitrageAgent:
    def __init__(self, contract_address: str, provider_url: str):
        self.web3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract = self.web3.eth.contract(
            address=contract_address, 
            abi=self.load_contract_abi()
        )
        self.account = self.web3.eth.account.privateKeyToAccount(os.getenv("PRIVATE_KEY"))
        # Configure gas price strategy
        self.web3.eth.set_gas_price_strategy(self.dynamic_gas_price_strategy)

    def load_contract_abi(self) -> List[Dict]:
        """Load contract ABI from JSON file."""
        try:
            with open('data/FlashArbitrageExecutor_abi.json') as f:
                abi_data = json.load(f)
                return abi_data['abi']
        except FileNotFoundError:
            logger.error("ABI file not found")
            raise ValueError("ABI file not found")
        except json.JSONDecodeError:
            logger.error("Error decoding ABI file")
            raise ValueError("Error decoding ABI file")

    def dynamic_gas_price_strategy(self, web3, transaction_params=None) -> int:
        """
        Dynamic gas price strategy considering EIP-1559 parameters.
        
        Returns:
            int: Gas price in wei
        """
        # Get fee history for last 4 blocks
        fee_history = self.web3.eth.fee_history(
            4,  # Number of blocks to sample
            "latest",
            [25, 50, 75]  # Percentiles for priority fees
        )

        # Calculate average base fee
        base_fees = fee_history["baseFeePerGas"]
        avg_base_fee = sum(base_fees) // len(base_fees)

        # Calculate average priority fee (using 50th percentile)
        priority_fees = fee_history["reward"][0]
        avg_priority_fee = priority_fees[1]  # 50th percentile

        # Calculate total fee with safety margin
        total_fee = avg_base_fee + avg_priority_fee * 1.2  # 20% safety margin
        
        logger.info(f"Gas price calculation:")
        logger.info(f"- Average base fee: {avg_base_fee}")
        logger.info(f"- Average priority fee: {avg_priority_fee}")
        logger.info(f"- Total fee: {total_fee}")

        return total_fee

    def execute_arbitrage(self, amount: float, path: List[str], min_amount_out: float) -> str:
        """Execute arbitrage transaction with confirmation."""
        nonce = self.web3.eth.getTransactionCount(self.account.address)
        
        # Build transaction with EIP-1559 parameters
        tx = self.contract.functions.initiateArbitrage(
            amount, path, min_amount_out
        ).buildTransaction({
            'chainId': 1,
            'gas': 2000000,
            'nonce': nonce,
            'maxFeePerGas': self.web3.eth.generate_gas_price(),
            'maxPriorityFeePerGas': self.web3.to_wei(2, 'gwei'),
            'from': self.account.address
        })

        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=os.getenv("PRIVATE_KEY")
        )

        try:
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f'Transaction sent: {tx_hash.hex()}')
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            gas_used = receipt.gasUsed
            effective_gas_price = receipt.effectiveGasPrice
            
            logger.info(f'Transaction confirmed:')
            logger.info(f'- Gas used: {gas_used}')
            logger.info(f'- Effective gas price: {effective_gas_price}')
            
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise ValueError(f"Transaction failed: {e}")

    def predict_revenue(self, simulation_results: List[Dict]) -> float:
        """Calculate predicted revenue from simulation results."""
        total_revenue = sum(result['profit'] for result in simulation_results)
        logger.info(f'Predicted Revenue: {total_revenue}')
        return total_revenue