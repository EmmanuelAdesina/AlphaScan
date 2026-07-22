# AlphaScan v0.5 - Complete Secret Intelligence System

**AlphaScan** (Autonomous Parallel Intelligence Scanner) is an AI-driven system that continuously scans the internet for exposed API keys, SSH private keys, and cryptocurrency keys. It classifies, verifies, and reports all discovered secrets with a comprehensive 0-10 ranking system. The system is fully autonomous with self-improvement capabilities, capable of writing its own code, managing its environment, and pushing to GitHub.

## 🚀 v0.5 New Features

### 🔐 Secret Intelligence System
- **SSH Private Key Detection (Rank 0)** - Detects OpenSSH, RSA, DSA, EC private keys with MD5 fingerprint generation, encryption status detection, and permission context analysis
- **Crypto Key Detection (Rank 1-6)** - Detects Ethereum/BSC private keys, Bitcoin WIF keys, Solana keys, BIP39 seed phrases, and exchange API keys with wallet balance checks via Etherscan (read-only)
- **API Key Detection (Rank 7-10)** - Detects cloud provider keys (AWS, GCP, Azure), payment processors (Stripe, PayPal), AI providers (OpenAI, Claude), and development platform keys (GitHub, GitLab)

### 🧠 Smart Verification Pipeline
Three-layer verification ensures only valid secrets are reported:
1. **Format Validation** - Structure, length, pattern matching
2. **Entropy Analysis** - Randomness measurement (Shannon entropy)
3. **Context Analysis** - Production vs test environment, permission levels

### 📊 Complete Ranking System (0-10)
| Rank | Category | Examples |
|------|----------|----------|
| **0** | SSH Private Keys | OpenSSH, RSA, DSA, EC |
| **1** | Crypto Exchange Keys | Binance, Coinbase, Kraken |
| **2** | Wallet Private Keys | ETH, BTC, BSC, Seed Phrases |
| **3** | Hot Wallet Keys | Exchange/project wallets |
| **4** | DeFi Admin Keys | Multisig, Deployer keys |
| **5** | RPC Provider Keys | Alchemy, Infura |
| **6** | Smart Contract Keys | Deployer keys |
| **7** | Cloud Provider Keys | AWS, GCP, Azure |
| **8** | Payment Processors | Stripe, PayPal |
| **9** | AI Provider Keys | OpenAI, Claude |
| **10** | Dev Platform Keys | GitHub, GitLab |

### 🤖 Autonomous System
- **Environment Management** - Auto-detects missing API keys, requests them via Discord, updates .env file
- **Strategy Analysis** - ROI-based pivoting between scanning sources
- **Git Management** - Autonomous commit, push, sync, and rollback
- **Command Handler** - Full Discord command system (!status, !scan, !config, !push, !rollback, !help, etc.)
- **Decision Logging** - Complete audit trail of all autonomous decisions

### 📡 New Scanners
- **Pastebin Scanner** - Scans public pastes for secrets
- **Telegram Scanner** - Scans public Telegram channels for secrets

### 📋 Clean Discord Reports
Classified, ranked, and prioritized reports with:
- Summary statistics by rank group
- Detailed key information (fingerprint, permissions, format, size)
- Production environment detection
- Wallet balance information (for crypto keys)

## 🛠️ Installation

### Option 1: Docker (Recommended)
```bash
git clone <repo-url>
cd AlphaScan
cp .env.example .env
nano .env  # Fill in your API keys
docker-compose up --build -d
curl http://localhost:8000/health
```

### Option 2: Local Development
```bash
pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CENSYS_API_ID` | Yes | Censys API ID |
| `CENSYS_API_SECRET` | Yes | Censys API Secret |
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token |
| `GROQ_API_KEY` | Yes | Groq AI API Key |
| `DISCORD_WEBHOOK_URL` | Yes | Discord Webhook URL |
| `AUTONOMOUS_MODE` | No | Enable autonomous mode (default: true) |
| `AUTO_PUSH_GITHUB` | No | Auto-push to GitHub (default: true) |
| `ENABLE_SSH_DETECTION` | No | Enable SSH key detection (default: true) |
| `ENABLE_CRYPTO_DETECTION` | No | Enable crypto key detection (default: true) |
| `ENABLE_API_DETECTION` | No | Enable API key detection (default: true) |
| `VERIFICATION_TIMEOUT` | No | Verification timeout in seconds (default: 5) |
| `ETHERSCAN_API_KEY` | No | Etherscan API key for balance checks |

## 📡 API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /status` - Engine status
- `GET /config` - Configuration summary
- `GET /autonomous/status` - Autonomous system status

### Scanning
- `POST /scan/start` - Start a scan
- `POST /scan/stop` - Stop the scan cycle
- `GET /scan/start` - Start scan (GET method)

### Results & Keys
- `GET /results` - Get scan results
- `GET /keys` - Get all discovered keys (masked)
- `GET /keys/{key_type}` - Get keys by type
- `GET /keys/rank/{rank}` - Get keys by rank (0-10)

### Verification
- `GET /verification/stats` - Verification statistics

