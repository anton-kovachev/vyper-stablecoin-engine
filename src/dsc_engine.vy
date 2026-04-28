# pragma version 0.4.3
"""
@license MIT
@author Anton
@dev The engine contract for the decentralized stable coin system. This contract will be responsible for mint
@notice
    Collateral: Exogenous  (WETH, WBTC, etc.)
    Stability (Minting) Mechanism: Algorithmic 
    Value (Relative stability): Anchored (Pegged to USD)
    Collateral Type: Crypto
"""

from interfaces import i_decentralized_stable_coin
from interfaces import AggregatorV3Interface
from ethereum.ercs import IERC20

# ------------------------------------------------------------------
#                         STATE VARIABLES
# ------------------------------------------------------------------

LIQUIDATION_THRESHOLD:public(constant(uint256)) = 50
LIQUIDATION_THRESHOLD_PRECISION: public(constant(uint256)) = 100
LIQUIDATION_BONUS: public(constant(uint256)) = 10
ADDITIONAL_FEED_PRECISION: public(constant(uint256)) = 1 * (10 ** 10)
PRECISION: public(constant(uint256)) = 1 * (10 ** 18)
MIN_HEALTH_FACTOR: public(constant(uint256)) = 1 * (10 ** 18)

DSC: public(immutable(i_decentralized_stable_coin))
COLLATERAL_TOKENS: public(immutable(address[2]))
PRICE_FEEDS: public(immutable(address[2]))

collateral_to_price_feed: public(HashMap[address, address])
user_to_token_to_amount_deposited: public(HashMap[address, HashMap[address, uint256]])
user_to_dsc_minted: public(HashMap[address, uint256])

# ------------------------------------------------------------------
#                              EVENTS
# ------------------------------------------------------------------

event CollateralDeposited:
    user: indexed(address)
    token: indexed(address)
    amount: uint256

event CollateralRedeemed:
    redeemed_from: indexed(address)
    redeemed_to: indexed(address)
    token: indexed(address)
    amount: uint256

# ------------------------------------------------------------------
#                        EXTERNAL FUNCTION
# ------------------------------------------------------------------

@deploy
def __init__(collateral_tokens: address[2], price_feed_addresses: address[2], dsc_address: address):
    """
    @notice Initializes the DSC Engine with collateral tokens, price feeds, and DSC token address
    @dev Sets up the collateral-to-price-feed mapping and stores immutable references
    @param collateral_tokens Array of 2 ERC20 token addresses to be used as collateral [WETH, WBTC]
    @param price_feed_addresses Array of 2 Chainlink price feed addresses corresponding to collateral tokens
    @param dsc_address Address of the DecentralizedStableCoin contract
    @custom:requirements All addresses must be non-zero; Arrays must have exactly 2 elements each, matching order
    """

    assert dsc_address != empty(address), "DSCEngine__DSCAddressCannotBeZeroAddress"
    assert collateral_tokens[0] != empty(address) and collateral_tokens[1] != empty(address), "DSCEngine__CollateralTokenAddressesCannotBeZeroAddress"
    assert price_feed_addresses[0] != empty(address) and price_feed_addresses[1] != empty(address), "DSCEngine__PriceFeedAddressesCannotBeZeroAddress"

    DSC = i_decentralized_stable_coin(dsc_address)
    COLLATERAL_TOKENS = collateral_tokens 
    PRICE_FEEDS = price_feed_addresses

    self.collateral_to_price_feed[collateral_tokens[0]] = price_feed_addresses[0]
    self.collateral_to_price_feed[collateral_tokens[1]] = price_feed_addresses[1]

# ------------------------------------------------------------------
#                             EXTERNAL
# ------------------------------------------------------------------

