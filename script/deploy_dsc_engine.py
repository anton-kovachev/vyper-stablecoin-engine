from moccasin.boa_tools import VyperContract
from moccasin.config import get_active_network, Address
from src import dsc_engine
from script.mocks.deploy_price_feed import deploy_price_feed


def deploy_dsc_engine(dsc_contract: VyperContract) -> VyperContract:
    print("Deploying Decentralized Stable Coin Engine...")
    active_network = get_active_network()
    # dsc_contract: VyperContract = active_network.manifest_named(
    #     "decentralized_stable_coin"
    # )

    weth_contract: VyperContract = active_network.manifest_named("weth")
    wbtc_contract: VyperContract = active_network.manifest_named("wbtc")

    eth_usd_price_feed_contract: VyperContract = active_network.manifest_named(
        "eth_usd_price_feed"
    )
    btc_usd_price_feed_contract: VyperContract = active_network.manifest_named(
        "btc_usd_price_feed"
    )

    dsc_engine_contract: VyperContract = dsc_engine.deploy(
        [weth_contract.address, wbtc_contract.address],
        [eth_usd_price_feed_contract.address, btc_usd_price_feed_contract.address],
        dsc_contract.address,
    )

    dsc_contract.set_minter(dsc_engine_contract.address, True)
    dsc_contract.transfer_ownership(dsc_engine_contract.address)
    print(
        "Decentralized Stable Coin Engine deployed at...",
        dsc_engine_contract.address,
    )

    return dsc_engine_contract


def moccasin_main() -> VyperContract:
    active_network = get_active_network()
    dsc_contract: VyperContract = active_network.manifest_named(
        "decentralized_stable_coin"
    )
    return deploy_dsc_engine(dsc_contract)
