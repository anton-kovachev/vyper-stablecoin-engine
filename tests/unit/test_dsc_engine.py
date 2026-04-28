import boa
import pytest
from unittest.mock import patch
from src import dsc_engine
from src.mocks import MockV3Aggregator
from eth.codecs.abi.exceptions import EncodeError
from conftest import ZERO_ADDRESS, BALANCE, AMOUNT_TO_DEPOSIT, PRECISION


def test_reverts_if_token_lengths_are_different(
    weth, wbtc, eth_usd_price_feed, btc_usd_price_feed, dsc
):
    with pytest.raises(EncodeError):
        dsc_engine.deploy(
            [weth.address, wbtc.address, wbtc.address],
            [eth_usd_price_feed.address, btc_usd_price_feed.address],
            dsc.address,
        )


def test_reverts_if_collateral_token_is_zero_address(
    weth, wbtc, eth_usd_price_feed, btc_usd_price_feed, dsc
):
    with boa.reverts("DSCEngine__CollateralTokenAddressesCannotBeZeroAddress"):
        dsc_engine.deploy(
            [weth.address, ZERO_ADDRESS],
            [eth_usd_price_feed.address, btc_usd_price_feed.address],
            dsc.address,
        )


def test_reverts_if_price_feed_is_zero_address(
    weth, wbtc, eth_usd_price_feed, btc_usd_price_feed, dsc
):
    with boa.reverts("DSCEngine__PriceFeedAddressesCannotBeZeroAddress"):
        dsc_engine.deploy(
            [weth.address, wbtc.address],
            [ZERO_ADDRESS, btc_usd_price_feed.address],
            dsc.address,
        )


def test_reverts_if_dsc_is_zero_address(
    weth, wbtc, eth_usd_price_feed, btc_usd_price_feed
):
    with boa.reverts("DSCEngine__DSCAddressCannotBeZeroAddress"):
        dsc_engine.deploy(
            [weth.address, wbtc.address],
            [eth_usd_price_feed.address, btc_usd_price_feed.address],
            ZERO_ADDRESS,
        )


# ------------------------------------------------------------------
#                        DEPOSIT COLLATERAL
# ------------------------------------------------------------------


def test_reverts_if_collateral_zero(some_user, weth, dsc_engine):
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__NeedsMoreThanZero"):
            dsc_engine.deposit_collateral(weth.address, 0)


def test_reverts_if_collateral_token_invalid(some_user, weth, dsc_engine):
    random_token = boa.env.generate_address("random_token")
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__TokenNotSupported"):
            dsc_engine.deposit_collateral(random_token, 10)


def test_deposit_reverts_if_collateral_amount_is_zero(some_user, weth, dsc_engine):
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__NeedsMoreThanZero"):
            dsc_engine.deposit_collateral(weth.address, 0)


def test_deposit_reverts_if_collateral_amount_not_approved(some_user, weth, dsc_engine):
    with boa.env.prank(some_user):
        with boa.reverts():
            dsc_engine.deposit_collateral(weth.address, AMOUNT_TO_DEPOSIT)


def test_deposit_collateral_emits_collateral_deposited_event(
    some_user, weth, dsc_engine
):
    with boa.env.prank(some_user):
        weth.approve(dsc_engine.address, AMOUNT_TO_DEPOSIT)
        dsc_engine.deposit_collateral(weth.address, AMOUNT_TO_DEPOSIT)

    logs = dsc_engine.get_logs()
    assert "CollateralDeposited" in str(type(logs[0]))
    assert logs[0].user == some_user
    assert logs[0].token == weth.address
    assert logs[0].amount == AMOUNT_TO_DEPOSIT


def test_deposit_collateral_records_collateral_balance(some_user, weth, dsc_engine):
    with boa.env.prank(some_user):
        weth.approve(dsc_engine.address, AMOUNT_TO_DEPOSIT)
        dsc_engine.deposit_collateral(weth.address, AMOUNT_TO_DEPOSIT)

    assert (
        dsc_engine.user_to_token_to_amount_deposited(some_user, weth.address)
        == AMOUNT_TO_DEPOSIT
    )


def test_mint_dsc_reverts_if_user_has_no_collateral_deposited(some_user, dsc_engine):
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__HealthFactorTooLow"):
            dsc_engine.mint_dsc(1)


def test_mint_dsc_reverts_if_user_wants_to_mint_zero_dsc(
    some_user, dsc_engine_with_collateral
):
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__AmountToMintMustBeAboveZero"):
            dsc_engine_with_collateral.mint_dsc(0)


def test_mint_dsc_reverts_if_user_wants_to_mint_more_than_what_is_allowed(
    some_user, dsc_engine_with_collateral, eth_usd_price_feed
):
    price = eth_usd_price_feed.latestAnswer()
    decimals = eth_usd_price_feed.decimals()
    normalized_price = price * (10 ** (18 - decimals))

    liquidation_threshold = dsc_engine_with_collateral.LIQUIDATION_THRESHOLD()
    liquidation_threshold_precision = (
        dsc_engine_with_collateral.LIQUIDATION_THRESHOLD_PRECISION()
    )

    amount_to_mint = (
        (
            (
                (AMOUNT_TO_DEPOSIT * liquidation_threshold)
                // liquidation_threshold_precision
            )
            * normalized_price
        )
        // dsc_engine_with_collateral.PRECISION()
    ) + 1
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__HealthFactorTooLow"):
            # with boa.reverts():
            dsc_engine_with_collateral.mint_dsc(amount_to_mint)


