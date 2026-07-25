"""
AlphaScan - Deep endpoint diagnosis
"""

import requests
import os
import sys
from dotenv import load_dotenv

# Ensure project root is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

logfile = os.path.join(BASE_DIR, "diagnose_results.txt")
log = open(logfile, "w", encoding="utf-8")


def p(msg=""):
    print(msg)
    log.write(msg + "\n")
    log.flush()


p("=" * 70)
p("  AlphaScan - Deep Endpoint Diagnosis")
p("=" * 70)
p()


# ==========================
# 1. CENSYS
# ==========================

p("[1] CENSYS Platform API v3 (PAT auth)")

pat = os.getenv("CENSYS_PAT")

if not pat:
    p("  ERROR: CENSYS_PAT missing")
else:
    p(f"  PAT: {pat[:8]}...{pat[-4:]} (len={len(pat)})")

    try:
        from censys_client import (
            CensysClient,
            CensysAuthError,
            CensysError
        )

        client = CensysClient(pat=pat)

        result = client.get_host("8.8.8.8")

        if result:
            p("  Auth: VALID")
            p("  Endpoint: WORKING")
            p(f"  Response keys: {list(result.keys())[:5]}")
        else:
            p("  Host lookup returned empty")

    except CensysAuthError:
        p("  Auth: INVALID PAT")

    except CensysError as e:
        p(f"  Censys error: {e}")

    except Exception as e:
        p(f"  Python error: {type(e).__name__}: {e}")

p()


# ==========================
# 2. GITHUB
# ==========================

p("[2] GITHUB")

gt = os.getenv("GITHUB_TOKEN")

try:
    r = requests.get(
        "https://api.github.com/search/code",
        headers={
            "Authorization": f"token {gt}",
            "Accept": "application/vnd.github.v3+json"
        },
        params={
            "q": "filename:.env",
            "per_page": 1
        },
        timeout=15
    )

    if r.status_code == 200:
        p(
            f"  Status: OK - "
            f"{r.json().get('total_count',0):,} results"
        )
    else:
        p(f"  Status {r.status_code}: {r.text[:150]}")

except Exception as e:
    p(f"  ERROR: {e}")

p()


# ==========================
# 3. MISTRAL
# ==========================

p("[3] MISTRAL AI")

try:
    from mistralai import Mistral

    client = Mistral(
        api_key=os.getenv("MISTRAL_API_KEY")
    )

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role":"user",
                "content":"Reply OK"
            }
        ],
        max_tokens=5
    )

    p(
        "  Status: OK - "
        + response.choices[0].message.content
    )

except Exception as e:
    p(f"  ERROR: {e}")

p()


# ==========================
# 4. DISCORD
# ==========================

p("[4] DISCORD")

try:
    r = requests.post(
        os.getenv("DISCORD_WEBHOOK_URL"),
        json={
            "content":"AlphaScan diagnostic test"
        },
        timeout=10
    )

    p(
        f"  Status: {r.status_code} "
        f"{'OK' if r.status_code==204 else r.text[:100]}"
    )

except Exception as e:
    p(f"  ERROR: {e}")

p()


# ==========================
# 5. ETHERSCAN
# ==========================

p("[5] ETHERSCAN")

try:

    r = requests.get(
        "https://api.etherscan.io/v2/api",
        params={
            "chainid":1,
            "module":"account",
            "action":"balance",
            "address":
            "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
            "tag":"latest",
            "apikey":os.getenv("ETHERSCAN_API_KEY")
        },
        timeout=10
    )

    data=r.json()

    if data.get("status")=="1":
        balance=int(data["result"])/1e18
        p(f"  Status: OK - {balance:.4f} ETH")
    else:
        p(f"  FAILED: {data}")

except Exception as e:
    p(f"  ERROR: {e}")


p()
p("=" * 70)
p(" DIAGNOSIS COMPLETE")
p(f" Results: {logfile}")
p("=" * 70)

log.close()