@external
def deposit_collateral(token_collateral: address, amount_collateral: uint256):
    """
    @notice Deposits collateral into the protocol
    @dev Transfers tokens from user to contract and updates user's collateral balance
    @param token_collateral Address of the collateral token (must be WETH or WBTC)
    @param amount_collateral Amount of collateral to deposit (in wei/satoshi)
    @custom:emits CollateralDeposited
    @custom:requirements Token must be approved for transfer; Amount must be > 0; Token must be supported collateral
    """
    self._deposit_collateral(token_collateral, amount_collateral)

@external
def deposit_collateral_and_mint_dsc(token_collateral: address, amount_collateral: uint256, amount_dsc_to_mint: uint256):
    """
    @notice Deposits collateral and mints DSC in a single transaction
    @dev Combines deposit and mint operations for gas efficiency
    @param token_collateral Address of the collateral token to deposit
    @param amount_collateral Amount of collateral to deposit (in wei/satoshi)
    @param amount_dsc_to_mint Amount of DSC stablecoin to mint (in wei)
    @custom:emits CollateralDeposited
    @custom:requirements Must maintain health factor >= MIN_HEALTH_FACTOR after minting; Collateral approved; Both amounts > 0
    """
    self._deposit_collateral(token_collateral, amount_collateral)
    self._mint_dsc(amount_dsc_to_mint)

@external
def mint_dsc(amount_to_mint: uint256):
    """
    @notice Mints DSC stablecoin against existing collateral
    @dev Increases user's DSC debt and mints tokens to their address
    @param amount_to_mint Amount of DSC to mint (in wei)
    @custom:requirements Sufficient collateral for health factor >= MIN_HEALTH_FACTOR; Amount > 0; 200% collateralization (50% threshold)
    """
    self._mint_dsc(amount_to_mint)

@external
def redeem_collateral(collateral: address, amount_to_redeem: uint256):
    """
    @notice Withdraws collateral from the protocol
    @dev Transfers collateral tokens back to user and checks health factor after redemption
    @param collateral Address of the collateral token to withdraw
    @param amount_to_redeem Amount of collateral to withdraw (in wei/satoshi)
    @custom:emits CollateralRedeemed
    @custom:requirements Sufficient collateral deposited; Health factor >= MIN_HEALTH_FACTOR after redemption; Amount > 0
    """
    self._redeem_collateral(collateral, amount_to_redeem, msg.sender, msg.sender)
    self._revert_if_health_factor_below_min(msg.sender)

@external
def redeem_for_dsc(collateral: address, amount_to_redeem: uint256, amount_dsc: uint256):
    """
    @notice Burns DSC and redeems collateral in a single transaction
    @dev Combines burn and redeem operations to improve capital efficiency
    @param collateral Address of the collateral token to withdraw
    @param amount_to_redeem Amount of collateral to withdraw (in wei/satoshi)
    @param amount_dsc Amount of DSC to burn (in wei)
    @custom:emits CollateralRedeemed
    @custom:requirements DSC approved for burning; Sufficient DSC debt to burn; Health factor >= MIN_HEALTH_FACTOR after redemption
    """
    self._burn_dsc(msg.sender, msg.sender, amount_dsc)
    self._redeem_collateral(collateral, amount_to_redeem, msg.sender, msg.sender)
    self._revert_if_health_factor_below_min(msg.sender)

@external
def burn_dsc(amount_to_burn: uint256):
    """
    @notice Burns DSC stablecoin to reduce user's debt
    @dev Decreases user's DSC minted balance and burns tokens from their address
    @param amount_to_burn Amount of DSC to burn (in wei)
    @custom:requirements Sufficient DSC balance; DSC approved for burning; Amount <= user's debt
    """
    self._burn_dsc(msg.sender, msg.sender, amount_to_burn)
    self._revert_if_health_factor_below_min(msg.sender)