def test_mint_dsc_emits_transfer_event(
    some_user, dsc_engine_with_collateral, eth_usd_price_feed
):
    price = eth_usd_price_feed.latestAnswer()
    decimals = eth_usd_price_feed.decimals()
    normalized_price = price * (10 ** (18 - decimals))

    liquidation_threshold = dsc_engine_with_collateral.LIQUIDATION_THRESHOLD()
    liquidation_threshold_precision = (
        dsc_engine_with_collateral.LIQUIDATION_THRESHOLD_PRECISION()
    )

    amount_to_mint = (
        (
            (
                (AMOUNT_TO_DEPOSIT * liquidation_threshold)
                // liquidation_threshold_precision
            )
            * normalized_price
        )
        // dsc_engine_with_collateral.PRECISION()
    ) - 1
    with boa.env.prank(some_user):
        dsc_engine_with_collateral.mint_dsc(amount_to_mint)

    logs = dsc_engine_with_collateral.get_logs()
    assert "Transfer" in str(type(logs[0]))
    assert logs[0].receiver == some_user
    assert logs[0].value == amount_to_mint


def test_mint_dsc_updates_dsc_balance(
    some_user, dsc_engine_with_collateral, eth_usd_price_feed
):
    price = eth_usd_price_feed.latestAnswer()
    decimals = eth_usd_price_feed.decimals()
    normalized_price = price * (10 ** (18 - decimals))

    liquidation_threshold = dsc_engine_with_collateral.LIQUIDATION_THRESHOLD()
    liquidation_threshold_precision = (
        dsc_engine_with_collateral.LIQUIDATION_THRESHOLD_PRECISION()
    )

    amount_to_mint = (
        (
            (
                (AMOUNT_TO_DEPOSIT * liquidation_threshold)
                // liquidation_threshold_precision
            )
            * normalized_price
        )
        // dsc_engine_with_collateral.PRECISION()
    ) - 1
    with boa.env.prank(some_user):
        dsc_engine_with_collateral.mint_dsc(amount_to_mint)

    assert dsc_engine_with_collateral.user_to_dsc_minted(some_user) == amount_to_mint


def test_redeem_collateral_reverts_if_amount_to_redeem_is_zero(
    some_user, dsc_engine, weth
):
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__AmountToRedeemMustBeGreaterThanZero"):
            dsc_engine.redeem_collateral(weth.address, 0)


def test_redeem_collateral_reverts_if_token_is_not_supported(some_user, dsc_engine):
    random_address = boa.env.generate_address("random_address")
    amount_to_redeem = 10
    with boa.env.prank(some_user):
        with boa.reverts("DCSEngine__TokenNotSupported"):
            dsc_engine.redeem_collateral(random_address, amount_to_redeem)


def test_redeem_collateral_reverts_if_amount_to_redeem_is_greater_than_deposited_amount(
    some_user, dsc_engine, weth
):
    amount_to_redeem = AMOUNT_TO_DEPOSIT + 1
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__AmountToRedeemIsGreaterThanAmountDeposited"):
            dsc_engine.redeem_collateral(weth.address, amount_to_redeem)


def test_redeem_collateral_health_factor_too_low(
    some_user, dsc_engine_with_collateral_and_dsc_minted, weth
):
    amount_to_redeem = 10
    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__HealthFactorTooLow"):
            dsc_engine_with_collateral_and_dsc_minted.redeem_collateral(
                weth.address, amount_to_redeem
            )


def test_redeem_collateral_emits_collateral_redeemed(
    some_user, dsc_engine_with_collateral_and_less_dsc_minted, weth
):
    amount_to_redeem = (AMOUNT_TO_DEPOSIT * 25) // 100
    with boa.env.prank(some_user):
        dsc_engine_with_collateral_and_less_dsc_minted.redeem_collateral(
            weth.address, amount_to_redeem
        )

    logs = dsc_engine_with_collateral_and_less_dsc_minted.get_logs()
    assert "CollateralRedeemed" in str(type(logs[0]))
    assert logs[0].redeemed_from == some_user
    assert logs[0].redeemed_to == some_user
    assert logs[0].token == weth.address
    assert logs[0].amount == amount_to_redeem


def test_redeem_collateral_updates_collateral_balance(
    some_user, dsc_engine_with_collateral_and_less_dsc_minted, weth
):
    collateral_balance_before = dsc_engine_with_collateral_and_less_dsc_minted.user_to_token_to_amount_deposited(
        some_user, weth.address
    )
    amount_to_redeem = (AMOUNT_TO_DEPOSIT * 25) // 100
    with boa.env.prank(some_user):
        dsc_engine_with_collateral_and_less_dsc_minted.redeem_collateral(
            weth.address, amount_to_redeem
        )

    collateral_balance_after = dsc_engine_with_collateral_and_less_dsc_minted.user_to_token_to_amount_deposited(
        some_user, weth.address
    )

    assert collateral_balance_after == collateral_balance_before - amount_to_redeem


