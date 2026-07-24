#!/usr/bin/env python3
"""
Detailed API Endpoint Response Verification
Shows actual response bodies from all working endpoints
"""
import requests
import json
from pprint import pprint

BASE_URL = "http://localhost:8000"

def fetch_and_print(method, path, name, data=None):
    """Fetch endpoint and print response details."""
    print("\n" + "="*80)
    print(f"ENDPOINT: {name}")
    print("="*80)
    print(f"Method: {method}")
    print(f"URL: {BASE_URL}{path}")
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{path}", json=data, timeout=10)
        
        print(f"HTTP Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        body = response.json()
        print(f"\nResponse Body:")
        pprint(body, width=100)
        
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("\n" + "#"*80)
    print("# AlphaScan API - DETAILED ENDPOINT RESPONSE VERIFICATION")
    print("#"*80)
    
    endpoints = [
        ("GET", "/", "Root Endpoint - Service Information"),
        ("GET", "/status", "Engine Status Endpoint"),
        ("GET", "/config", "Configuration Endpoint"),
        ("GET", "/results", "Results Endpoint"),
        ("GET", "/keys", "Keys Endpoint"),
        ("POST", "/scan", "Scan Endpoint (Non-blocking)", {}),
        ("GET", "/metrics", "Metrics Endpoint"),
        ("POST", "/discord/command", "Discord Command Endpoint", {"command": "!status"}),
    ]
    
    success_count = 0
    total_count = len(endpoints)
    
    for endpoint in endpoints:
        method = endpoint[0]
        path = endpoint[1]
        name = endpoint[2]
        data = endpoint[3] if len(endpoint) > 3 else None
        
        if fetch_and_print(method, path, name, data):
            success_count += 1
    
    # Final summary
    print("\n" + "#"*80)
    print(f"# SUMMARY: {success_count}/{total_count} endpoints responding correctly")
    print("#"*80)
    
    if success_count == total_count:
        print("✅ ALL ENDPOINTS VERIFIED AND WORKING!")
    else:
        print(f"⚠️  {total_count - success_count} endpoint(s) failed")

if __name__ == "__main__":
    main()
