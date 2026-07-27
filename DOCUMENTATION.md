# AlphaScan Documentation

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Module Reference](#module-reference)
- [Discord Integration](#discord-integration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

AlphaScan is a secret scanning and key intelligence system that:
1. Scans public sources (Censys, GitHub, Pastebin) for exposed credentials
2. Uses LLM (Mistral AI) and regex to extract keys from raw text
3. Validates extracted keys through a three-layer validation pipeline
4. Sends ranked reports to Discord with severity levels (0-10)

### Key Features
- **Multi-source scanning**: Censys, GitHub, Pastebin
- **LLM-powered extraction**: Mistral AI for intelligent key extraction
- **Three-layer validation**: Format, entropy, Etherscan balance check
- **Discord reporting**: Ranked reports (0=critical, 10=lowest)
- **Pre-scan verification**: Validates API keys before startup
- **Quiet mode**: Suppresses INFO logs for production

---

## Architecture

```
AlphaScan/
  main.py              - CLI entry point, starts FastAPI server
  config.py            - Environment variables and settings
  censys_client.py     - Censys Platform API v3 client (PAT auth)
  scanner.py            - Scan implementations (Censys, GitHub, Pastebin)
  parser.py            - Key extraction (Mistral LLM + regex)
  validator.py         - Three-layer key validation
  reporter.py          - Discord webhook reporting
  utils/
    __init__.py        - Package marker
    config_validator.py - Config validation and warnings
    api_verifier.py    - Pre-scan API key verification
  api/
    __init__.py        - Package marker
    routes.py          - FastAPI routes (/health, /)
```

### Data Flow

```
[Scan Sources] → [Raw Text] → [Parser] → [Keys] → [Validator] → [Validated Keys] → [Reporter] → Discord
```

---

## Installation

### Prerequisites
- Python 3.11+
- pip
- API keys (see Configuration)

### Steps

```bash
git clone https://github.com/EmmanuelAdesina/AlphaScan.git
cd AlphaScan
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

---

## Configuration

All configuration is done through environment variables in `.env`.

### Required API Keys

| Variable | Service | Purpose | Get It From |
|----------|---------|---------|-------------|
| `CENSYS_PAT` | Censys | Scan for exposed services | https://console.censys.io/api |
| `GITHUB_TOKEN` | GitHub | Search public repos | https://github.com/settings/tokens |
| `MISTRAL_API_KEY` | Mistral | LLM key extraction | https://console.mistral.ai/api-keys |
| `DISCORD_WEBHOOK_URL` | Discord | Send reports | Discord channel settings |
| `ETHERSCAN_API_KEY` | Etherscan | Check wallet balances | https://etherscan.io/myapikey |

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable uvicorn reload |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `QUIET_MODE` | `false` | Suppress INFO logs |
| `SCAN_INTERVAL` | `300` | Seconds between scans |
| `MAX_KEYS_PER_REPORT` | `50` | Max keys per Discord message |

### Custom Queries

| Variable | Default |
|----------|---------|
| `CENSYS_QUERY` | `"http.api.key" OR "api_key" OR ...` |
| `GITHUB_SEARCH_QUERY` | `filename:.env OR ...` |

### Example `.env`

```env
CENSYS_PAT=censys_xxx
GITHUB_TOKEN=ghp_xxx
MISTRAL_API_KEY=xxx
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx
ETHERSCAN_API_KEY=xxx
SCAN_INTERVAL=300
MAX_KEYS_PER_REPORT=50
```

---

## Usage

### Start Server

```bash
python main.py
```

This starts the FastAPI server on `http://0.0.0.0:8000`. The server runs continuously.

### CLI Flags

| Flag | Description |
|------|-------------|
| `--quiet` | Suppress INFO logs, only show warnings/errors |
| `--no-verify` | Skip pre-scan API key verification |
| `--once` | Run single scan cycle and exit |
| `--no-report` | Skip Discord reporting |

### Examples

```bash
# Quiet mode (production)
python main.py --quiet

# Skip verification (for testing)
python main.py --no-verify

# Run once with reporting
python main.py --once --no-report

# Full quiet run
python main.py --quiet --once --no-report
```

### Docker Build

The production image uses a multi-stage build. The first stage creates a static Next.js export; the second stage runs FastAPI and serves that export from `/static`. Build from the repository root because the Dockerfile copies `frontend/` into the Node builder stage.

It requires:

- `requirements-prod.txt` (production dependencies only)
- `frontend/package.json` and `frontend/package-lock.json`
- `.env` file with valid API keys (or runtime `-e` variables)
- `PORT=8000` for this deployment (the image defaults to 8000)

Build:

```bash
docker build -t alphascan:latest .
```

> Note: If `CENSYS_PAT`, `GITHUB_TOKEN`, or `MISTRAL_API_KEY` is missing, invalid, or expired, the container will exit with an error like `❌ Censys PAT is invalid or expired.` Ensure `.env` is configured before running.

Run with `.env`:

```bash
docker run --rm --env-file .env -p 8000:8000 alphascan:latest
```

Run continuously:

```bash
docker run -d --name alphascan --env-file .env -p 8000:8000 alphascan:latest
```

---

## How It Works

### 1. Pre-Scan Verification

Before starting, AlphaScan verifies all configured API keys:
- Censys: Validates PAT with a lightweight search
- GitHub: Validates token with `/user` endpoint
- Mistral: Validates API key with a test completion
- Discord: Validates webhook with a test message

If any critical key fails verification, startup aborts with an error message.

### 2. Configuration Validation

Non-network checks:
- `.env` file exists
- API keys are configured
- Settings are within reasonable ranges

Logs warnings but does not abort.

### 3. Scanning Phase

Three scanners run in parallel:

#### Censys Scanner
- Uses Censys Platform API v3
- Searches for services exposing potential secrets
- Returns HTTP response bodies and service metadata

#### GitHub Scanner
- Searches code via GitHub Code Search API
- Fetches raw file contents for matches
- Targets `.env`, `config.py`, `settings.py`, JSON files

#### Pastebin Scanner
- Scrapes Pastebin archive for recent pastes
- Fetches raw paste contents
- Returns text from first 15 pastes

### 4. Parsing Phase (Key Extraction)

Two extraction methods:

#### Mistral LLM Extraction
- Sends raw text to Mistral API
- Prompt asks for JSON array of extracted keys
- Fallback to regex on failure

#### Regex Extraction
- Pattern matching against known key formats
- SSH keys, crypto keys, API keys, connection strings
- Generic patterns for unrecognized formats

**Extracted key object:**
```python
{
    "type": "eth_private_key",
    "value": "0xabc123...",
    "rank": 2,
    "source": "regex"  # or "mistral"
}
```

### 5. Validation Phase (Three-Layer)

#### Layer 1: Format Validation
- Minimum length check per key type
- Prefix validation (e.g., `sk-`, `AKIA`, `ghp_`)
- SSH key structure (`-----BEGIN` / `-----END`)
- Ethereum hex format validation

#### Layer 2: Entropy Analysis
- Calculates Shannon entropy
- Categories: high (>=4.0), medium (>=3.0), low_medium (>=1.5), low (<1.5)
- Advisory only — format-valid keys pass regardless

#### Layer 3: Etherscan Balance Check
- Derives Ethereum address from private key
- Queries Etherscan for wallet balance
- Marks keys with funds as highest priority

**Validated key object:**
```python
{
    "type": "eth_private_key",
    "value": "0xabc123...",
    "rank": 2,
    "valid": True,
    "format_valid": True,
    "format_reason": "format OK",
    "entropy": 5.2,
    "entropy_category": "high",
    "wallet_address": "0xdef456...",
    "wallet_balance_eth": 1.5,
    "wallet_has_funds": True,
    "validation_summary": "PASSED (wallet: 1.5000 ETH)"
}
```

### 6. Reporting Phase (Discord)

Keys are grouped by rank (0=most critical) and sent to Discord:

- **Embeds**: One embed per rank group
- **Fields**: Masked key value, entropy, balance, validation status
- **Limits**: 20 fields per embed, 10 embeds per webhook
- **Masking**: Shows first/last chars, hides middle

---

## Module Reference

### main.py
Entry point. Parses CLI args, verifies config, starts uvicorn.

### config.py
Loads environment variables. Exposes:
- API credentials (`CENSYS_PAT`, `GITHUB_TOKEN`, etc.)
- App settings (`DEBUG`, `LOG_LEVEL`, `QUIET_MODE`)
- Scan settings (`SCAN_INTERVAL`, `MAX_KEYS_PER_REPORT`)
- Query templates (`CENSYS_QUERY`, `GITHUB_SEARCH_QUERY`)

### utils/config_validator.py
`ConfigValidator` class:
- `validate_all()`: Returns `{"errors": [], "warnings": [], "info": []}`
- `log_report()`: Logs validation findings

### utils/api_verifier.py
API key verification functions:
- `verify_censys(pat) -> bool`
- `verify_github(token) -> bool`
- `verify_mistral(api_key) -> bool`
- `verify_discord(webhook_url) -> bool`
- `verify_all_api_keys() -> VerificationResult`
- `should_abort_scan(result) -> bool`

### censys_client.py
`CensysClient` class:
- `search_hosts(query, per_page) -> List[Dict]`
- `get_host(ip) -> Dict`
- `verify_auth() -> bool`

Exceptions:
- `CensysError`, `CensysAuthError`, `CensysPermissionError`, `CensysNotFound`

### scanner.py
Scan functions:
- `scan_censys() -> List[str]`
- `scan_github() -> List[str]`
- `scan_pastebin() -> List[str]`
- `run_all_scanners() -> List[str]`

### parser.py
Key extraction:
- `extract_with_regex(text) -> List[Dict]`
- `extract_with_mistral(texts) -> List[Dict]`
- `extract_keys(texts) -> List[Dict]`

Regex patterns defined at module level.

### validator.py
Validation:
- `check_format(key) -> Tuple[bool, str]`
- `check_entropy(key) -> Tuple[bool, float, str]`
- `derive_address_from_private_key(pk) -> Optional[str]`
- `check_etherscan_balance(addr) -> Optional[Dict]`
- `validate_key(key) -> Dict`
- `validate_keys(keys) -> List[Dict]`

### reporter.py
Discord reporting:
- `send_discord(content, embeds) -> bool`
- `send_status(cycle, duration, keys_found, scanners_used) -> bool`
- `send_key_report(keys) -> bool`
- `send_error(error, context) -> bool`
- `send_info(message) -> bool`

---

## Discord Integration

### Webhook Format

Messages include:
- Summary line with counts
- Embeds grouped by rank
- Masked key values for safety
- Validation status and entropy
- Wallet balances (if available)

### Rank Table

| Rank | Category | Color |
|------|----------|-------|
| 0 | SSH Private Keys | 🔴 Red |
| 1 | Crypto Exchange Keys | 🟠 Orange |
| 2 | Wallet Private Keys | 🟠 Dark Orange |
| 3 | Hot Wallet Server Keys | 🟡 Orange |
| 4 | DeFi Protocol Admin Keys | 🟡 Gold |
| 5 | RPC Provider Keys | 🟣 Purple |
| 6 | Smart Contract Deployment Keys | 🟣 Medium Purple |
| 7 | Cloud Provider Keys | 🔵 Blue |
| 8 | Payment Processor Keys | 🟢 Green |
| 9 | AI Provider Keys | 🟢 Cyan |
| 10 | Dev Platform Keys | 🔵 Discord Blurple |

### Field Limits
- 20 fields per embed
- 10 embeds per webhook
- Keys limited to `MAX_KEYS_PER_REPORT`

---

## Testing

### Live Test

```bash
python live_test.py
```

Tests all endpoints:
1. Censys API (PAT auth)
2. GitHub Code Search
3. Mistral LLM
4. Discord Webhook
5. Etherscan API

Results written to `live_test_results.txt`.

### Diagnostics

```bash
python diagnose.py
```

Deep diagnostic of all endpoints with detailed error messages.
Writes results to `diagnose_results.txt`.

### Import Test

```bash
python -c "from main import *; print('OK')"
```

---

## Troubleshooting

### Censys 401 Unauthorized
- PAT is invalid or expired
- Generate new PAT at https://console.censys.io/api

### GitHub 403 Rate Limited
- Too many requests
- Wait or use authenticated requests with valid token

### Mistral API Failure
- Verify API key at https://console.mistral.ai/api-keys
- Check API status at https://status.mistral.ai

### Discord 404 Webhook Not Found
- Webhook URL is invalid or deleted
- Recreate webhook in Discord channel settings

### Discord 429 Rate Limited
- Too many messages
- Reduce `MAX_KEYS_PER_REPORT` or increase scan interval

### Etherscan Errors
- Free tier has rate limits (5 calls/sec)
- Verify API key at https://etherscan.io/myapikey

### Module Import Errors
- Ensure running from project root
- Check `PYTHONPATH` includes current directory
- Verify `utils/` and `api/` directories exist

---

## License

MIT