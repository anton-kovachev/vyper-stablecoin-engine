from src import decentralized_stable_coin 
from moccasin.boa_tools import VyperContract

def deploy() -> VyperContract:
    counter: VyperContract = decentralized_stable_coin.deploy()
    print("Starting count: ", counter.number())
    counter.increment()
    print("Ending count: ", counter.number())
    return counter

def moccasin_main() -> VyperContract:
    return deploy()
