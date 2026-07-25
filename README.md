# AlphaScan

Secret scanning & key intelligence system. Scans public sources for exposed API keys, private keys, and credentials, then validates and reports them.

## Features

- **Multi-source scanning**: Censys, GitHub, Pastebin
- **LLM-powered extraction**: Mistral AI for intelligent key extraction
- **Three-layer validation**: Format check, entropy analysis, Etherscan balance check
- **Discord reporting**: Ranked reports with severity levels (0-10)
- **Docker ready**: Multi-stage production build

## Quick Start

### Prerequisites

- Python 3.11+
- API keys for: Censys (PAT), GitHub, Mistral AI, Discord (webhook), Etherscan (optional)

### Installation

```bash
git clone https://github.com/EmmanuelAdesina/AlphaScan.git
cd AlphaScan
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
CENSYS_PAT=your_censys_pat
GITHUB_TOKEN=your_github_token
MISTRAL_API_KEY=your_mistral_api_key
DISCORD_WEBHOOK_URL=your_discord_webhook
ETHERSCAN_API_KEY=your_etherscan_key  # optional
SCAN_INTERVAL=300
MAX_KEYS_PER_REPORT=50
```

### Usage

Run a single scan cycle:

```bash
python main.py
```

Continuous scanning (every 5 minutes):

```bash
python main.py --quiet
```

Skip API verification (not recommended):

```bash
python main.py --no-verify
```

## Docker

Build the production image:

```bash
docker build -f Dockerfile -t alphascan:latest .
```

Run a single scan:

```bash
docker run --rm alphascan:latest
```

Run continuously:

```bash
docker run -d --name alphascan alphascan:latest
```

Pass secrets at runtime:

```bash
docker run -e CENSYS_PAT=your_pat \
  -e GITHUB_TOKEN=your_token \
  -e MISTRAL_API_KEY=your_key \
  -e DISCORD_WEBHOOK_URL=your_webhook \
  alphascan:latest
```

## Architecture

```
AlphaScan/
  main.py           - Entry point, FastAPI server startup
  config.py         - Environment configuration
  scanners.py       - Censys, GitHub, Pastebin scanners
  parser.py         - Mistral LLM + regex key extraction
  validator.py      - Format, entropy, Etherscan validation
  reporter.py       - Discord webhook reporting
  censys_client.py  - Censys Platform API client (PAT auth)
  utils/            - Utility modules (config_validator, api_verifier)
  api/              - FastAPI routes
```

## How It Works

1. **Scan**: Query Censys, GitHub, and Pastebin for raw text containing potential secrets
2. **Parse**: Use Mistral LLM to extract keys from raw text, with regex fallback
3. **Validate**: Three-layer validation:
   - Format check (prefix, length, structure)
   - Entropy analysis
   - Etherscan balance check (for Ethereum keys)
4. **Report**: Send ranked findings to Discord

## Key Ranking

| Rank | Type |
|------|------|
| 0 | SSH Private Keys |
| 1 | Crypto Exchange Keys |
| 2 | Wallet Private Keys |
| 3 | Hot Wallet Server Keys |
| 4 | DeFi Protocol Admin Keys |
| 5 | RPC Provider Keys |
| 6 | Cloud Provider Keys |
| 7 | Smart Contract Deployment Keys |
| 8 | Payment Processor Keys |
| 9 | AI Provider Keys |
| 10 | Dev Platform Keys |

## API Endpoints

- **Censys**: `https://search.censys.io/api/v2` (PAT auth)
- **GitHub**: `https://api.github.com/search/code`
- **Mistral**: `https://api.mistral.ai/v1/chat/completions`
- **Discord**: Webhook URL
- **Etherscan**: `https://api.etherscan.io/v2/api`

## Testing

Run live endpoint verification:

```bash
python live_test.py
```

Run diagnostics:

```bash
python diagnose.py
```

## Troubleshooting

**Censys 401 Unauthorized**: Your PAT is expired. Generate a new one at https://console.censys.io/api

**Mistral module not found**: Install dependencies: `pip install -r requirements.txt`

**Docker build fails**: Ensure Dockerfile is at the repo root. The build context is `/build`.

## License

MIT