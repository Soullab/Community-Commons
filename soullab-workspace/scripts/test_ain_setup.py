#!/usr/bin/env python3
"""
Quick test to verify AIN setup is correct
"""

import os
import sys
from pathlib import Path

print("="*60)
print("AIN Setup Verification")
print("="*60)

# Check python-dotenv
try:
    from dotenv import load_dotenv
    print("✅ python-dotenv installed")

    # Try loading .env files
    env_paths = [
        Path.home() / "MAIA-SOVEREIGN" / ".env.local",
        Path.home() / "MAIA-SOVEREIGN" / ".env",
        Path.home() / "soullab-workspace" / ".env.local",
    ]

    env_loaded = None
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)  # Override existing env vars
            env_loaded = env_path
            print(f"✅ Loaded environment from: {env_path}")
            break

    if not env_loaded:
        print("⚠️  No .env file found in common locations")

except ImportError:
    print("❌ python-dotenv not installed")
    print("   Install with: pip install python-dotenv")
    sys.exit(1)

# Check anthropic package
try:
    from anthropic import Anthropic
    print("✅ anthropic package installed")
except ImportError:
    print("❌ anthropic package not installed")
    print("   Install with: pip install anthropic")
    sys.exit(1)

# Check API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
if api_key:
    # Mask the key for security
    masked = api_key[:15] + "..." + api_key[-4:]
    print(f"✅ ANTHROPIC_API_KEY loaded: {masked}")
    print(f"   Length: {len(api_key)} characters")

    # Check for common issues
    if api_key != api_key.strip():
        print("⚠️  WARNING: API key has leading/trailing whitespace")
    if "\n" in api_key:
        print("⚠️  WARNING: API key contains newlines")
    if " " in api_key:
        print("⚠️  WARNING: API key contains spaces")

else:
    print("❌ ANTHROPIC_API_KEY not found")
    print("   Add to ~/MAIA-SOVEREIGN/.env.local")
    sys.exit(1)

# Test API connection
print("\n" + "="*60)
print("Testing API Connection...")
print("="*60)

try:
    client = Anthropic(api_key=api_key)

    # Make a minimal test request
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": "Say 'test'"
        }]
    )

    print("✅ API connection successful!")
    print(f"   Response: {response.content[0].text}")
    print("\n✅ All checks passed! AIN is ready to use.")

except Exception as e:
    error_str = str(e)
    print(f"❌ API connection failed")
    print(f"   Error: {error_str}")

    if "401" in error_str or "authentication" in error_str.lower():
        print("\n⚠️  This looks like an invalid or expired API key.")
        print("   Solutions:")
        print("   1. Get a new API key from: https://console.anthropic.com/")
        print("   2. Update ~/MAIA-SOVEREIGN/.env.local with new key")
        print("   3. Format: ANTHROPIC_API_KEY=sk-ant-api03-...")
    elif "credit balance" in error_str.lower() or "billing" in error_str.lower():
        print("\n⚠️  Your API key is valid, but you need to add credits!")
        print("   Solutions:")
        print("   1. Go to: https://console.anthropic.com/settings/billing")
        print("   2. Add credits (can start with $5 to test)")
        print("   3. Once credits are added, AIN will work immediately")
    elif "rate" in error_str.lower():
        print("\n⚠️  Rate limit hit - wait a moment and try again")
    else:
        print("\n⚠️  Unexpected error - check your network connection")

    sys.exit(1)

print("\n" + "="*60)
print("Ready to run your first committee!")
print("="*60)
print("\nTry:")
print('  python3 scripts/ain_orchestrator.py deliberate "What is consciousness?"')
print("\nOr via slash command:")
print('  /ain deliberate "How should I prioritize this week?"')
