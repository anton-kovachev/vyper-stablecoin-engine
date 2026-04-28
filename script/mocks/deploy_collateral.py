from moccasin.boa_tools import VyperContract
from moccasin.config import get_active_network
from src.mocks import mock_token


def deploy_collateral() -> VyperContract:
    print("Deploying Mock Collateral Token...")
    mock_token_contract = mock_token.deploy()

    active_network = get_active_network()

    if (
        active_network.has_explorer()
        and not active_network.is_local_or_forked_network()
    ):
        active_network.moccasin_verify(mock_token_contract)

    print(
        "Mock Collateral Token deployed at...",
        mock_token_contract.address,
    )
    return mock_token_contract


def moccasin_main() -> VyperContract:
    return deploy_collateral()
