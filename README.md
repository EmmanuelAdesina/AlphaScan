# APIS - Autonomous Parallel Intelligence Scanner

**APIS** (Autonomous Parallel Intelligence Scanner) is an AI-driven system that continuously scans the internet for exposed API keys, classifies them by type, validates them, and reports findings via Discord. The system is fully autonomous with self-improvement capabilities, capable of writing its own code to add new features and improve existing ones.

## 🚀 Features

- **Multi-source scanning**: Censys, GitHub, port scanning, and service discovery
- **AI-powered classification**: Uses Groq AI (with regex fallback) to identify key types
- **Self-improvement**: Generates, validates, and deploys its own code
- **Discord integration**: Real-time notifications and command support
- **Dockerized**: Easy deployment with multi-stage Docker build
- **Free-tier friendly**: Uses only free-tier external services
- **Security-focused**: No full key logging, non-root Docker user, rate limiting

## 📋 Requirements

- Python 3.10+
- API keys for: Censys, GitHub, Groq, Discord Webhook

## 🛠️ Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd apis

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env

# Build and run with Docker Compose
docker-compose up --build -d

# Check health
curl http://localhost:8000/health
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the application
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
| `SCAN_INTERVAL` | No | Scan interval in seconds (default: 300) |
| `MAX_KEYS_PER_REPORT` | No | Max keys per Discord report (default: 50) |
| `DEBUG` | No | Enable debug mode (default: false) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

## 📡 API Endpoints

### Status
- `GET /health` - Health check
- `GET /status` - Engine status
- `GET /config` - Configuration summary

### Scanning
- `POST /scan/start` - Start a scan
- `POST /scan/stop` - Stop the scan cycle
- `GET /scan/start` - Start scan (GET method)

### Results
- `GET /results` - Get scan results
- `GET /keys` - Get all discovered keys (masked)
- `GET /keys/{key_type}` - Get keys by type

### Self-Improvement
- `POST /self-improve` - Trigger self-improvement
- `GET /self-improve/metrics` - Get improvement metrics

### Scanners
- `GET /scanners` - List all scanners and status

### Discord Commands
- `POST /discord/command` - Process Discord commands (!status, !scan, !improve, !config)

## 🔑 Key Classification

APIS can identify and classify the following key types:

| Type | Pattern | Description |
|------|---------|-------------|
| `openai` | `sk-...` | OpenAI API key |
| `claude` | `sk-ant-...` | Anthropic/Claude API key |
| `aws` | `AKIA...` | AWS Access Key ID |
| `google` | `AIza...` | Google API key |
| `github` | `ghp_...` | GitHub token |
| `stripe_live` | `sk_live_...` | Stripe Live secret key |
| `stripe_test` | `sk_test_...` | Stripe Test secret key |
| `discord` | `xxx.xxx.xxx` | Discord bot token |
| `slack` | `xoxb-...` | Slack token |
| `mongodb` | `mongodb://...` | MongoDB connection string |
| `postgresql` | `postgresql://...` | PostgreSQL connection string |
| `mysql` | `mysql://...` | MySQL connection string |
| `generic` | Various | Generic API key patterns |

## 🤖 Self-Improvement System

APIS has a built-in self-improvement engine that can:

1. **Analyze metrics**: Reviews scan results, detection rates, and missed keys
2. **Generate code**: Writes Python code to add new features or improve existing ones
3. **Validate code**: Syntax checking, import verification, and security scanning
4. **Deploy code**: Writes code to disk and reloads modules dynamically
5. **Learn from results**: Tracks what works and adjusts priorities
6. **Communicate**: Sends updates via Discord and requests human input when needed

### Self-Improvement Commands

```bash
# Trigger self-improvement via API
curl -X POST http://localhost:8000/self-improve \
  -H "Content-Type: application/json" \
  -d '{"description": "Add support for detecting Slack tokens"}'

# Trigger via Discord
!improve Add support for detecting Slack tokens
```

### Example Self-Improvement Scenario

1. System finds 20 unclassified keys
2. Sends to Discord: "⚠️ Found 20 unclassified keys. Analyzing patterns..."
3. Identifies a pattern (e.g., "xoxb-" for Slack)
4. Sends: "💡 New key type discovered: Slack tokens"
5. Writes code to add Slack detection
6. Validates and deploys the update
7. Sends: "✅ Added Slack token detection. Next scan will include it."

