#!/usr/bin/env python3
"""
Live API endpoint testing script.
Tests all endpoints and validates responses.
"""
import requests
import json
import time
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

def test_endpoint(method: str, path: str, name: str, data=None, timeout=5) -> tuple[bool, str, Any]:
    """Test a single endpoint and return result."""
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            return False, "Unknown method", None

        if response.status_code in [200, 201, 202]:
            try:
                body = response.json()
                return True, f"Status {response.status_code}", body
            except:
                return True, f"Status {response.status_code}", response.text
        else:
            return False, f"Status {response.status_code}", response.text
    except Exception as e:
        return False, f"Error: {str(e)}", None

def main():
    """Run all endpoint tests."""
    print("=" * 80)
    print("AlphaScan API Live Endpoint Testing")
    print("=" * 80)
    print()
    
    # Give server a moment to be fully ready
    time.sleep(1)
    
    tests = [
        ("GET", "/", "Root Endpoint - Service Info", None),
        ("GET", "/status", "Status Endpoint - Engine Status", None),
        ("GET", "/config", "Config Endpoint - Configuration", None),
        ("GET", "/results", "Results Endpoint - Recent Scan Results", None),
        ("GET", "/keys", "Keys Endpoint - Verified Keys", None),
        ("POST", "/scan", "Scan Endpoint - Trigger Scan", {}, 10),  # Higher timeout for scan
        ("GET", "/metrics", "Metrics Endpoint - Improvement Metrics", None),
        ("POST", "/discord/command", "Discord Command Endpoint", {"command": "test"}),
    ]
    
    results: List[Dict[str, Any]] = []
    
    for method, path, name, data, *timeout_args in tests:
        timeout = timeout_args[0] if timeout_args else 5
        print(f"Testing: {name}")
        print(f"  {method} {path}")
        
        success, message, body = test_endpoint(method, path, name, data, timeout)
        
        if success:
            print(f"  ✅ PASSED: {message}")
            if body:
                if isinstance(body, dict):
                    # Show key fields from response
                    keys = list(body.keys())[:5]
                    print(f"  Response keys: {', '.join(keys)}")
                    if len(body.keys()) > 5:
                        print(f"  ... and {len(body.keys()) - 5} more")
                else:
                    print(f"  Response: {str(body)[:100]}")
        else:
            print(f"  ❌ FAILED: {message}")
            if body:
                print(f"  Error: {str(body)[:200]}")
        
        results.append({
            "name": name,
            "path": path,
            "method": method,
            "success": success,
            "message": message,
            "has_body": body is not None,
        })
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print()
    
    print("Endpoint Status:")
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['method']:4} {r['path']:20} - {r['name']}")
    
    print()
    print("=" * 80)
    if passed == total:
        print("✅ ALL ENDPOINTS WORKING!")
    else:
        print(f"⚠️  {total - passed} endpoint(s) failed")
    print("=" * 80)

if __name__ == "__main__":
    main()
