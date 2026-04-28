# 🪙 Decentralized Stablecoin Protocol (DSC)

<div align="center">

[![Vyper](https://img.shields.io/badge/Vyper-0.4.3-blue.svg)](https://docs.vyperlang.org/)
[![Moccasin](https://img.shields.io/badge/Moccasin-0.4.3-green.svg)](https://github.com/Cyfrin/moccasin)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*A fully decentralized, algorithmic, over-collateralized stablecoin system built with Vyper*

</div>

---

## 📖 Overview

The **Decentralized Stablecoin Protocol (DSC)** is a smart contract system that enables users to mint a USD-pegged stablecoin by depositing cryptocurrency collateral (WETH or WBTC). The protocol maintains price stability through over-collateralization and a robust liquidation mechanism.

### 💡 Business Case

Traditional stablecoins (like USDC or USDT) are centralized and require trust in a custodian. DSC solves this by creating a **trustless, decentralized alternative** where:

- **No Central Authority**: The protocol is entirely governed by smart contracts
- **Capital Efficiency**: Users can leverage their crypto holdings without selling
- **Price Stability**: Maintained through over-collateralization and liquidations
- **Transparency**: All operations are on-chain and auditable

### 🎯 Key Features

✅ **Over-Collateralized**: Requires 200% collateral ratio (users can borrow up to 50% of collateral value)  
✅ **Multi-Collateral**: Supports WETH and WBTC as collateral  
✅ **Liquidation System**: Protects protocol solvency with 10% liquidator incentive  
✅ **Price Oracles**: Integrates Chainlink price feeds for accurate valuation  
✅ **Health Factor**: Real-time monitoring of position safety with 18-decimal precision  
✅ **Gas Optimized**: Written in Vyper for efficient EVM execution

---

## 🏗️ Architecture

### Core Contracts

#### 1. **DecentralizedStableCoin** (`decentralized_stable_coin.vy`)
- ERC20 stablecoin token implementation
- Minting and burning controlled by DSC Engine
- Ownable with 2-step ownership transfer

#### 2. **DSCEngine** (`dsc_engine.vy`)
- Main protocol logic contract
- Handles collateral deposits/withdrawals
- Manages DSC minting/burning
- Implements liquidation mechanism
- Health factor calculations

### Protocol Mechanics

```
User Flow:
1. Deposit collateral (WETH/WBTC) → 2. Mint DSC (up to 50% of collateral value)
3. Health Factor = (Collateral × 0.5 × Price) / DSC Minted
4. If Health Factor < 1.0 → Position can be liquidated

Liquidation Flow:
1. Liquidator identifies unhealthy position (HF < 1.0)
2. Liquidator burns DSC to cover user's debt
3. Liquidator receives 110% collateral value (10% bonus)
4. Protocol remains solvent
```

### Economic Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Liquidation Threshold** | 50% | Users can borrow 50% of collateral value |
| **Liquidation Bonus** | 10% | Extra collateral given to liquidators |
| **Minimum Health Factor** | 1.0 (1e18) | Below this = liquidatable |
| **Required Collateralization** | 200% | User level (110% protocol level) |
| **Precision** | 18 decimals | Fixed-point arithmetic precision |

---

## 🛠️ Technologies Used

### Smart Contract Development
- **[Vyper 0.4.3](https://docs.vyperlang.org/)**: Pythonic smart contract language
- **[Moccasin 0.4.3](https://github.com/Cyfrin/moccasin)**: Vyper development framework
- **[Titanoboa](https://github.com/vyperlang/titanoboa)**: Vyper testing and simulation engine

### Testing & Quality Assurance
- **[pytest](https://docs.pytest.org/)**: Unit testing framework
- **[Hypothesis](https://hypothesis.readthedocs.io/)**: Property-based fuzz testing
- **RuleBasedStateMachine**: Stateful fuzz testing for invariant verification

### External Integrations
- **[Chainlink Price Feeds](https://docs.chain.link/)**: Decentralized oracle network for ETH/USD and BTC/USD prices
- **[snekmate](https://github.com/pcaversaccio/snekmate)**: Vyper library for ERC20 and access control

### Deployment Networks
- **Anvil**: Local development (EVM)
- **Sepolia**: Ethereum testnet
- **zkSync Sepolia**: zkSync Era testnet

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **pip** package manager
- **Git** version control
- Basic understanding of:
  - Ethereum and smart contracts
  - Collateralized lending protocols
  - Command-line interface

---

## 🚀 Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/mox-stablecoin-cu.git
cd mox-stablecoin-cu
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Moccasin

```bash
pip install moccasin
```

### 4. Install Dependencies

```bash
mox install
```

This will install:
- `snekmate` library (ERC20, Ownable, etc.)
- All Python testing dependencies

### 5. Configuration

The project uses `moccasin.toml` for configuration. Key settings:

```toml
[project]
src = "src"                    # Smart contract source directory
out = "out"                    # Build output directory
dependencies = ["snekmate"]    # External dependencies

[networks.anvil]
url = "http://127.0.0.1:8545"
chain_id = 31337
```

### 6. Environment Variables (Optional)

Create a `.env` file for deployment:

```bash
# .env
PRIVATE_KEY=your_private_key_here
SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
```

⚠️ **Never commit your `.env` file!** It's already in `.gitignore`.

---

## 🧪 Testing

The project includes comprehensive test coverage with both unit and fuzz tests.

### Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── unit/
│   ├── test_dsc.py         # DecentralizedStableCoin tests
│   └── test_dsc_engine.py  # DSCEngine unit tests
└── fuzz/
    └── test_fuzz.py        # Hypothesis property-based tests
```

### Running Tests

#### Run All Tests
```bash
mox test
```

#### Run Unit Tests Only
```bash
mox test tests/unit
```

#### Run Fuzz Tests Only
```bash
mox test tests/fuzz
```

#### Run with Verbose Output
```bash
mox test -v
```

#### Run Specific Test File
```bash
mox test tests/unit/test_dsc_engine.py
```

### Testing Patterns

#### 1. **Unit Testing** (`pytest`)

Uses function-scoped and session-scoped fixtures:

```python
# Session-scoped: Deployed once for all tests
@pytest.fixture(scope="session")
def dsc_engine(weth, wbtc, eth_usd_price_feed, btc_usd_price_feed, dsc):
    return deploy_dsc_engine(weth, wbtc, eth_usd_price_feed, btc_usd_price_feed, dsc)

# Function-scoped: Fresh user for each test
@pytest.fixture(scope="function")
def user():
    return boa.env.generate_address()
```

**Example Test:**
```python
def test_deposit_collateral(dsc_engine, weth, user):
    """Test that users can deposit collateral"""
    amount = 10 * 10**18  # 10 WETH
    
    # Setup: Mint and approve
    weth.mint(user, amount, sender=user)
    weth.approve(dsc_engine.address, amount, sender=user)
    
    # Act: Deposit collateral
    dsc_engine.deposit_collateral(weth.address, amount, sender=user)
    
    # Assert: Check balance
    _, collateral_value = dsc_engine.get_account_information(user)
    assert collateral_value > 0
```

#### 2. **Fuzz Testing** (`Hypothesis`)

Uses `RuleBasedStateMachine` for stateful property testing:

```python
class StablecoinFuzzer(RuleBasedStateMachine):
    """Stateful fuzzer that tests protocol invariants"""
    
    @rule(amount=st.integers(min_value=1, max_value=1000))
    def mint_and_deposit_collateral(self, amount):
        """Deposit collateral and mint DSC"""
        # ... implementation ...
    
    @invariant()
    def check_collateralization(self):
        """Protocol must always be >= 110% collateralized"""
        total_dsc = self.dsc_engine.user_to_dsc_minted(self.user)
        total_collateral = self._get_account_collateral_value(self.user)
        
        assert total_collateral >= total_dsc * 110 // 100
```

**Run Extended Fuzz Tests:**
```bash
# Run with more examples for thorough testing
mox test tests/fuzz -v --hypothesis-max-examples=1000
```

#### 3. **Mock Contracts**

For isolated testing without external dependencies:

- `MockV3Aggregator.vy`: Simulates Chainlink price feeds
- `mock_token.vy`: Test ERC20 token

**Example: Price Manipulation**
```python
def test_liquidation_on_price_crash(dsc_engine, weth, price_feed):
    """Test liquidation when collateral price drops"""
    # Crash ETH price to $50
    price_feed.updateAnswer(50 * 10**8)
    
    # User should now be liquidatable
    health_factor = dsc_engine.health_factor(user)
    assert health_factor < 1 * 10**18
```

### Test Coverage Goals

- ✅ **Unit Tests**: Cover all individual functions
- ✅ **Integration Tests**: Test contract interactions
- ✅ **Fuzz Tests**: Verify protocol invariants under random inputs
- ✅ **Edge Cases**: Zero amounts, maximum values, liquidation thresholds

---

## 📦 Deployment

### Deploy to Local Anvil

1. Start Anvil (local EVM):
```bash
anvil
```

2. Deploy contracts:
```bash
mox run deploy
```

### Deploy to Sepolia Testnet

1. Ensure you have Sepolia ETH ([faucet](https://sepoliafaucet.com/))

2. Set environment variables:
```bash
export PRIVATE_KEY=your_private_key
```

3. Deploy:
```bash
mox run deploy --network sepolia
```

### Deployment Scripts

Located in `script/` directory:

- `deploy_dsc.py`: Deploys DecentralizedStableCoin
- `deploy_dsc_engine.py`: Deploys DSCEngine with collateral setup
- `deploy.py`: Master deployment script
- `mocks/`: Mock contract deployers for testing

---

## 📁 Project Structure

```
mox-stablecoin-cu/
├── src/                          # Smart contracts (Vyper)
│   ├── decentralized_stable_coin.vy   # ERC20 stablecoin
│   ├── dsc_engine.vy                  # Main protocol logic
│   ├── interfaces/                    # Contract interfaces
│   │   ├── AggregatorV3Interface.vyi  # Chainlink oracle
│   │   └── i_decentralized_stable_coin.vyi
│   └── mocks/                         # Mock contracts for testing
│       ├── MockV3Aggregator.vy
│       └── mock_token.vy
├── script/                       # Deployment scripts
│   ├── deploy.py
│   ├── deploy_dsc.py
│   ├── deploy_dsc_engine.py
│   └── mocks/
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── unit/                    # Unit tests
│   │   ├── test_dsc.py
│   │   └── test_dsc_engine.py
│   └── fuzz/                    # Fuzz tests
│       └── test_fuzz.py
├── lib/                          # Dependencies (snekmate)
├── out/                          # Compiled contracts (gitignored)
├── moccasin.toml                # Moccasin configuration
├── pyproject.toml               # Python project configuration
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

---

## 🔒 Security Considerations

### Known Security Features

1. **Checks-Effects-Interactions Pattern**: Prevents reentrancy
2. **Integer Overflow Protection**: Vyper's built-in safeguards
3. **Access Control**: Only DSCEngine can mint/burn DSC
4. **Health Factor Validation**: Prevents undercollateralized positions
5. **Price Oracle Integration**: Uses Chainlink for tamper-resistant prices

### Audit Status

⚠️ **This is an educational project and has NOT been audited.** Do not use in production with real funds.

### Recommendations for Production

- [ ] Professional smart contract audit
- [ ] Formal verification of critical functions
- [ ] Bug bounty program
- [ ] Multi-sig governance for parameter updates
- [ ] Emergency pause mechanism
- [ ] Time-lock for admin functions

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Write tests for all new features
- Follow Vyper style guide
- Add NatSpec documentation to all functions
- Ensure all tests pass before submitting PR
- Update README if adding new functionality

---

## 📚 Additional Resources

### Documentation
- [Vyper Documentation](https://docs.vyperlang.org/)
- [Moccasin Documentation](https://github.com/Cyfrin/moccasin)
- [Chainlink Price Feeds](https://docs.chain.link/data-feeds)
- [MakerDAO Whitepaper](https://makerdao.com/en/whitepaper/) (inspiration)

### Learning Materials
- [Cyfrin Updraft - Vyper Course](https://updraft.cyfrin.io/)
- [Understanding Collateralized Debt Positions](https://ethereum.org/en/defi/)
- [Property-Based Testing with Hypothesis](https://hypothesis.readthedocs.io/)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[Cyfrin](https://www.cyfrin.io/)**: For Moccasin framework and educational content
- **[snekmate](https://github.com/pcaversaccio/snekmate)**: Vyper smart contract library
- **[Chainlink](https://chain.link/)**: Decentralized oracle network
- **[MakerDAO](https://makerdao.com/)**: Pioneering the collateralized stablecoin model

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/mox-stablecoin-cu/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/mox-stablecoin-cu/discussions)

---

<div align="center">

**Built with ❤️ using Vyper and Moccasin**

⭐ Star this repo if you find it helpful!

</div>