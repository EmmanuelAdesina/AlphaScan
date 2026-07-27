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

### Build (Multi-stage build serving both Frontend and Backend)

```bash
docker build -t alphascan:latest .
```

> Note: Build from the repository root. The production image uses `requirements-prod.txt` (no test dependencies), compiles the Next.js frontend into a static export, and serves it through FastAPI. The frontend dashboard is available at `/`. The application listens on `PORT=8000` by default.

### Configure Environment

Before running, create `.env` from the template:

```bash
cp .env.example .env
# Edit .env with your real API keys
```

If any required key (`CENSYS_PAT`, `GITHUB_TOKEN`, `MISTRAL_API_KEY`) is missing or invalid, the container will exit with an error like:

```
❌ Censys PAT is invalid or expired.
```

### Run

Single scan with `.env` file:

```bash
docker run --rm --env-file .env -p 8000:8000 alphascan:latest
```

Continuous (with `.env`):

```bash
docker run -d --name alphascan --env-file .env -p 8000:8000 alphascan:latest
```

Pass secrets at runtime (alternative to `.env`):

```bash
docker run --rm \
  -e CENSYS_PAT=your_pat \
  -e GITHUB_TOKEN=your_token \
  -e MISTRAL_API_KEY=your_key \
  -e DISCORD_WEBHOOK_URL=your_webhook \
  alphascan:latest
```

### Docker Compose

```bash
docker compose up -d
```

Requires `.env` at the repo root with valid API keys.

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

**Docker build fails**: Build from the repository root so the Docker build context contains both `Dockerfile` and `frontend/`:

```bash
docker build -t alphascan:latest .
```

**Remote server cannot reach the app**: Set `PORT=8000`, publish `8000:8000`, and ensure the cloud firewall/security group allows inbound TCP port 8000.

## License

MIT