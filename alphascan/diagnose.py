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
p("[1] CENSYS Platform API v3 (PAT auth)")
pat = os.getenv("CENSYS_PAT")
p(f"  PAT: {pat[:8]}...{pat[-4:]} (len={len(pat)})")

try:
    from alphascan.censys_client import CensysClient, CensysAuthError
    client = CensysClient(pat=pat)
    auth_ok = client.verify_auth()
    if auth_ok:
        hits = client.search_hosts("api_key", per_page=3)
        p(f"  Auth: VALID")
        p(f"  Hits: {len(hits)} results")
        for i, hit in enumerate(hits[:2]):
            ip = hit.get("ip", "?")
            services = [s.get("service_name", "?") for s in hit.get("services", [])[:3]]
            p(f"    [{i+1}] {ip} - services: {', '.join(services)}")
    else:
        p("  Auth: INVALID or EXPIRED PAT")
        p("  Generate a new PAT at https://console.censys.io/api")
except CensysAuthError:
    p("  Auth: INVALID PAT (401)")
except Exception as e:
    p(f"  ERROR: {e}")
p()

# ── 2. GITHUB - already working
p("[2] GITHUB")
gt = os.getenv("GITHUB_TOKEN")
try:
    headers = {"Authorization": f"token {gt}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get("https://api.github.com/search/code", headers=headers,
        params={"q": "filename:.env", "per_page": 1}, timeout=15)
    if r.status_code == 200:
        p(f"  Status: 200 OK - {r.json().get('total_count', 0):,} total results")
    else:
        p(f"  Status: {r.status_code} - {r.text[:100]}")
except Exception as e:
    p(f"  ERROR: {e}")
p()

# ── 3. GROQ ──
p("[3] GROQ")
gk = os.getenv("GROQ_API_KEY")
try:
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "Say OK"}],
              "max_tokens": 5, "temperature": 0.1}, timeout=15)
    if r.status_code == 200:
        p(f"  Status: 200 OK - Response: {r.json()['choices'][0]['message']['content'].strip()}")
    else:
        p(f"  Status: {r.status_code} - {r.text[:150]}")
except Exception as e:
    p(f"  ERROR: {e}")
p()

# ── 4. DISCORD - already working
p("[4] DISCORD")
dw = os.getenv("DISCORD_WEBHOOK_URL")
try:
    r = requests.post(dw, json={"content": "AlphaScan diagnostic test"}, timeout=10)
    p(f"  Status: {r.status_code} - {'OK' if r.status_code == 204 else r.text[:100]}")
except Exception as e:
    p(f"  ERROR: {e}")
p()

# ── 5. ETHERSCAN ──
p("[5] ETHERSCAN (V2)")
ek = os.getenv("ETHERSCAN_API_KEY")
try:
    r = requests.get("https://api.etherscan.io/v2/api", params={
        "chainid": 1, "module": "account", "action": "balance",
        "address": "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
        "tag": "latest", "apikey": ek}, timeout=10)
    data = r.json()
    if data.get("status") == "1":
        balance = int(data.get("result", "0")) / 1e18
        p(f"  Status: OK - Balance: {balance:.4f} ETH")
    else:
        p(f"  Status: {data.get('message')} - {data.get('result', '')[:80]}")
except Exception as e:
    p(f"  ERROR: {e}")
p()

p("=" * 70)
p("  DIAGNOSIS COMPLETE")
p(f"  Full results: {os.path.abspath(logfile)}")
p("=" * 70)
log.close()