from moccasin.boa_tools import VyperContract
from src import decentralized_stable_coin


def deploy_dsc() -> VyperContract:
    print("Deploying Decentralized Stable Coin...")
    decentralized_stable_coin_contract: VyperContract = (
        decentralized_stable_coin.deploy()
    )
    print(
        "Decentralized Stable Coin deployed at...",
        decentralized_stable_coin_contract.address,
    )

    return decentralized_stable_coin_contract


def moccasin_main() -> VyperContract:
    return deploy_dsc()