## 🏗️ Architecture

```
apis/
├── api/                    # FastAPI REST API
│   ├── __init__.py
│   ├── routes.py           # API endpoints
│   ├── models.py           # Pydantic models
│   └── dependencies.py     # Shared dependencies
├── scanners/               # Scanner modules
│   ├── __init__.py
│   ├── base_scanner.py     # Abstract base class
│   ├── censys_scanner.py   # Censys API scanner
│   ├── github_scanner.py   # GitHub API scanner
│   └── port_scanner.py     # Port and service scanner
├── utils/                  # Utility modules
│   ├── __init__.py
│   ├── groq_parser.py      # AI-powered key extraction
│   ├── key_validator.py    # Key validation
│   ├── key_classifier.py   # Key classification (re-export)
│   └── discord_notifier.py # Discord notifications
├── self_improve/           # Self-improvement system
│   ├── __init__.py
│   ├── code_generator.py   # Code generation + SelfImprovementEngine
│   ├── metrics_analyzer.py # Metrics analysis
│   ├── auto_deploy.py      # Code deployment
│   └── knowledge_base.py   # Persistent knowledge base
├── core/                   # Core engine
│   ├── __init__.py
│   ├── engine.py           # Main engine orchestrator
│   └── scanner_manager.py  # Scanner management
├── config/                 # Configuration
│   ├── __init__.py
│   ├── settings.py         # Environment settings
│   └── patterns.py         # Key classification patterns
├── data/                   # Persistent data
│   ├── keys_history.json
│   ├── metrics.json
│   └── knowledge.db
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_scanners.py
│   └── test_validator.py
├── main.py                 # Entry point
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔒 Security Considerations

- **No full key logging**: Only first 6 characters are logged
- **Discord webhook URL**: Never exposed in logs
- **Non-root Docker user**: Container runs as non-root user
- **Rate limiting**: API endpoints are rate-limited
- **Input sanitization**: All user input is validated
- **Code validation**: Self-generated code is checked for dangerous patterns
- **Environment variables**: All API keys stored in environment variables only

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_validator.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## 📊 Discord Communication

### Status Updates
```
📡 APIS Status
- Cycle #42 completed in 142s
- Found 8 valid keys
- Next scan in 4m 58s
```

### Key Reports
```
🔑 APIS - API Keys Found

📊 Summary: 8 valid key(s)

OPENAI (3)
`sk-proj-abc123...`

AWS (2)
`AKIA1234567890...`

GITHUB (2)
`ghp_abcdef...`

STRIPE LIVE (1)
`sk_live_xyz...`
```

### Self-Improvement Updates
```
💡 System Improvement
✅ Identified: Many keys from port 11434 (Ollama)
⚙️ Generated: `ollama_scanner.py`
✅ Deployed successfully
Expected increase in key discovery: +37%
```

### Discord Commands
- `!status` - Current engine state
- `!scan` - Force immediate scan
- `!improve <description>` - Trigger self-improvement
- `!config` - Show current configuration

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

## 🔧 Troubleshooting

### Common Issues

1. **"Censys API credentials not configured"**
   - Ensure `CENSYS_API_ID` and `CENSYS_API_SECRET` are set in `.env`

2. **"GitHub token not configured"**
   - Ensure `GITHUB_TOKEN` is set in `.env`

3. **Discord notifications not working**
   - Verify `DISCORD_WEBHOOK_URL` is correct
   - Check that the webhook is still active

4. **Docker health check failing**
   - Ensure port 8000 is not already in use
   - Check container logs: `docker-compose logs apis`

5. **Groq API errors**
   - The system will fall back to regex classification if Groq fails
   - Verify `GROQ_API_KEY` is valid

### Log Locations

- Docker: `docker-compose logs -f`
- Local: Console output
- Data files: `data/` directory

## 📄 License

This project is provided for educational and security research purposes. Use responsibly and only on systems you own or have permission to scan.

## ⚠️ Disclaimer

- This tool is for authorized security testing only
- Do not use against systems without explicit permission
- The self-improvement system generates code that should be reviewed
- The developers are not responsible for misuse of this tool
