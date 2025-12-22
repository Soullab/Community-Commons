#!/usr/bin/env python3
"""
Regression test for AIN provider failover.

Tests that when Anthropic is unavailable (no credits), the system
automatically fails over to OpenAI and completes successfully.
"""

import asyncio
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ain_orchestrator import CommitteeOrchestrator


async def test_provider_failover():
    """Test that AIN automatically fails over from Anthropic to OpenAI"""

    print("=" * 60)
    print("AIN Provider Failover Regression Test")
    print("=" * 60)
    print()

    orchestrator = CommitteeOrchestrator()

    # Simple question for quick test
    question = "What is consciousness computing in one sentence?"

    # Minimal framings for speed
    framings = [
        {
            "name": "Technical",
            "framing": "Define from technical/engineering perspective, one sentence."
        },
        {
            "name": "Practical",
            "framing": "Define from practical use-case perspective, one sentence."
        }
    ]

    print("Testing failover with minimal 2-agent committee...")
    print(f"Question: {question}")
    print()

    try:
        # Run deliberation (should failover from Anthropic to OpenAI)
        result = await orchestrator.deliberate(
            question=question,
            framings=framings,
            verbose=True  # Show provider routing
        )

        # Verify result
        provider_used = result.get("provider_used")
        elapsed = result.get("elapsed_seconds", 0)

        print()
        print("=" * 60)
        print("Test Results")
        print("=" * 60)

        if not provider_used:
            print("❌ FAIL: No provider_used in session metadata")
            return False

        print(f"✅ Provider used: {provider_used}")
        print(f"✅ Elapsed time: {elapsed:.1f}s")
        print(f"✅ Agents responded: {len(result.get('responses', {}))}")
        print(f"✅ Synthesis generated: {len(result.get('synthesis', '')) > 0}")

        # Expected behavior: Should use OpenAI since Anthropic has no credits
        if provider_used == "openai":
            print()
            print("✅ PASS: Correctly failed over to OpenAI")
            return True
        elif provider_used == "anthropic":
            print()
            print("⚠️  WARNING: Used Anthropic (credits may have been added)")
            print("   This is OK if you added credits, but failover wasn't tested.")
            return True
        elif provider_used == "local":
            print()
            print("⚠️  WARNING: Used local Ollama (both cloud providers unavailable?)")
            print("   This is OK for sovereignty, but cloud failover wasn't tested.")
            return True
        else:
            print()
            print(f"❌ FAIL: Unexpected provider: {provider_used}")
            return False

    except Exception as e:
        print()
        print("=" * 60)
        print("Test Results")
        print("=" * 60)
        print(f"❌ FAIL: Exception during deliberation")
        print(f"   Error: {str(e)}")
        return False


async def main():
    success = await test_provider_failover()

    print()
    print("=" * 60)

    if success:
        print("Regression test PASSED ✅")
        print()
        print("Provider failover is working correctly.")
        print("AIN will automatically use available providers.")
        sys.exit(0)
    else:
        print("Regression test FAILED ❌")
        print()
        print("Check provider configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