@external
def liquidate(collateral: address, user: address, debt_to_cover: uint256):
    """
    @notice Liquidates an undercollateralized position to protect the protocol
    @dev Caller burns DSC to cover user's debt and receives collateral + 10% bonus
    @param collateral Address of the collateral token to seize from the liquidated user
    @param user Address of the user being liquidated (must have health factor < MIN_HEALTH_FACTOR)
    @param debt_to_cover Amount of DSC debt to cover (in wei)
    @custom:emits CollateralRedeemed
    @custom:requirements Health factor < MIN_HEALTH_FACTOR (1e18); debt_to_cover > 0; Liquidation improves health factor; DSC approved; Liquidator health factor >= MIN_HEALTH_FACTOR
    @custom:incentive Liquidator receives 110% of debt value in collateral (10% bonus)
    """
    assert debt_to_cover > 0, "DSCEngine__NeedsMoreThanZero"
    starting_health_factor: uint256 = self._calculate_health_factor(user)

    assert starting_health_factor < MIN_HEALTH_FACTOR, "DSCEngine_HealthFactorIsAboveMinimum"

    token_amount_from_debt_to_cover: uint256 = self._get_token_amount_from_usd(collateral, debt_to_cover)
    bonus_collateral: uint256 = (token_amount_from_debt_to_cover * LIQUIDATION_BONUS) // LIQUIDATION_THRESHOLD_PRECISION 

    self._redeem_collateral(collateral, token_amount_from_debt_to_cover + bonus_collateral, user, msg.sender)
    self._burn_dsc(user, msg.sender, debt_to_cover)

    ending_health_factor: uint256 = self._calculate_health_factor(user)
    assert ending_health_factor > starting_health_factor, "DSCEngine__HealthFactorDidNotImprove"
    self._revert_if_health_factor_below_min(user)
    self._revert_if_health_factor_below_min(msg.sender)

# ------------------------------------------------------------------
#                          EXTERNAL VIEW
# ------------------------------------------------------------------

@external
@view
def health_factor(user: address) -> uint256:
    """
    @notice Calculates and returns the health factor for a user
    @dev Health factor = (collateral_value * liquidation_threshold / 100) * 1e18 / debt
    @param user Address of the user to check
    @return uint256 Health factor with 18 decimals (1e18 = 100%, 2e18 = 200%)
    @custom:interpretation <1e18: undercollateralized (can liquidate); >=1e18: safe; max_value: no debt
    """
    return self._calculate_health_factor(user)
    
@internal
def _deposit_collateral(collateral: address, amount_collateral: uint256):
    """
    @notice Internal function to deposit collateral following Checks-Effects-Interactions pattern
    @dev Validates token support, updates balances, and transfers tokens
    @param collateral Address of the collateral token
    @param amount_collateral Amount to deposit (in native token decimals)
    @custom:emits CollateralDeposited
    """
    # Checks
    assert amount_collateral > 0, "DSCEngine__NeedsMoreThanZero"
    assert self.collateral_to_price_feed[collateral] != empty(address), "DSCEngine__TokenNotSupported"

    # Effects
    self.user_to_token_to_amount_deposited[msg.sender][collateral] += amount_collateral
    log CollateralDeposited(user = msg.sender, token = collateral, amount = amount_collateral)

    # Interactions (External calls)
    success: bool = extcall IERC20(collateral).transferFrom(msg.sender, self, amount_collateral)
    assert success, "Transfer failed"

@external
@view
def get_usd_value(token: address, amount: uint256) -> uint256:
    """
    @notice Converts a token amount to USD value using Chainlink price feeds
    @dev Fetches price from oracle and normalizes to 18 decimals
    @param token Address of the token to price
    @param amount Amount of tokens (in token's native decimals)
    @return uint256 USD value with 18 decimals precision
    """
    return self._get_usd_value(token, amount)

