#!/usr/bin/env python3
"""
Zero-cost regression test for AIN JSON output.

Tests that AIN correctly outputs valid JSON even when all providers fail.
"""

import os
import json
import subprocess
import sys


def test_json_output_on_failure():
    """Test that JSON output is valid even when AIN fails (no API keys)"""

    print("=" * 60)
    print("AIN JSON Output Regression Test")
    print("=" * 60)
    print("\nTesting that stdout is valid JSON even on failure...")
    print()

    # Create environment without API keys (force failure)
    env = dict(os.environ)
    # Remove all possible API keys
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)
    # Set invalid keys to force failure
    env["ANTHROPIC_API_KEY"] = "invalid-key-for-testing"
    env["OPENAI_API_KEY"] = "invalid-key-for-testing"
    env["AIN_PROVIDER"] = "anthropic"  # Force Anthropic which will fail with invalid key

    cmd = [
        sys.executable,
        "scripts/ain_orchestrator.py",
        "deliberate",
        "JSON output smoke test",
        "--json",
    ]

    print(f"Running: {' '.join(cmd)}")
    print(f"Environment: No API keys (forcing provider failure)")
    print()

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=os.path.expanduser("~/soullab-workspace"))
    stdout = (p.stdout or "").strip()
    stderr = (p.stderr or "").strip()

    print("Return code:", p.returncode)
    print()

    # Verify stdout is valid JSON
    try:
        data = json.loads(stdout)
        print("✅ stdout is valid JSON")
    except Exception as e:
        print("❌ FAIL: stdout is not valid JSON")
        print("\nSTDOUT:", stdout[:500])
        print("\nSTDERR:", stderr[:500])
        raise RuntimeError(f"JSON parsing failed: {e}")

    # Verify JSON structure
    print(f"✅ JSON contains 'ok' field: {data.get('ok')}")

    if "ok" not in data:
        raise AssertionError("JSON must include 'ok' field")

    if data["ok"] is False:
        # Error path - verify error fields present
        if "error" not in data:
            raise AssertionError("JSON must include 'error' field on failure")
        print(f"✅ Error path: JSON contains error: {data.get('error')[:50]}...")
        print(f"✅ Error path: JSON contains error_type: {data.get('error_type')}")
    else:
        # Success path - verify result fields present
        if "responses" not in data or "synthesis" not in data:
            raise AssertionError("JSON must include 'responses' and 'synthesis' on success")
        print(f"✅ Success path: JSON contains responses: {len(data.get('responses', {}))} agents")
        print(f"✅ Success path: JSON contains synthesis: {len(data.get('synthesis', ''))} chars")
        print(f"✅ Success path: Used provider: {data.get('provider_used')}")

    # Verify stderr contains logs (not data)
    if "Spawning committee" in stderr or "Running parallel" in stderr:
        print("✅ Status logs correctly routed to stderr")
    else:
        print("⚠️  Warning: Expected status logs in stderr")

    # Verify stdout contains ONLY JSON (no status logs)
    if "Spawning" in stdout or "Running" in stdout:
        raise AssertionError("Status logs leaked into stdout (should be stderr only)")

    print("✅ Status logs not present in stdout")

    print()
    print("=" * 60)
    print("All assertions PASSED ✅")
    print("=" * 60)
    print()
    if data["ok"]:
        print("JSON output is machine-readable and valid on success.")
    else:
        print("JSON output is machine-readable and valid even on error.")
    print("MAIA can safely parse stdout with JSON.parse().")


def test_json_pretty_output():
    """Test that --json-pretty outputs readable JSON"""

    print()
    print("=" * 60)
    print("Testing --json-pretty mode")
    print("=" * 60)
    print()

    # Use minimal environment (no keys, forcing failure)
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)

    cmd = [
        sys.executable,
        "scripts/ain_orchestrator.py",
        "deliberate",
        "Pretty JSON test",
        "--json-pretty",
    ]

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=os.path.expanduser("~/soullab-workspace"))
    stdout = (p.stdout or "").strip()

    # Verify it's valid JSON
    data = json.loads(stdout)
    print("✅ --json-pretty produces valid JSON")

    # Verify it's actually pretty (has newlines and indentation)
    if "\n" not in stdout:
        raise AssertionError("Expected pretty JSON to have newlines")

    if "  " not in stdout:  # Two spaces = indentation
        raise AssertionError("Expected pretty JSON to have indentation")

    print("✅ JSON is formatted with newlines and indentation")

    # Verify same structure as --json (must have 'ok' field)
    if "ok" not in data:
        raise AssertionError("--json-pretty must have 'ok' field")

    print(f"✅ --json-pretty has same structure (ok={data['ok']})")


def main():
    try:
        test_json_output_on_failure()
        test_json_pretty_output()

        print()
        print("=" * 60)
        print("All JSON output tests PASSED ✅")
        print("=" * 60)
        print()
        print("MAIA can now call AIN like this:")
        print("  python3 scripts/ain_orchestrator.py deliberate \"...\" --json \\")
        print("    1>committee.json 2>committee.log")
        print()
        print("Then parse committee.json with JSON.parse()")

        sys.exit(0)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"Test FAILED ❌: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
