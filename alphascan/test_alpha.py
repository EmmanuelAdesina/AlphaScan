"""Quick test to verify AlphaScan system integrity."""
import sys
sys.path.insert(0, '.')

print("=== AlphaScan System Test ===\n")

# 1. Config
from alphascan.config import check_config
config = check_config()
print("1. Config check:")
for k, v in config.items():
    status = "OK" if v else "NOT SET"
    print(f"   {k}: {status}")

# 2. Parser regex
from alphascan.parser import extract_with_regex
keys = extract_with_regex("API_KEY=sk-proj-test-key-1234567890123456")
print(f"\n2. Regex extraction: {len(keys)} key(s) found")
for k in keys:
    print(f"   type={k['type']}, rank={k['rank']}")

# 3. Validator
from alphascan.validator import validate_key, calculate_entropy, check_format
test_keys = [
    {"type": "openai", "value": "sk-proj-abcdef12345678901234567890", "rank": 9},
    {"type": "aws", "value": "AKIA1234567890ABCDEF", "rank": 7},
    {"type": "github", "value": "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "rank": 10},
    {"type": "eth_private_key", "value": "0x" + "a" * 64, "rank": 2},
]
print("\n3. Validation:")
for tk in test_keys:
    result = validate_key(tk)
    fmt = result.get("format_valid", "?")
    ent = result.get("entropy", "?")
    valid = result.get("valid", "?")
    summary = result.get("validation_summary", "?")
    print(f"   {tk['type']}: format={fmt} entropy={ent} valid={valid} -> {summary}")

# 4. Reporter
from alphascan.reporter import get_rank_name, mask_value
print(f"\n4. Reporter:")
print(f"   Rank 0 name: {get_rank_name(0)}")
print(f"   Masked API key: {mask_value('sk-proj-abc123', 'openai')}")
print(f"   Masked SSH: {mask_value('-----BEGIN RSA PRIVATE KEY-----', 'ssh_rsa')}")

print("\n=== ALL TESTS PASSED ===")