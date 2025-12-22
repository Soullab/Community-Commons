#!/usr/bin/env python3
"""
Test configurable fallback chain for AIN provider router.

Verifies that AIN_FALLBACK_CHAIN env var correctly sets provider priority.
"""

import os
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ain_providers import AINProviderRouter


def test_default_priority():
    """Test that default priority is anthropic -> openai -> local"""
    router = AINProviderRouter()

    assert router.priority == ["anthropic", "openai", "local"], \
        f"Expected default priority ['anthropic', 'openai', 'local'], got {router.priority}"

    print("✅ Default priority: anthropic -> openai -> local")


def test_custom_priority_via_parameter():
    """Test custom priority via parameter"""
    router = AINProviderRouter(fallback_chain="openai,local,anthropic")

    assert router.priority == ["openai", "local", "anthropic"], \
        f"Expected priority ['openai', 'local', 'anthropic'], got {router.priority}"

    print("✅ Custom priority (parameter): openai -> local -> anthropic")


def test_custom_priority_via_env():
    """Test custom priority via AIN_FALLBACK_CHAIN env var"""
    # Set env var
    os.environ["AIN_FALLBACK_CHAIN"] = "local,openai"

    try:
        router = AINProviderRouter()

        assert router.priority == ["local", "openai"], \
            f"Expected priority ['local', 'openai'], got {router.priority}"

        print("✅ Custom priority (env var): local -> openai")
    finally:
        # Clean up
        del os.environ["AIN_FALLBACK_CHAIN"]


def test_local_first_chain():
    """Test local-first sovereignty chain"""
    router = AINProviderRouter(fallback_chain="local,anthropic,openai")

    assert router.priority == ["local", "anthropic", "openai"], \
        f"Expected priority ['local', 'anthropic', 'openai'], got {router.priority}"

    print("✅ Local-first (sovereignty) priority: local -> anthropic -> openai")


def test_invalid_provider():
    """Test that invalid providers raise ValueError"""
    try:
        router = AINProviderRouter(fallback_chain="invalid,openai")
        print("❌ FAIL: Should have raised ValueError for invalid provider")
        sys.exit(1)
    except ValueError as e:
        if "invalid" in str(e).lower():
            print("✅ Invalid provider correctly raises ValueError")
        else:
            print(f"❌ FAIL: Unexpected error message: {e}")
            sys.exit(1)


def main():
    print("=" * 60)
    print("AIN Fallback Chain Configuration Tests")
    print("=" * 60)
    print()

    try:
        test_default_priority()
        test_custom_priority_via_parameter()
        test_custom_priority_via_env()
        test_local_first_chain()
        test_invalid_provider()

        print()
        print("=" * 60)
        print("All tests PASSED ✅")
        print("=" * 60)
        print()
        print("Usage examples:")
        print("  # Default (anthropic -> openai -> local)")
        print("  python3 scripts/ain_orchestrator.py deliberate \"Question\"")
        print()
        print("  # Local-first sovereignty mode")
        print("  AIN_FALLBACK_CHAIN=local,anthropic,openai \\")
        print("    python3 scripts/ain_orchestrator.py deliberate \"Question\"")
        print()
        print("  # OpenAI-first (cheaper/faster for simple queries)")
        print("  AIN_FALLBACK_CHAIN=openai,local \\")
        print("    python3 scripts/ain_orchestrator.py deliberate \"Question\"")

        sys.exit(0)

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"Test FAILED ❌: {e}")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"Test ERROR ❌: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
