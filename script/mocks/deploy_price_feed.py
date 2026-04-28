from moccasin.boa_tools import VyperContract
from src.mocks import MockV3Aggregator

DECIMALS: int = 8
INITIAL_VALUE: int = 2000 * 10**DECIMALS


def deploy_price_feed() -> VyperContract:
    print("Deploying MockV3Aggregator...")
    mock_v3_aggregator_contract: VyperContract = MockV3Aggregator.deploy(
        DECIMALS, INITIAL_VALUE
    )
    print(
        "MockV3Aggregator deployed at...",
        mock_v3_aggregator_contract.address,
    )

    print("MockV3Aggregator deployed at...", mock_v3_aggregator_contract.address)
    return mock_v3_aggregator_contract


def moccasin_main() -> VyperContract:
    return deploy_price_feed()
