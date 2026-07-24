"""
AlphaScan Live Endpoint Verification Script
Tests all configured API endpoints and reports status.
"""
import requests, json, os, sys
from dotenv import load_dotenv

load_dotenv()
results = []

def test(name, status, detail=""):
    icon = "[PASS]" if status else "[FAIL]"
    msg = f"  {icon} {name}: {'OK' if status else 'FAILED'} - {detail}"
    print(msg)
    results.append({"name": name, "ok": status, "detail": detail})

# Also write to file so it's not lost
logfile = os.path.join(os.path.dirname(__file__) or ".", "live_test_results.txt")
log = open(logfile, "w", encoding="utf-8")

def logprint(s):
    print(s)
    log.write(s + "\n")
    log.flush()

logprint("=" * 60)
logprint("  AlphaScan - Live Endpoint Verification")
logprint("=" * 60)
logprint("")

# ── 1. CENSYS ──
logprint("[1/5] CENSYS Search API")
cid = os.getenv("CENSYS_API_ID")
csec = os.getenv("CENSYS_API_SECRET")
if not cid or not csec:
    test("Censys", False, "API credentials not configured in .env")
else:
    try:
        r = requests.get(
            "https://search.censys.io/api/v2/hosts/search",
            auth=(cid, csec),
            params={"q": "api_key", "per_page": 1},
            timeout=15,
        )
        if r.status_code == 200:
            hits = r.json().get("result", {}).get("hits", [])
            test("Censys", True, f"Status 200, {len(hits)} hits")
        else:
            err = r.json().get("error", r.text[:100])
            test("Censys", False, f"Status {r.status_code}: {err}")
    except Exception as e:
        test("Censys", False, str(e)[:150])
logprint("")

# ── 2. GITHUB ──
logprint("[2/5] GitHub Code Search API")
gt = os.getenv("GITHUB_TOKEN")
if not gt:
    test("GitHub", False, "Token not configured in .env")
else:
    try:
        headers = {
            "Authorization": f"token {gt}",
            "Accept": "application/vnd.github.v3+json",
        }
        r = requests.get(
            "https://api.github.com/search/code",
            headers=headers,
            params={"q": "filename:.env", "per_page": 1},
            timeout=15,
        )
        if r.status_code == 200:
            total = r.json().get("total_count", 0)
            test("GitHub", True, f"Status 200, {total:,} total results")
        elif r.status_code == 401:
            test("GitHub", False, "Status 401: Token is invalid/expired")
        elif r.status_code == 403:
            msg = r.json().get("message", "Rate limited?")
            test("GitHub", False, f"Status 403: {msg[:100]}")
        elif r.status_code == 422:
            errs = r.json().get("errors", [{}])
            test("GitHub", False, f"Status 422: {errs[0].get('message', '')[:100]}")
        else:
            test("GitHub", False, f"Status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        test("GitHub", False, str(e)[:100])
logprint("")

# ── 3. GROQ ──
logprint("[3/5] Groq LLM API")
gk = os.getenv("GROQ_API_KEY")
if not gk:
    test("Groq", False, "API key not configured in .env")
else:
    try:
        import groq
        client = groq.Groq(api_key=gk)
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": "Reply with just the word OK"}],
            temperature=0.1,
            max_tokens=10,
        )
        content = response.choices[0].message.content.strip()
        test("Groq", True, f"Response: {content}")
    except Exception as e:
        test("Groq", False, str(e)[:150])
logprint("")

# ── 4. DISCORD ──
logprint("[4/5] Discord Webhook")
dw = os.getenv("DISCORD_WEBHOOK_URL")
if not dw:
    test("Discord", False, "Webhook URL not configured in .env")
else:
    try:
        r = requests.post(
            dw,
            json={"content": "AlphaScan Live Test - All endpoints verified successfully."},
            timeout=10,
        )
        if r.status_code == 204:
            test("Discord", True, "Status 204, message delivered")
        elif r.status_code == 404:
            test("Discord", False, "Status 404: Webhook URL invalid/deleted")
        elif r.status_code == 429:
            test("Discord", False, "Status 429: Rate limited")
        else:
            test("Discord", False, f"Status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        test("Discord", False, str(e)[:100])
logprint("")

# ── 5. ETHERSCAN ──
logprint("[5/5] Etherscan API")
ek = os.getenv("ETHERSCAN_API_KEY")
if not ek:
    test("Etherscan", False, "API key not configured in .env")
else:
    try:
        r = requests.get(
            "https://api.etherscan.io/api",
            params={
                "module": "account",
                "action": "balance",
                "address": "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
                "tag": "latest",
                "apikey": ek,
            },
            timeout=10,
        )
        data = r.json()
        if data.get("status") == "1":
            balance = int(data.get("result", "0")) / 1e18
            test("Etherscan", True, f"Status 1, balance {balance:.4f} ETH")
        else:
            msg = data.get("message", "unknown")
            result = data.get("result", "")
            test("Etherscan", False, f"Status {data.get('status')}: {msg} -> {result[:80]}")
    except Exception as e:
        test("Etherscan", False, str(e)[:100])
logprint("")

# ── SUMMARY ──
logprint("=" * 60)
logprint("  RESULTS SUMMARY")
logprint("=" * 60)
pass_count = sum(1 for r in results if r["ok"])
fail_count = sum(1 for r in results if not r["ok"])
for r in results:
    icon = "[PASS]" if r["ok"] else "[FAIL]"
    logprint(f"  {icon} {r['name']:15s} {'OK' if r['ok'] else 'FAILED':6s}  {r['detail']}")
logprint("")
logprint(f"  Total: {pass_count}/{pass_count+fail_count} passed ({fail_count} failed)")
logprint("")
logprint(f"Full results written to: {logfile}")
log.close()

# Exit with appropriate code
sys.exit(0 if fail_count == 0 else 1)