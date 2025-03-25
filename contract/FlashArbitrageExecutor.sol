// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0; // Specify the Solidity version

// Interface for the Flash Loan Provider which allows borrowing without collateral
interface IFlashLoanProvider {
    // Function to request a flash loan
    function flashLoan(
        uint256 amount, // The amount of tokens to borrow
        address recipient, // The address to receive the borrowed tokens
        bytes calldata data // Extra data for the loan operation
    ) external; // Makes the function callable externally
}

// Interface for the DEX Router used to perform token swaps
interface IDEXRouter {
    // Function to swap an exact amount of input tokens for output tokens
    function swapExactTokensForTokens(
        uint amountIn, // Amount of input tokens to swap
        uint amountOutMin, // Minimum acceptable output tokens to receive
        address[] calldata path, // List of token addresses to route through
        address to, // Address to which the output tokens will be sent
        uint deadline // Timestamp by which the swap must occur
    ) external returns (uint[] memory amounts); // Returns the amounts of tokens swapped
}

// Main contract for executing flash arbitrage strategies
contract FlashArbitrageExecutor {
    address private owner; // Owner of the contract
    IFlashLoanProvider public flashLoanProvider; // Instance of the flash loan provider
    IDEXRouter public dexRouter; // Instance of the DEX router for swaps

    // Contract constructor initializes the owner and the relevant contract instances
    constructor(address _flashLoanProvider, address _dexRouter) {
        owner = msg.sender; // Set the deployer of the contract as the owner
        flashLoanProvider = IFlashLoanProvider(_flashLoanProvider); // Assign flash loan provider
        dexRouter = IDEXRouter(_dexRouter); // Assign the DEX router
    }

    // Modifier to restrict access to certain functions, allowing only the owner to call them
    modifier onlyOwner() {
        require(msg.sender == owner, "Not the contract owner"); // Check if sender is the owner
        _; // Continue execution of the function
    }

    // Function to initiate arbitrage by requesting a flash loan
    function initiateArbitrage(
        uint256 amount, // Amount of tokens to borrow via flash loan
        address[] calldata path, // The token swap path used in arbitrage
        uint256 minAmountOut // Minimum amount of output tokens expected
    ) external onlyOwner {
        // Ensure only the owner can call this function
        // Request a flash loan with encoded data for path and minimum output amount
        flashLoanProvider.flashLoan(
            amount,
            address(this), // The current contract as the recipient
            abi.encode(path, minAmountOut) // Encode additional parameters for the loan
        );
    }

    // Function to execute the arbitrage after receiving the flash loan
    function executeArbitrage(
        address[] calldata path, // The token swap path for executing trades
        uint256 minAmountOut // Minimum output amount expected from the trade
    ) external {
        // Get the amount of tokens the contract received from the flash loan
        uint256 amountIn = IERC20(path[0]).balanceOf(address(this));

        // Approve the DEX router to spend the input tokens on behalf of this contract
        IERC20(path[0]).approve(address(dexRouter), amountIn);

        // Execute the token swap on the DEX router and get the amounts received
        uint256[] memory amounts = dexRouter.swapExactTokensForTokens(
            amountIn, // Amount of input tokens to swap
            minAmountOut, // Minimum output tokens expected
            path, // Token swap path
            address(this), // Address to receive output tokens
            block.timestamp // Current timestamp as the deadline
        );

        // Calculate profit from the arbitrage trade
        uint256 profit = amounts[amounts.length - 1] - amountIn; // Output tokens - input tokens
        require(profit > 0, "No profit from arbitrage"); // Ensure trade is profitable

        // Repay the flash loan by transferring the original amount back to the provider
        IERC20(path[0]).transfer(address(flashLoanProvider), amountIn);
    }
}

// Interface for ERC20 token standard functions
interface IERC20 {
    function balanceOf(address account) external view returns (uint256); // Get the balance of a specific account

    function approve(address spender, uint256 amount) external returns (bool); // Approve a spender to use tokens

    function transfer(
        address recipient,
        uint256 amount
    ) external returns (bool); // Transfer tokens to a recipient
}