@external
@view
def get_token_amount_from_usd(collateral: address, usd_amount: uint256) -> uint256:
    """
    @notice Converts a USD value to token amount using Chainlink price feeds
    @dev Inverse of get_usd_value - divides USD by token price
    @param collateral Address of the collateral token
    @param usd_amount USD value with 18 decimals precision
    @return uint256 Amount of tokens (in token's native decimals)
    """
    return self._get_token_amount_from_usd(collateral, usd_amount)

@external
@view
def get_dsc() -> address:
    """
    @notice Returns the address of the DecentralizedStableCoin contract
    @return address The DSC token contract address
    """
    return DSC.address

@external
@view
def get_account_information(user: address) -> (uint256, uint256):
    """
    @notice Returns complete account information for a user
    @param user Address of the user to query
    @return tuple (total_dsc_minted: 18 decimals, total_collateral_value_in_usd: 18 decimals)
    """
    return self._get_account_information(user)

@external
@view
def get_collateral_adjusted_for_health_factor(user: address) -> uint256:
    """
    @notice Returns collateral value adjusted by liquidation threshold (50%)
    @dev This is the maximum DSC that can be minted against the collateral
    @param user Address of the user to query
    @return uint256 Adjusted collateral value in USD (18 decimals)
    @custom:formula adjusted_collateral = total_collateral_usd * 50 / 100
    """
    total_collateral_value_in_usd: uint256 = self._get_account_collateral_value(user)
    collateral_adjusted_for_health_factor: uint256 = (total_collateral_value_in_usd * LIQUIDATION_THRESHOLD) // LIQUIDATION_THRESHOLD_PRECISION
    return collateral_adjusted_for_health_factor
    

# ------------------------------------------------------------------
#                             INTERNAL
# ------------------------------------------------------------------

@internal
def _mint_dsc(amount_dsc_to_mint: uint256):
    """
    @notice Internal function to mint DSC tokens
    @dev Updates user's debt and checks health factor before minting
    @param amount_dsc_to_mint Amount of DSC to mint (in wei)
    """
    assert amount_dsc_to_mint > 0, "DSCEngine__AmountToMintMustBeAboveZero"
    self.user_to_dsc_minted[msg.sender] += amount_dsc_to_mint
    self._revert_if_health_factor_below_min(msg.sender)
    extcall DSC.mint(msg.sender, amount_dsc_to_mint)

@internal
def _redeem_collateral(collateral: address, amount_to_redeem: uint256, _from: address, _to: address):
    """
    @notice Internal function to redeem collateral
    @dev Updates balances and transfers tokens
    @param collateral Address of collateral token
    @param amount_to_redeem Amount to redeem
    @param _from Address to deduct collateral from
    @param _to Address to send collateral to
    """
    assert amount_to_redeem > 0, "DSCEngine__AmountToRedeemMustBeGreaterThanZero"
    assert self.collateral_to_price_feed[collateral] != empty(address), "DCSEngine__TokenNotSupported"
    assert self.user_to_token_to_amount_deposited[_from][collateral] >= amount_to_redeem, "DSCEngine__AmountToRedeemIsGreaterThanAmountDeposited"

    self.user_to_token_to_amount_deposited[_from][collateral] -= amount_to_redeem

    log CollateralRedeemed(redeemed_from = _from, redeemed_to = _to, token = collateral, amount = amount_to_redeem)
    success: bool = extcall IERC20(collateral).transfer(_to, amount_to_redeem)
    assert success, "Transfer failed"
    
@internal
def _burn_dsc(_on_behalf_of: address, dsc_from: address, amount: uint256):
    """
    @notice Internal function to burn DSC tokens
    @dev Reduces debt for one user while burning tokens from another
    @param _on_behalf_of Address whose debt to reduce
    @param dsc_from Address to burn DSC tokens from
    @param amount Amount of DSC to burn (in wei)
    """
    self.user_to_dsc_minted[_on_behalf_of] -= amount
    extcall DSC.burn_from(dsc_from, amount)

