# AlphaScan — Deployment Guide

## What Changed

### Production-Ready Docker Setup

**Fixed Dockerfile Issues:**
- ✅ Multi-stage build (frontend + backend in one image)
- ✅ Non-root user for security (`alphascan`)
- ✅ Health check endpoint configured
- ✅ Proper `EXPOSE 8000` directive
- ✅ Production-grade entrypoint script
- ✅ Optimized layer caching

**Cleaned Repository:**
- ❌ Removed `diagnose.py` (diagnostic script)
- ❌ Removed `diagnose_results.txt` (output file)
- ❌ Removed `live_test.py` (test script)
- ❌ Removed `live_test_results.txt` (output file)
- ❌ Removed all `__pycache__/*.pyc` files (7 files)

**New Files:**
- ✅ `.dockerignore` — Excludes unnecessary files from Docker build
- ✅ `requirements-prod.txt` — Production dependencies only (no pytest)
- ✅ `docker-compose.yml` — One-command deployment
- ✅ `entrypoint.sh` — Production startup script

**Frontend Updates:**
- ✅ Static export mode (`output: 'export'`)
- ✅ Served from FastAPI (single container, single port)
- ✅ API client updated for same-origin requests

---

## Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - CENSYS_PAT
# - GITHUB_TOKEN
# - MISTRAL_API_KEY
# - DISCORD_WEBHOOK_URL (optional)
# - ETHERSCAN_API_KEY (optional)
```

### 2. Deploy with Docker Compose (Recommended)
```bash
docker compose up -d
```

Access the application at: **http://localhost:8000**

### 3. Alternative: Manual Docker Build
```bash
# Build the image
docker build -t alphascan .

# Run the container
docker run -d \
  --name alphascan \
  --env-file .env \
  -p 8000:8000 \
  -v alphascan-data:/app/data \
  -v alphascan-exports:/app/exports \
  alphascan
```

---

## Architecture

The production Docker image is a **single container** that serves:
- **FastAPI backend** on port 8000 (API endpoints)
- **Next.js frontend** as static files (served by FastAPI)

This simplifies deployment while maintaining separation of concerns.

### Data Persistence

Two named volumes persist data across container restarts:
- `alphascan-data` — Scan results database
- `alphascan-exports` — Export files

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CENSYS_PAT` | Yes | — | Censys Platform API token |
| `GITHUB_TOKEN` | Yes | — | GitHub personal access token |
| `MISTRAL_API_KEY` | Yes | — | Mistral AI API key |
| `DISCORD_WEBHOOK_URL` | No | — | Discord webhook for alerts |
| `ETHERSCAN_API_KEY` | No | — | Etherscan API key |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `UVICORN_WORKERS` | No | `2` | Number of uvicorn worker processes |
| `SCAN_INTERVAL` | No | `300` | Seconds between scan cycles |

### Docker Compose Variables

Edit `docker-compose.yml` to customize:
- Port mapping (default: `8000:8000`)
- Worker count
- Volume names
- Restart policy

---

## Health Check

The container includes an automatic health check:
```bash
docker compose ps
# or
curl http://localhost:8000/health
```

---

## Logs

View container logs:
```bash
docker compose logs -f alphascan
```

---

## Stopping

```bash
docker compose down
```

To also remove persisted data:
```bash
docker compose down -v
```

---

## Development Mode

For local development without Docker:
```bash
# Backend
pip install -r requirements.txt
python main.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Troubleshooting

### Build Fails
- Ensure Docker is running: `docker ps`
- Check `.env` file exists and has required API keys
- Review build logs: `docker compose logs`

### Container Won't Start
- Check health check: `curl http://localhost:8000/health`
- Verify API keys in `.env`
- Check logs: `docker compose logs alphascan`

### Port Already in Use
Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Change 8080 to your preferred port
```

---

## Production Checklist

- [ ] Set strong API keys in `.env`
- [ ] Configure `LOG_LEVEL=WARNING` for production
- [ ] Set up log aggregation (e.g., CloudWatch, ELK)
- [ ] Enable TLS/SSL with reverse proxy (nginx, Traefik)
- [ ] Set up automated backups of `alphascan-data` volume
- [ ] Configure resource limits in `docker-compose.yml`
- [ ] Set up monitoring/alerting on health check failures
