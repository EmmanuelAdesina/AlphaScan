"""
AlphaScan - Deep diagnostic of all failing endpoints
Writes results to diagnose_results.txt
"""
import requests, json, os, sys, inspect
from dotenv import load_dotenv

os.chdir(os.path.dirname(__file__) or ".")
load_dotenv()

logfile = "diagnose_results.txt"
log = open(logfile, "w", encoding="utf-8")

def p(s=""):
    print(s)
    log.write(s + "\n")
    log.flush()

p("=" * 70)
p("  AlphaScan - Deep Endpoint Diagnosis")
p("=" * 70)
p()

# ── 1. CENSYS ──
p("[1] CENSYS - 401 Unauthorized")
cid = os.getenv("CENSYS_API_ID")
csec = os.getenv("CENSYS_API_SECRET")
p(f"  API ID:    {cid}")
p(f"  Secret:    {csec[:8]}...{csec[-4:]} (len={len(csec)})")

# Try different auth methods
p("  Trying basic auth (requests default)...")
r = requests.get("https://search.censys.io/api/v2/hosts/search",
    auth=(cid, csec), params={"q": "api_key", "per_page": 1}, timeout=15)
p(f"    Status: {r.status_code}")
p(f"    Body:   {r.text[:200]}")

# Check if credentials are expired by trying the /account endpoint
p("  Checking /account endpoint...")
r2 = requests.get("https://search.censys.io/api/v2/account",
    auth=(cid, csec), timeout=15)
p(f"    Status: {r2.status_code}")
p(f"    Body:   {r2.text[:200]}")
p()

# ── 2. GITHUB - already working, just confirm
p("[2] GITHUB - Already PASSED (200, 39,912 results)")
p()

# ── 3. GROQ ──
p("[3] GROQ - Library version mismatch")
gk = os.getenv("GROQ_API_KEY")
p(f"  API Key:   {gk[:8]}...{gk[-4:]} (len={len(gk)})")

# Check groq version
try:
    import groq
    p(f"  groq version: {groq.__version__}")
except:
    p("  groq not importable")

# Try direct REST API call (bypasses library)
p("  Direct REST API call...")
try:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {gk}",
            "Content-Type": "application/json",
        },
        json={
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": "Reply with just the word OK"}],
            "max_tokens": 5,
            "temperature": 0.1,
        },
        timeout=15,
    )
    p(f"    Status: {r.status_code}")
    p(f"    Body:   {r.text[:300]}")
except Exception as e:
    p(f"    ERROR:  {e}")
p()

# ── 4. DISCORD - already working
p("[4] DISCORD - Already PASSED (204)")
p()

# ── 5. ETHERSCAN ──
p("[5] ETHERSCAN - V1 deprecated, need V2")
ek = os.getenv("ETHERSCAN_API_KEY")
p(f"  API Key:   {ek[:8]}...{ek[-4:]} (len={len(ek)})")

# Try V2 endpoint
p("  Trying V2 endpoint (api.etherscan.io/v2/api)...")
try:
    r = requests.get("https://api.etherscan.io/v2/api", params={
        "chainid": 1,
        "module": "account",
        "action": "balance",
        "address": "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
        "tag": "latest",
        "apikey": ek,
    }, timeout=10)
    p(f"    Status: {r.status_code}")
    p(f"    Body:   {r.text[:300]}")
except Exception as e:
    p(f"    ERROR:  {e}")

# Try V1 with explicit chainid
p("  Trying V1 with chainid param...")
try:
    r = requests.get("https://api.etherscan.io/api", params={
        "chainid": 1,
        "module": "account",
        "action": "balance",
        "address": "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
        "tag": "latest",
        "apikey": ek,
    }, timeout=10)
    p(f"    Status: {r.status_code}")
    p(f"    Body:   {r.text[:300]}")
except Exception as e:
    p(f"    ERROR:  {e}")

# Try V1 with just the basic params (no chainid)
p("  Trying V1 basic (no chainid)...")
try:
    r = requests.get("https://api.etherscan.io/api", params={
        "module": "account",
        "action": "balance",
        "address": "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
        "tag": "latest",
        "apikey": ek,
    }, timeout=10)
    p(f"    Status: {r.status_code}")
    p(f"    Body:   {r.text[:300]}")
except Exception as e:
    p(f"    ERROR:  {e}")
p()

p("=" * 70)
p("  DIAGNOSIS COMPLETE")
p(f"  Full results: {os.path.abspath(logfile)}")
p("=" * 70)
log.close()