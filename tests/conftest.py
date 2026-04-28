import pytest
import boa
from moccasin.config import get_active_network
from script.deploy_dsc_engine import deploy_dsc_engine
from eth_account import Account
from eth_utils import to_wei

# ------------------------------------------------------------------
#                          SESSION SCOPED
# ------------------------------------------------------------------
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
BALANCE = to_wei(10, "ether")
AMOUNT_TO_DEPOSIT = 2 * (10**18)
PRECISION = 1 * (10**18)


@pytest.fixture(scope="session")
def active_network():
    return get_active_network()


@pytest.fixture(scope="session")
def weth(active_network):
    return active_network.manifest_named("weth")


@pytest.fixture(scope="session")
def wbtc(active_network):
    return active_network.manifest_named("wbtc")


@pytest.fixture(scope="session")
def eth_usd_price_feed(active_network):
    return active_network.manifest_named("eth_usd_price_feed")


@pytest.fixture(scope="session")
def btc_usd_price_feed(active_network):
    return active_network.manifest_named("btc_usd_price_feed")


# ------------------------------------------------------------------
#                         FUNCTION SCOPED
# ------------------------------------------------------------------


@pytest.fixture(scope="function")
def dsc(active_network):
    return active_network.manifest_named("decentralized_stable_coin")


@pytest.fixture(scope="function")
def dsc_engine(weth, wbtc, eth_usd_price_feed, btc_usd_price_feed, dsc):
    return deploy_dsc_engine(dsc)


@pytest.fixture(scope="function")
def some_user(weth, wbtc):
    entropy = 13
    account = Account.create(entropy)
    boa.env.set_balance(account.address, BALANCE)
    with boa.env.prank(account.address):
        weth.mock_mint()
        wbtc.mock_mint()
    return account.address


@pytest.fixture(scope="function")
def dsc_engine_with_collateral(some_user, weth, wbtc, dsc_engine):
    with boa.env.prank(some_user):
        weth.approve(dsc_engine.address, AMOUNT_TO_DEPOSIT)
        dsc_engine.deposit_collateral(weth.address, AMOUNT_TO_DEPOSIT)
    return dsc_engine


@pytest.fixture(scope="function")
def dsc_engine_with_collateral_and_dsc_minted(
    some_user, weth, wbtc, dsc_engine_with_collateral, eth_usd_price_feed
):
    eth_usd_price_feed.updateAnswer(eth_usd_price_feed.latestAnswer() // 4)
    price = eth_usd_price_feed.latestAnswer()
    decimals = eth_usd_price_feed.decimals()
    normalized_price = price * (10 ** (18 - decimals))

    liquidation_threshold = dsc_engine_with_collateral.LIQUIDATION_THRESHOLD()
    liquidation_threshold_precision = (
        dsc_engine_with_collateral.LIQUIDATION_THRESHOLD_PRECISION()
    )

    amount_to_mint = (
        calculate_max_amount_to_mint(
            AMOUNT_TO_DEPOSIT,
            liquidation_threshold,
            liquidation_threshold_precision,
            normalized_price,
            dsc_engine_with_collateral.PRECISION(),
        )
        - 1
    )

    print("Amount to mint:", amount_to_mint)

    with boa.env.prank(some_user):
        dsc_engine_with_collateral.mint_dsc(amount_to_mint)

    return dsc_engine_with_collateral


@pytest.fixture(scope="function")
def dsc_engine_with_collateral_and_less_dsc_minted(
    some_user, weth, wbtc, dsc_engine_with_collateral, eth_usd_price_feed
):
    price = eth_usd_price_feed.latestAnswer()
    decimals = eth_usd_price_feed.decimals()
    normalized_price = price * (10 ** (18 - decimals))

    liquidation_threshold = dsc_engine_with_collateral.LIQUIDATION_THRESHOLD()
    liquidation_threshold_precision = (
        dsc_engine_with_collateral.LIQUIDATION_THRESHOLD_PRECISION()
    )

    amount_to_mint = (
        calculate_max_amount_to_mint(
            AMOUNT_TO_DEPOSIT,
            liquidation_threshold,
            liquidation_threshold_precision,
            normalized_price,
            dsc_engine_with_collateral.PRECISION(),
        )
        * 25
    ) // 100

    print("Amount to mint:", amount_to_mint)
    with boa.env.prank(some_user):
        dsc_engine_with_collateral.mint_dsc(amount_to_mint)

    return dsc_engine_with_collateral


@pytest.fixture(scope="function")
def liquidator(weth, wbtc):
    entropy = 15
    account = Account.create(entropy)
    boa.env.set_balance(account.address, BALANCE)
    with boa.env.prank(account.address):
        for i in range(4):
            weth.mock_mint()
        wbtc.mock_mint()

    return account.address


@pytest.fixture(scope="function")
def maximum_mintable_dsc(
    dsc_engine,
    eth_usd_price_feed,
):
    price = eth_usd_price_feed.latestAnswer()
    decimals = eth_usd_price_feed.decimals()
    normalized_price = price * (10 ** (18 - decimals))

    liquidation_threshold = dsc_engine.LIQUIDATION_THRESHOLD()
    liquidation_threshold_precision = dsc_engine.LIQUIDATION_THRESHOLD_PRECISION()

    maximum_mintable_dsc = calculate_max_amount_to_mint(
        AMOUNT_TO_DEPOSIT,
        liquidation_threshold,
        liquidation_threshold_precision,
        normalized_price,
        PRECISION,
    )

    return maximum_mintable_dsc


def calculate_max_amount_to_mint(
    amount_to_deposit,
    liquidation_threshold,
    liquidation_threshold_precision,
    normalized_price,
    precision,
):
    print("Amount to deposit:", amount_to_deposit)
    print("Liquidation threshold:", liquidation_threshold)
    print("Liquidation threshold precision:", liquidation_threshold_precision)
    print("Normalized price:", normalized_price)
    print("Precision:", precision)
    return (
        ((amount_to_deposit * liquidation_threshold) // liquidation_threshold_precision)
        * normalized_price
    ) // precision


@pytest.fixture(scope="module")
def normalized_weth_usd_price(eth_usd_price_feed):
    price = eth_usd_price_feed.latestAnswer()
    decimals = eth_usd_price_feed.decimals()
    normalized_price = price * (10 ** (18 - decimals))

    return normalized_price


@pytest.fixture(scope="function")
def debt_to_cover(
    maximum_mintable_dsc,
):
    return maximum_mintable_dsc // 2
