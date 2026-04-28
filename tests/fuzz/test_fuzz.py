from hypothesis.stateful import RuleBasedStateMachine, initialize, rule, invariant
from script.deploy_dsc import deploy_dsc
from script.deploy_dsc_engine import deploy_dsc_engine
from moccasin.config import get_active_network
from eth.constants import ZERO_ADDRESS
from eth_utils import to_wei
from boa.util.abi import Address
from hypothesis import strategies as st, assume, settings
from src.mocks import mock_token, MockV3Aggregator
from boa.test.strategies import strategy
import boa
from boa import BoaError

USER_SIZE = 10
COLLATERAL_AMOUNT_TO_DEPOSIT = 2 * (10**18)
MAX_COLLATERAL_AMOUNT_TO_DEPOSIT = 10 * (10**18)
MAX_DEPOSIT = to_wei(1000, "ether")


class StablecoinFuzzer(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()

    @initialize()
    def setup(self):
        self.runs = 0
        self.dsc = deploy_dsc()
        self.dsc_engine = deploy_dsc_engine(self.dsc)

        active_network = get_active_network()
        self.weth = active_network.manifest_named("weth")
        self.wbtc = active_network.manifest_named("wbtc")

        self.liquidator = boa.env.generate_address("liquidator")
        self.users = [Address("0x" + ZERO_ADDRESS.hex())]

        while Address("0x" + ZERO_ADDRESS.hex()) in self.users:
            self.users = [boa.env.generate_address() for _ in range(10)]

    @rule(
        collateral_seed=st.integers(min_value=0, max_value=1),
        user_seed=st.integers(min_value=0, max_value=USER_SIZE - 1),
        amount=strategy("uint256", min_value=1, max_value=MAX_DEPOSIT),
    )
    def mint_and_deposit_collateral(self, collateral_seed, user_seed, amount):
        collateral_token_contract = self._get_collateral_from_seed(collateral_seed)
        user = self.users[user_seed]

        self._mint_and_depostit_collateral(
            collateral_token_contract.address, user, amount
        )

    @rule(
        collateral_seed=st.integers(min_value=0, max_value=1),
        user_seed=st.integers(min_value=0, max_value=USER_SIZE - 1),
        percentage_to_redeem=strategy("uint8", min_value=1, max_value=100),
    )
    def redeem_collateral(self, collateral_seed, user_seed, percentage_to_redeem):
        collateral_token_contract = self._get_collateral_from_seed(collateral_seed)
        user = self.users[user_seed]

        collateral_deposited = self.dsc_engine.user_to_token_to_amount_deposited(
            user, collateral_token_contract.address
        )

        collateral_to_redeem = (collateral_deposited * percentage_to_redeem) // 100
        assume(collateral_to_redeem > 0)
        with boa.env.prank(user):
            try:
                self.dsc_engine.redeem_collateral(
                    collateral_token_contract.address, collateral_to_redeem
                )
            except BoaError as err:
                if "DSCEngine__HealthFactorTooLow" in str(err.stack_trace[0].vm_error):
                    pass

    @rule(
        collateral_seed=st.integers(min_value=0, max_value=1),
        user_seed=st.integers(min_value=0, max_value=USER_SIZE - 1),
        amount=strategy("uint256", min_value=1, max_value=MAX_DEPOSIT),
    )
    def mint_dsc_and_update_price(self, user_seed, amount, collateral_seed):
        self.mint_dsc(user_seed, amount, collateral_seed)
        self.update_collateral_price(collateral_seed, price_percentage_change=0.7)

    # @rule(
    #     collateral_seed=st.integers(min_value=0, max_value=1),
    #     user_seed=st.integers(min_value=0, max_value=USER_SIZE - 1),
    #     amount=strategy("uint256", min_value=1, max_value=MAX_DEPOSIT),
    # )
    def mint_dsc(self, user_seed, amount, collateral_seed):
        user = self.users[user_seed]
        with boa.env.prank(user):
            try:
                self.dsc_engine.mint_dsc(amount)
            except Exception as err:
                if "DSCEngine__HealthFactorTooLow" in str(err.stack_trace[0].vm_error):
                    collateral_contract = self._get_collateral_from_seed(
                        collateral_seed
                    )

                    user_current_dsc_minted = self.dsc_engine.user_to_dsc_minted(user)
                    user_total_dsc_after_minting = user_current_dsc_minted + amount
                    user_total_collateral_value_in_usd_nedeed_to_support_dsc_debt = (
                        user_total_dsc_after_minting + 1
                    ) * 2
                    _, user_current_collateral_value_in_usd = (
                        self.dsc_engine.get_account_information(user)
                    )

                    user_collateral_usd_value_needed_to_mint = (
                        user_total_collateral_value_in_usd_nedeed_to_support_dsc_debt
                        - user_current_collateral_value_in_usd
                    )

                    if user_collateral_usd_value_needed_to_mint == 0:
                        user_collateral_usd_value_needed_to_mint = 1

                    if user_collateral_usd_value_needed_to_mint > 0:
                        token_amount_to_deposit = (
                            self.dsc_engine.get_token_amount_from_usd(
                                collateral_contract.address,
                                user_collateral_usd_value_needed_to_mint,
                            )
                        )

                        if token_amount_to_deposit == 0:
                            token_amount_to_deposit = 1

                        self.mint_and_deposit_collateral(
                            collateral_seed,
                            user_seed,
                            token_amount_to_deposit + 1,  # +1 for safety margin
                        )

                    self.dsc_engine.mint_dsc(amount)

    # @rule(
    #     collateral_seed=st.integers(min_value=0, max_value=1),
    #     price_percentage_change=st.floats(min_value=0.3, max_value=0.5),
    # )
    def update_collateral_price(self, collateral_seed, price_percentage_change):
        collateral_contract = self._get_collateral_from_seed(collateral_seed)
        price_feed_address = self.dsc_engine.collateral_to_price_feed(
            collateral_contract.address
        )

        price_feed_contract = MockV3Aggregator.at(price_feed_address)
        current_price = price_feed_contract.latestAnswer()
        price_feed_contract.updateAnswer(int(current_price * price_percentage_change))

    def _get_collateral_from_seed(self, seed):
        collateral_token_address = self.dsc_engine.COLLATERAL_TOKENS(seed)
        collateral_token_contract = mock_token.at(collateral_token_address)
        return collateral_token_contract

    # Invariant: Protocol must have more value in collateral that the total supply of DSC minted
    @invariant()
    def liquidate_and_check_collateralization(self):
        self.runs += 1
        for user in self.users:
            health_factor = self.dsc_engine.health_factor(user)
            if health_factor < self.dsc_engine.MIN_HEALTH_FACTOR():
                total_dsc_minted, _ = self.dsc_engine.get_account_information(user)

                total_collateral_value_in_usd_adjusted = (
                    self.dsc_engine.get_collateral_adjusted_for_health_factor(user)
                )

                # Calculate the MINIMUM debt needed to bring user to 110% health factor
                # Goal: Liquidate just enough so adjusted_collateral = debt × 1.1 (110%)
                #
                # Math: After liquidating X DSC:
                # - New debt = total_dsc - X
                # - Collateral removed = X * 1.1 (10% bonus)
                # - New adjusted collateral = (old_collateral - X*1.1) * 0.5
                #
                # For health_factor = 1.1e18 (110%):
                # - new_adjusted_collateral = new_debt × 1.1
                # - (old_collateral - X*1.1) * 0.5 = (total_dsc - X) × 1.1
                # - Solving for X: X = (total_dsc × 1.1 - adjusted_collateral) / 0.55

                _, total_collateral_value_in_usd = (
                    self.dsc_engine.get_account_information(user)
                )

                # Calculate target: debt × 1.1
                target_adjusted_collateral = (total_dsc_minted * 110) // 100

                # Check if user needs liquidation
                if total_collateral_value_in_usd_adjusted >= target_adjusted_collateral:
                    # User is actually safe or close enough, skip
                    continue

                # Calculate debt to cover to reach 110% health factor
                # X = (D × 1.1 - C_adjusted) / 0.55
                # In integer math: X = (D × 110 - C_adjusted × 100) / 55
                debt_to_cover = (
                    total_dsc_minted * 110
                    - total_collateral_value_in_usd_adjusted * 100
                ) // 55

                # Ensure we don't liquidate more than user's total debt
                debt_to_cover = min(debt_to_cover, total_dsc_minted)

                # Maximum debt that can be covered with available collateral (safety check)
                max_debt_coverable = (total_collateral_value_in_usd * 100) // 110
                debt_to_cover = min(debt_to_cover, max_debt_coverable)

                # Only liquidate if there's meaningful debt to cover
                if debt_to_cover < 1:
                    continue

                weth_collateral = self.dsc_engine.user_to_token_to_amount_deposited(
                    user, self.weth.address
                )
                wbtc_collateral = self.dsc_engine.user_to_token_to_amount_deposited(
                    user, self.wbtc.address
                )

                if weth_collateral >= wbtc_collateral:
                    collatera_token_contract = self.weth
                else:
                    collatera_token_contract = self.wbtc

                with boa.env.prank(self.liquidator):
                    # Check liquidator's existing DSC debt
                    existing_dsc_debt = self.dsc_engine.user_to_dsc_minted(
                        self.liquidator
                    )
                    total_dsc_debt_after_minting = existing_dsc_debt + debt_to_cover

                    # Need 200% collateralization (50% liquidation threshold)
                    # Calculate total collateral needed for TOTAL debt
                    total_required_collateral_value = (
                        total_dsc_debt_after_minting + 1
                    ) * 2

                    # Get current collateral value
                    _, current_collateral_value = (
                        self.dsc_engine.get_account_information(self.liquidator)
                    )

                    # Calculate additional collateral needed
                    additional_collateral_value_needed = (
                        total_required_collateral_value - current_collateral_value
                    )

                    if additional_collateral_value_needed > 0:
                        collateral_to_mint_for_liquidator = (
                            self.dsc_engine.get_token_amount_from_usd(
                                collatera_token_contract.address,
                                additional_collateral_value_needed,
                            )
                        )

                        if collateral_to_mint_for_liquidator == 0:
                            collateral_to_mint_for_liquidator = 1

                        self._mint_and_depostit_collateral(
                            collatera_token_contract.address,
                            self.liquidator,
                            collateral_to_mint_for_liquidator
                            + 1,  # +1 for safety margin
                        )

                    self.dsc_engine.mint_dsc(debt_to_cover)

                    try:
                        self.dsc.approve(self.dsc_engine.address, debt_to_cover)
                        self.dsc_engine.liquidate(
                            collatera_token_contract.address, user, debt_to_cover
                        )
                    except BoaError as er:
                        pass
        # self.check_collateralization()

    @invariant()
    def check_collateralization(self):
        weth_balance = self.weth.balanceOf(self.dsc_engine.address)
        weth_usd_value = self.dsc_engine.get_usd_value(self.weth.address, weth_balance)
        wbtc_balance = self.wbtc.balanceOf(self.dsc_engine.address)
        wbtc_usd_value = self.dsc_engine.get_usd_value(self.wbtc.address, wbtc_balance)

        total_collateral_value_in_usd = weth_usd_value + wbtc_usd_value
        total_dsc_minted = self.dsc.totalSupply()

        # Protocol must maintain at least 100% collateralization
        # Individual users need 200%, but protocol level can be lower
        # because users at different health factor levels balance out
        # We add a 10% buffer to account for liquidation bonuses
        min_required_collateral = (
            total_dsc_minted * 110
        ) // 100  # 110% for liquidation bonus

        assert (
            total_collateral_value_in_usd >= min_required_collateral
        ), f"Protocol is undercollateralized: {total_collateral_value_in_usd} < {min_required_collateral}"

    def _mint_and_depostit_collateral(self, collateral_address, user, amount):
        with boa.env.prank(user):
            mock_token.at(collateral_address).mint_amount(amount)
            mock_token.at(collateral_address).approve(self.dsc_engine.address, amount)
            self.dsc_engine.deposit_collateral(collateral_address, amount)


stablecoin_fuzzer = StablecoinFuzzer.TestCase
# stablecoin_fuzzer.settings = settings(max_examples=6, stateful_step_count=6)
