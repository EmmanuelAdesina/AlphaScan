[35mconfig/patterns.py[m[36m:[m    # Anthropic / Claude (must come before OpenAI since [1;31msk-[mant- also starts with [1;31msk-[m)
[35mconfig/patterns.py[m[36m:[m    ("claude", r"[1;31msk-[mant-[a-zA-Z0-9_-]{20,}", "Anthropic/Claude API key", "[1;31msk-[mant-", RANK_AI),
[35mconfig/patterns.py[m[36m:[m    ("openai", r"[1;31msk-[m[a-zA-Z0-9-]{20,}", "OpenAI API key", "[1;31msk-[m", RANK_AI),
[35mscanners/pastebin_scanner.py[m[36m:[m        "[1;31msk-[mlive", "[1;31msk-[mtest", "AKIA", "ghp_",
[35mscanners/telegram_scanner.py[m[36m:[m        "[1;31msk-[mlive", "[1;31msk-[mtest", "AKIA", "ghp_",
[35mself_improve/code_generator.py[m[36m:[m            "openai": ("openai", "[1;31msk-[m[a-zA-Z0-9]{20,}", "OpenAI API key", "[1;31msk-[m"),
[35mself_improve/code_generator.py[m[36m:[m            "claude": ("claude", "[1;31msk-[mant-[a-zA-Z0-9_-]{20,}", "Anthropic/Claude API key", "[1;31msk-[mant-"),
[35mself_improve/code_generator.py[m[36m:[m        prefix = "[1;31msk-[m"
[35mtests/test_v05_features.py[m[36m:[m        text = "OpenAI key: [1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr"
[35mtests/test_v05_features.py[m[36m:[m            {"type": "openai", "value": "[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr", "context": "", "rank": 9},
[35mtests/test_validator.py[m[36m:[m        result = classifier.classify("[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr")
[35mtests/test_validator.py[m[36m:[m        assert "[1;31msk-[m" in result["value"]
[35mtests/test_validator.py[m[36m:[m        result = classifier.classify("[1;31msk-[mant-api03-abc123def456ghi789jkl012mno345")
[35mtests/test_validator.py[m[36m:[m            "[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr",
[35mtests/test_validator.py[m[36m:[m        result = classifier.classify("[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr")
[35mtests/test_validator.py[m[36m:[m        key_data = {"type": "openai", "value": "[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr"}
[35mtests/test_validator.py[m[36m:[m        key_data = {"type": "openai", "value": "[1;31msk-[mshort"}
[35mtests/test_validator.py[m[36m:[m            {"type": "openai", "value": "[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr"},
[35mtests/test_validator.py[m[36m:[m        masked = validator.mask_key("[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr")
[35mtests/test_validator.py[m[36m:[m        assert len(masked) < len("[1;31msk-[mproj-abc123def456ghi789jkl012mno345pqr")
[35mutils/key_validator.py[m[36m:[m        "openai": {"min_len": 20, "max_len": 200, "prefix": "[1;31msk-[m"},
[35mutils/key_validator.py[m[36m:[m        "claude": {"min_len": 20, "max_len": 200, "prefix": "[1;31msk-[mant-"},
[35mverification/api_intelligence.py[m[36m:[m    "openai": re.compile(r"[1;31msk-[m[a-zA-Z0-9-]{20,}"),
[35mverification/api_intelligence.py[m[36m:[m    "claude": re.compile(r"[1;31msk-[mant-[a-zA-Z0-9_-]{20,}"),
[35mverification/api_intelligence.py[m[36m:[m    "openai": "[1;31msk-[m",
[35mverification/api_intelligence.py[m[36m:[m    "claude": "[1;31msk-[mant-",
[35mverification/api_intelligence.py[m[36m:[m            checks["format_valid"] = value.startswith("[1;31msk-[m") and len(value) >= 23
[35mverification/api_intelligence.py[m[36m:[m            checks["format_valid"] = value.startswith("[1;31msk-[mant-") and len(value) >= 25
[35mverification/verifiers/api_verifier.py[m[36m:[m            result["valid"] = value.startswith("[1;31msk-[m") and len(value) >= 23
[35mverification/verifiers/api_verifier.py[m[36m:[m            result["prefix_check"] = value.startswith("[1;31msk-[m")
[35mverification/verifiers/api_verifier.py[m[36m:[m            result["valid"] = value.startswith("[1;31msk-[mant-") and len(value) >= 25
[35mverification/verifiers/api_verifier.py[m[36m:[m            result["prefix_check"] = value.startswith("[1;31msk-[mant-")