@internal
@view
def _get_account_information(user: address) -> (uint256, uint256):
    """
    @notice Internal function to get account information
    @param user Address to query
    @return tuple (total_dsc_minted, total_collateral_value_in_usd)
    """
    total_dsc_minted: uint256 = self.user_to_dsc_minted[user]

    total_collateral_value_in_usd: uint256 = self._get_account_collateral_value(user)
    return (total_dsc_minted, total_collateral_value_in_usd)

@internal
@view
def _get_account_collateral_value(user: address) -> uint256:
    """
    @notice Internal function to calculate total collateral value across all tokens
    @param user Address to query
    @return uint256 Total collateral value in USD (18 decimals)
    """
    total_collateral_value_in_usd: uint256 = 0

    for collateral: address in COLLATERAL_TOKENS:
        amount_deposited: uint256 = self.user_to_token_to_amount_deposited[user][collateral]
        total_collateral_value_in_usd += self._get_usd_value(collateral, amount_deposited)

    return total_collateral_value_in_usd

@internal
@view
def _revert_if_health_factor_below_min(user: address):
    """
    @notice Internal function to check if user's health factor is acceptable
    @dev Reverts if health factor < MIN_HEALTH_FACTOR (1e18)
    @param user Address to check
    """
    assert self._calculate_health_factor(user) >= MIN_HEALTH_FACTOR, "DSCEngine__HealthFactorTooLow"

@internal
@view
def _calculate_health_factor(user: address) -> uint256:
    """
    @notice Internal function to calculate user's health factor
    @dev Formula: (collateral_usd * 50 / 100 * 1e18) / dsc_minted
    @param user Address to calculate for
    @return uint256 Health factor with 18 decimals (1e18 = 100%)
    @custom:special Returns max_value(uint256) if user has no debt
    """
    if self.user_to_dsc_minted[user] == 0:
        return max_value(uint256) 

    total_amount_of_collateral_in_usd: uint256 = 0
    total_amount_of_collateral: uint256 = 0
    for collateral: address in COLLATERAL_TOKENS:
        total_amount_of_collateral += self.user_to_token_to_amount_deposited[user][collateral]
        total_amount_of_collateral_in_usd += self._get_usd_value(collateral, self.user_to_token_to_amount_deposited[user][collateral])

    collateral_adjusted_for_health_factor: uint256 = (total_amount_of_collateral_in_usd * LIQUIDATION_THRESHOLD) // LIQUIDATION_THRESHOLD_PRECISION
    return (collateral_adjusted_for_health_factor * PRECISION) // self.user_to_dsc_minted[user] 

@internal
@view
def _get_usd_value(token: address, amount: uint256) -> uint256:
    """
    @notice Internal function to get USD value from token amount
    @dev Fetches price from Chainlink oracle and normalizes to 18 decimals
    @param token Address of the token
    @param amount Amount of tokens (in native decimals)
    @return uint256 USD value with 18 decimals
    @custom:formula (price * 1e10 * amount) / 1e18
    """
    price_feed: AggregatorV3Interface = AggregatorV3Interface(self.collateral_to_price_feed[token])
    return ((convert(staticcall price_feed.latestAnswer(), uint256) * ADDITIONAL_FEED_PRECISION)  * amount) // PRECISION 

@internal
@view
def _get_token_amount_from_usd(collateral: address, usd_amount: uint256) -> uint256:
    """
    @notice Internal function to convert USD value to token amount
    @dev Inverse calculation of _get_usd_value
    @param collateral Address of the collateral token
    @param usd_amount USD value with 18 decimals
    @return uint256 Token amount (in native decimals)
    @custom:formula (usd_amount * 1e18) / (price * 1e10)
    """
    price_feed: AggregatorV3Interface = AggregatorV3Interface(self.collateral_to_price_feed[collateral])
    
    return (usd_amount * PRECISION) // (convert(staticcall price_feed.latestAnswer(), uint256) * ADDITIONAL_FEED_PRECISION)
    
