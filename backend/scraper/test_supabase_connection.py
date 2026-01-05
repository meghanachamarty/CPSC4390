#!/usr/bin/env python3
"""
Test script to verify Supabase connection and environment variables
"""
import os
import requests

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")

# Check environment variables
ANON = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET")

print(f"\n=== Environment Variables ===")
print(f"SUPABASE_ANON_KEY: {'SET (' + ANON[:20] + '...)' if ANON else 'NOT SET'}")
print(f"SUPABASE_URL: {SUPABASE_URL if SUPABASE_URL else 'NOT SET'}")
print(f"STORAGE_BUCKET: {STORAGE_BUCKET if STORAGE_BUCKET else 'NOT SET'}")

if not ANON:
    print("\n❌ SUPABASE_ANON_KEY is missing!")
    exit(1)

if not SUPABASE_URL:
    print("\n❌ SUPABASE_URL is missing!")
    exit(1)

# Test Supabase function endpoint
EDGE_FN_URL = f"{SUPABASE_URL}/functions/v1/ingest_by_url"
FN_HEADERS = {"Authorization": f"Bearer {ANON}"}

print(f"\n=== Testing Supabase Connection ===")
print(f"Function URL: {EDGE_FN_URL}")

try:
    # Test with a simple request
    test_payload = {
        "path": "test/connection.txt",
        "contentType": "text/plain"
    }
    
    response = requests.post(
        EDGE_FN_URL,
        json=test_payload,
        headers=FN_HEADERS,
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.ok:
        try:
            data = response.json()
            print(f"Response Data: {data}")
            if "url" in data:
                print("✓ Successfully got signed URL from Supabase!")
            else:
                print("⚠️  Response doesn't contain 'url' field")
        except Exception as e:
            print(f"⚠️  Could not parse JSON response: {e}")
            print(f"Raw response: {response.text}")
    else:
        print(f"❌ Request failed: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Network error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print(f"\n=== Summary ===")
if ANON and SUPABASE_URL:
    print("✓ Environment variables are configured")
    print("✓ Ready to test the main scraper")
else:
    print("❌ Missing required environment variables")
    print("Please check your .env file")