def test_redeem_collateral_for_dsc_emits_collateral_redeemed_event(
    some_user,
    dsc_engine_with_collateral_and_dsc_minted,
    dsc,
    weth,
    eth_usd_price_feed,
    maximum_mintable_dsc,
    normalized_weth_usd_price,
):
    dsc_to_burn = maximum_mintable_dsc - 1
    amount_to_redeem = dsc_to_burn * PRECISION // normalized_weth_usd_price

    with boa.env.prank(some_user):
        dsc.approve(
            dsc_engine_with_collateral_and_dsc_minted.address,
            dsc_to_burn,
        )
        dsc_engine_with_collateral_and_dsc_minted.redeem_for_dsc(
            weth.address, amount_to_redeem, dsc_to_burn
        )

    logs = [
        log
        for log in dsc_engine_with_collateral_and_dsc_minted.get_logs()
        if type(log).__name__ == "CollateralRedeemed"
    ]

    assert "CollateralRedeemed" in [type(log).__name__ for log in logs]
    assert logs[0].redeemed_from == some_user
    assert logs[0].redeemed_to == some_user
    assert logs[0].token == weth.address
    assert logs[0].amount == amount_to_redeem

    assert dsc_engine_with_collateral_and_dsc_minted.user_to_dsc_minted(some_user) == 0


def test_redeem_collateral_for_dsc_reverts(
    some_user,
    dsc_engine_with_collateral_and_dsc_minted,
    dsc,
    weth,
    eth_usd_price_feed,
    maximum_mintable_dsc,
    normalized_weth_usd_price,
):
    dsc_to_burn = maximum_mintable_dsc
    dsc_to_redeem = 2 * (10**4)
    amount_to_redeem = dsc_to_burn * PRECISION // normalized_weth_usd_price

    with boa.env.prank(some_user):
        with boa.reverts("DSCEngine__HealthFactorTooLow"):
            dsc.approve(
                dsc_engine_with_collateral_and_dsc_minted.address,
                dsc_to_burn,
            )
            dsc_engine_with_collateral_and_dsc_minted.redeem_for_dsc(
                weth.address, amount_to_redeem, dsc_to_redeem
            )


def test_liquidate_reverts_if_user_health_factor_is_above_liquidation_threshold(
    some_user,
    dsc_engine_with_collateral_and_less_dsc_minted,
    weth,
    eth_usd_price_feed,
    liquidator,
    debt_to_cover,
    maximum_mintable_dsc,
):
    with boa.env.prank(liquidator):
        weth.approve(
            dsc_engine_with_collateral_and_less_dsc_minted.address, AMOUNT_TO_DEPOSIT
        )
        dsc_engine_with_collateral_and_less_dsc_minted.deposit_collateral_and_mint_dsc(
            weth.address, AMOUNT_TO_DEPOSIT, maximum_mintable_dsc
        )
        with boa.reverts("DSCEngine_HealthFactorIsAboveMinimum"):
            dsc_engine_with_collateral_and_less_dsc_minted.liquidate(
                weth.address, some_user, debt_to_cover
            )


def test_liquidate_if_user_health_factor_is_below_minimum(
    some_user,
    dsc,
    dsc_engine_with_collateral_and_dsc_minted,
    weth,
    eth_usd_price_feed,
    liquidator,
    maximum_mintable_dsc,
):
    with boa.env.prank(liquidator):
        weth.approve(
            dsc_engine_with_collateral_and_dsc_minted.address,
            weth.balanceOf(liquidator),
        )
        dsc_engine_with_collateral_and_dsc_minted.deposit_collateral_and_mint_dsc(
            weth.address,
            weth.balanceOf(liquidator),
            maximum_mintable_dsc * 2,
        )

        price_feed_address = (
            dsc_engine_with_collateral_and_dsc_minted.collateral_to_price_feed(
                weth.address
            )
        )

        # Get the price feed contract and update the price to crash it
        health_factor_before = dsc_engine_with_collateral_and_dsc_minted.health_factor(
            some_user
        )
        price_feed = MockV3Aggregator.at(price_feed_address)
        new_price = (
            eth_usd_price_feed.latestAnswer() * 80
        ) // 100  # Reduce price by 80%
        price_feed.updateAnswer(new_price)
        health_factor_after = dsc_engine_with_collateral_and_dsc_minted.health_factor(
            some_user
        )

        some_user_dsc_minted = (
            dsc_engine_with_collateral_and_dsc_minted.user_to_dsc_minted(some_user)
        )

        debt_to_cover = (some_user_dsc_minted * 50) // 100
        # with boa.reverts("DSCEngine_HealthFactorIsAboveMinimum"):
        dsc.approve(dsc_engine_with_collateral_and_dsc_minted.address, debt_to_cover)
        dsc_engine_with_collateral_and_dsc_minted.liquidate(
            weth.address, some_user, debt_to_cover
        )