### Self-Improvement
- `POST /self-improve` - Trigger self-improvement
- `GET /self-improve/metrics` - Get improvement metrics

### Autonomous
- `GET /autonomous/decisions` - Get decision log

### Discord Commands
- `POST /discord/command` - Process Discord commands

## 🤖 Discord Commands

| Command | Action |
|---------|--------|
| `!status` | Show current scan state, keys found, uptime |
| `!approve-pivot` | Approve strategy pivot |
| `!deny-pivot` | Reject strategy pivot |
| `!approve-feature` | Approve new feature addition |
| `!deny-feature` | Reject new feature addition |
| `!config` | Show current configuration |
| `!restart` | Restart the system |
| `!push` | Force push to GitHub |
| `!rollback [hash]` | Rollback last change |
| `!logs` | Show recent logs |
| `!help` | Show available commands |
| `!provide-key <KEY> <value>` | Provide API key via Discord |
| `!improve <description>` | Trigger self-improvement |
| `!scan` | Force immediate scan |

## 🔑 Key Classification

AlphaScan can identify and classify the following key types:

### SSH Keys (Rank 0)
- OpenSSH Private Key
- RSA Private Key
- DSA Private Key
- EC Private Key
- SSH Public Keys (RSA, ECDSA, ED25519)

### Crypto Keys (Rank 1-6)
- Ethereum/BSC Private Keys
- Bitcoin WIF Private Keys
- Solana Private Keys
- BIP39 Seed Phrases (12-24 words)
- Exchange API Keys (Binance, Coinbase, Kraken)
- RPC Provider Keys (Alchemy, Infura)
- DeFi Admin Keys (Multisig, Deployer)

### API Keys (Rank 7-10)
- Cloud: AWS, GCP, Azure
- Payment: Stripe, PayPal
- AI: OpenAI, Claude, Google AI
- Dev: GitHub, GitLab, Slack, Discord
- Database: MongoDB, Supabase, Firebase
- Email/SMS: Twilio, SendGrid, Mailgun

## 🏗️ Architecture

```
AlphaScan/
├── verification/              # v0.5: Secret verification system
│   ├── verifier.py            # Core 3-layer verification pipeline
│   ├── key_rank.py            # Rank 0-10 classification
│   ├── ssh_intelligence.py    # SSH key detection
│   ├── crypto_intelligence.py # Crypto key detection
│   ├── api_intelligence.py    # API key detection
│   ├── discord_reporter.py    # Clean classified reports
│   └── verifiers/
│       ├── ssh_verifier.py
│       ├── crypto_verifier.py
│       └── api_verifier.py
├── autonomous/                # v0.5: True autonomy
│   ├── env_manager.py         # Auto-request API keys
│   ├── strategy_analyzer.py   # ROI-based pivoting
│   ├── git_manager.py         # Auto-push to GitHub
│   ├── command_handler.py     # Discord commands
│   ├── module_registry.py     # Dynamic module management
│   └── decision_logger.py     # Audit trail
├── scanners/                  # Scanner modules
│   ├── base_scanner.py
│   ├── censys_scanner.py
│   ├── github_scanner.py
│   ├── port_scanner.py
│   ├── pastebin_scanner.py    # v0.5: NEW
│   └── telegram_scanner.py    # v0.5: NEW
├── self_improve/              # Self-improvement system
│   ├── code_generator.py
│   ├── metrics_analyzer.py
│   ├── auto_deploy.py
│   └── knowledge_base.py
├── core/                      # Core engine
│   ├── engine.py              # v0.5: Autonomous loop
│   └── scanner_manager.py
├── config/
│   ├── settings.py            # v0.5: New config vars
│   └── patterns.py            # v0.5: All key patterns
├── api/                       # FastAPI REST API
├── utils/                     # Utility modules
├── data/                      # Persistent data
│   ├── verified_keys/         # v0.5: Verified keys storage
│   └── decisions.log          # v0.5: Decision log
├── tests/                     # Test suite
│   ├── test_scanners.py
│   ├── test_validator.py
│   └── test_v05_features.py   # v0.5: Comprehensive tests
├── main.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run v0.5 feature tests
pytest tests/test_v05_features.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## 🐳 Docker Deployment

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Health check
curl http://localhost:8000/health
```

## 🔒 Security Considerations

- **No full key logging**: Only first 6 characters are logged
- **Passive verification only**: SSH keys are never used, crypto balance checks are read-only
- **Discord webhook URL**: Never exposed in logs
- **Non-root Docker user**: Container runs as non-root user
- **Rate limiting**: API endpoints are rate-limited
- **Input sanitization**: All user input is validated
- **Code validation**: Self-generated code is checked for dangerous patterns
- **Environment variables**: All API keys stored in environment variables only

## 📄 License

This project is provided for educational and security research purposes. Use responsibly and only on systems you own or have permission to scan.

## ⚠️ Disclaimer

- This tool is for authorized security testing only
- Do not use against systems without explicit permission
- The self-improvement system generates code that should be reviewed
- The developers are not responsible for misuse of this tool
