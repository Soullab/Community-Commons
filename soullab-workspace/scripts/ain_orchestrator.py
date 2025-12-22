#!/usr/bin/env python3
"""
AIN (Agentic Intelligence Networks) Committee Orchestrator
Runs multiple LLM instances in parallel with different framings
to produce dialectical synthesis and emergence detection.

Supports: Anthropic Claude, OpenAI GPT-4, Ollama (local)
Automatic failover when primary provider is unavailable.

Based on Soullab consciousness computing architecture.
"""

import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import provider abstraction
try:
    from ain_providers import get_llm_response, AINProviderRouter
except ImportError:
    print("Error: ain_providers not found.")
    print("Make sure ain_providers.py is in the same directory.")
    sys.exit(1)

# Configuration
WORKSPACE = Path.home() / "soullab-workspace"
LOG_DIR = WORKSPACE / ".logs"
AIN_LOG = LOG_DIR / "ain_sessions.jsonl"
CONTEXT_DIR = WORKSPACE / "llm-context"

# Get preferred provider from environment (or auto-detect)
PROVIDER_PREFERENCE = os.environ.get("AIN_PROVIDER", "auto")

# Initialize router (will check for available providers)
router = AINProviderRouter(preference=PROVIDER_PREFERENCE)


# JSON output helpers
def _log(*args, **kwargs):
    """Log to stderr (for status/progress messages in JSON mode)"""
    print(*args, file=sys.stderr, **kwargs)


def _emit_json(obj: Dict[str, Any], pretty: bool = False):
    """Emit JSON to stdout (for machine-readable output)"""
    if pretty:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(obj, ensure_ascii=False))


def _result_envelope_ok(result: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap successful result in standard envelope"""
    return {"ok": True, **result}


def _result_envelope_err(stage: str, err: Exception) -> Dict[str, Any]:
    """Wrap error in standard envelope"""
    return {
        "ok": False,
        "stage": stage,
        "error": str(err),
        "error_type": err.__class__.__name__,
        "traceback": traceback.format_exc(limit=8),
    }


class Agent:
    """Individual agent with specific framing/lens"""

    def __init__(self, name: str, framing: str, context: str = ""):
        self.name = name
        self.framing = framing
        self.context = context

    async def respond(self, question: str, verbose: bool = False) -> str:
        """Get agent's response to question through their lens"""

        system_prompt = f"""You are participating in a multi-perspective committee deliberation.

Your specific lens/framing: {self.framing}

Respond to the question ONLY from this perspective. Be concise but insightful.
Your response should be 2-4 paragraphs maximum.

Do not try to synthesize other perspectives - that's the orchestrator's job.
Focus deeply on your assigned lens.
"""

        if self.context:
            system_prompt += f"\n\nRelevant context:\n{self.context}"

        try:
            response, provider = await router.generate(
                prompt=question,
                system=system_prompt,
                max_tokens=1024,
                temperature=1.0,
                verbose=verbose
            )
            return response

        except Exception as e:
            return f"[Error from {self.name}: {str(e)}]"


class CommitteeOrchestrator:
    """Orchestrates multi-agent committees for consciousness computing"""

    def __init__(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    async def deliberate(
        self,
        question: str,
        framings: List[Dict[str, str]],
        context: str = "",
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Run a deliberation committee.

        Args:
            question: The question/problem to deliberate
            framings: List of dicts with 'name' and 'framing' keys
            context: Optional shared context for all agents
            verbose: Print provider routing info

        Returns:
            Dict with responses, synthesis, and metadata
        """

        _log(f"\n🧠 Spawning committee with {len(framings)} agents...")

        # Show available providers
        available = router.get_available_providers()
        if verbose:
            _log(f"   Available providers: {', '.join([p[1].name for p in available])}")
        _log()

        # Create agents
        agents = [
            Agent(f["name"], f["framing"], context)
            for f in framings
        ]

        # Parallel execution
        _log("⚡ Running parallel deliberation...")
        start_time = datetime.now()

        responses = await asyncio.gather(*[
            agent.respond(question, verbose=False) for agent in agents  # Don't spam verbose per agent
        ])

        elapsed = (datetime.now() - start_time).total_seconds()
        _log(f"✅ Collected {len(responses)} responses in {elapsed:.1f}s\n")

        # Build response dict
        agent_responses = {
            agents[i].name: {
                "framing": agents[i].framing,
                "response": responses[i]
            }
            for i in range(len(agents))
        }

        # Synthesize
        _log("🔮 Generating dialectical synthesis...")
        synthesis, synthesis_provider = await self._synthesize(question, agent_responses, verbose)

        # Log session
        session = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "framings": framings,
            "responses": agent_responses,
            "synthesis": synthesis,
            "elapsed_seconds": elapsed,
            "provider_used": synthesis_provider
        }

        self._log_session(session)

        return session

    async def _synthesize(
        self,
        question: str,
        responses: Dict[str, Dict],
        verbose: bool = False
    ) -> tuple[str, str]:
        """Generate dialectical synthesis from agent responses"""

        # Build prompt with all responses
        responses_text = ""
        for name, data in responses.items():
            responses_text += f"\n## {name} ({data['framing']})\n\n{data['response']}\n"

        synthesis_prompt = f"""You are synthesizing a multi-perspective committee deliberation.

ORIGINAL QUESTION:
{question}

AGENT RESPONSES:
{responses_text}

Your task: Generate a dialectical synthesis that:

1. **Identifies Key Tensions**: Where do perspectives conflict or diverge?
2. **Maps Polarities**: What are the thesis/antithesis pairs?
3. **Synthesizes Higher-Order Insights**: What emerges from holding tensions together?
4. **Detects Novelty**: Is this just recombination or genuine emergence?
5. **Provides Recommendation**: What's the integrated path forward?

Format your synthesis as:

### Synthesis

[2-3 paragraphs integrating the perspectives]

### Key Tensions

- **[Tension 1]**: [Description]
- **[Tension 2]**: [Description]

### Emergence Detected

[Rating: ⭐ Recombination | ⭐⭐ Synthesis | ⭐⭐⭐ Breakthrough]

[Explanation of why this rating]

### Recommended Action

[Clear next step that honors the dialectic]
"""

        response, provider = await router.generate(
            prompt=synthesis_prompt,
            max_tokens=2048,
            temperature=1.0,
            verbose=verbose
        )

        return (response, provider)

    def _log_session(self, session: Dict[str, Any]):
        """Append session to JSONL log"""
        with open(AIN_LOG, 'a') as f:
            f.write(json.dumps(session) + "\n")

    async def review_writing(
        self,
        file_path: str,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Multi-perspective writing review.

        Args:
            file_path: Path to markdown file to review
            verbose: Print provider routing info

        Returns:
            Dict with reviews, synthesis, and metadata
        """

        # Read file
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            _log(f"Error: File not found: {file_path}")
            return {}

        # Read writing style guide if available
        style_guide = ""
        style_path = CONTEXT_DIR / "writing-style.md"
        if style_path.exists():
            with open(style_path, 'r') as f:
                style_guide = f.read()

        # Define review lenses
        framings = [
            {
                "name": "Technical Accuracy",
                "framing": "Review for technical accuracy, logical consistency, and factual correctness. Flag anything misleading or imprecise."
            },
            {
                "name": "Voice & Style",
                "framing": f"Review for voice consistency and style. Reference the style guide:\n\n{style_guide[:500]}...\n\nFlag AI-speak, corporate jargon, or places where the voice slips."
            },
            {
                "name": "Audience Resonance",
                "framing": "Review from the reader's perspective. What's confusing? What assumptions are made? What needs more context or examples?"
            },
            {
                "name": "Structure & Flow",
                "framing": "Review the structure and flow. Are transitions smooth? Is the argument building logically? Are sections in the right order?"
            },
            {
                "name": "Depth & Impact",
                "framing": "Review for intellectual depth and potential impact. What could be explored more deeply? What insights are underdeveloped? What's the archetypal/mythic dimension?"
            }
        ]

        question = f"""Review this piece of writing:

---
{content[:3000]}{'...' if len(content) > 3000 else ''}
---

Provide specific, actionable feedback from your lens.
Quote specific passages when giving feedback.
"""

        # Run deliberation
        return await self.deliberate(question, framings, verbose=verbose)


async def main(args):
    """CLI interface for AIN orchestrator"""

    orchestrator = CommitteeOrchestrator()
    command = args.command

    if command == "deliberate":
        question = args.question

        # Default framings for general deliberation
        framings = [
            {
                "name": "First Principles",
                "framing": "Analyze from first principles. What are the fundamental truths? What assumptions are we making? Strip away complexity to core concepts."
            },
            {
                "name": "Systems Thinking",
                "framing": "Analyze as a systems thinker. What are the feedback loops? What are the emergent properties? How does this fit in the larger system?"
            },
            {
                "name": "Practical Engineering",
                "framing": "Analyze from practical engineering perspective. What's the simplest thing that could work? What are the technical constraints? What's maintainable?"
            },
            {
                "name": "User Experience",
                "framing": "Analyze from user experience perspective. What does the user actually need? What's intuitive? Where's the friction?"
            },
            {
                "name": "Strategic Vision",
                "framing": "Analyze from strategic vision perspective. How does this serve the larger mission? What doors does it open? What's the long-term trajectory?"
            }
        ]

        result = await orchestrator.deliberate(question, framings, verbose=args.verbose)
        return result

    elif command == "review-writing":
        file_path = args.file_path
        result = await orchestrator.review_writing(file_path, verbose=args.verbose)
        return result if result else {"error": "File not found"}

    elif command == "custom-deliberate":
        question = args.question
        config_path = args.config

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            _log(f"Error loading config: {e}")
            return {"error": f"Config load failed: {str(e)}"}

        framings = config.get("framings", [])
        context = config.get("context", "")

        result = await orchestrator.deliberate(question, framings, context, verbose=args.verbose)
        return result

    else:
        return {"error": f"Unknown command: {command}"}


def _print_human_readable(result: Dict[str, Any], command: str, question: str = "", file_path: str = ""):
    """Print results in human-readable format"""
    if "error" in result:
        print(f"Error: {result['error']}")
        return

    if command == "deliberate" or command == "custom-deliberate":
        print("\n" + "="*80)
        print(f"QUESTION: {question}")
        print("="*80)

        for name, data in result["responses"].items():
            print(f"\n### {name}")
            if "framing" in data:
                print(f"*{data['framing']}*\n")
            print(data['response'])
            print()

        print("\n" + "="*80)
        print("SYNTHESIS")
        print("="*80)
        print(result["synthesis"])
        print()

    elif command == "review-writing":
        print("\n" + "="*80)
        print(f"WRITING REVIEW: {file_path}")
        print("="*80)

        for name, data in result["responses"].items():
            print(f"\n### {name}")
            print(data['response'])
            print()

        print("\n" + "="*80)
        print("SYNTHESIS")
        print("="*80)
        print(result["synthesis"])
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="AIN Committee Orchestrator - Multi-agent deliberation with dialectical synthesis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 ain_orchestrator.py deliberate "How should we implement emergence detection v2?"
  python3 ain_orchestrator.py review-writing ~/soullab-workspace/writing/blog-post.md
  python3 ain_orchestrator.py deliberate "Question" --json
  python3 ain_orchestrator.py deliberate "Question" --json-pretty

For custom deliberations, create a JSON file with framings:
{
  "framings": [
    {"name": "Agent 1", "framing": "Your lens description"},
    {"name": "Agent 2", "framing": "Your lens description"}
  ],
  "context": "Optional shared context"
}
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Deliberate command
    deliberate_parser = subparsers.add_parser("deliberate", help="Run multi-agent deliberation")
    deliberate_parser.add_argument("question", help="Question to deliberate")
    deliberate_parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    deliberate_parser.add_argument("--json-pretty", action="store_true", help="Pretty-print JSON (implies --json)")
    deliberate_parser.add_argument("--verbose", action="store_true", help="Show provider routing info")

    # Review writing command
    review_parser = subparsers.add_parser("review-writing", help="Multi-perspective writing review")
    review_parser.add_argument("file_path", help="Path to markdown file to review")
    review_parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    review_parser.add_argument("--json-pretty", action="store_true", help="Pretty-print JSON (implies --json)")
    review_parser.add_argument("--verbose", action="store_true", help="Show provider routing info")

    # Custom deliberate command
    custom_parser = subparsers.add_parser("custom-deliberate", help="Custom deliberation with config file")
    custom_parser.add_argument("question", help="Question to deliberate")
    custom_parser.add_argument("config", help="Path to JSON config file with framings")
    custom_parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    custom_parser.add_argument("--json-pretty", action="store_true", help="Pretty-print JSON (implies --json)")
    custom_parser.add_argument("--verbose", action="store_true", help="Show provider routing info")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle json-pretty (implies json)
    if hasattr(args, "json_pretty") and args.json_pretty:
        args.json = True

    # Run main and handle output
    try:
        result = asyncio.run(main(args))

        # Output results
        if args.json:
            _emit_json(_result_envelope_ok(result), pretty=args.json_pretty)
        else:
            _print_human_readable(
                result,
                args.command,
                question=getattr(args, "question", ""),
                file_path=getattr(args, "file_path", "")
            )

        sys.exit(0)

    except Exception as e:
        _log(f"❌ AIN failed: {str(e)}")

        if hasattr(args, "json") and args.json:
            _emit_json(_result_envelope_err(stage="main", err=e), pretty=getattr(args, "json_pretty", False))
        else:
            _log(f"\nError: {str(e)}")
            if hasattr(args, "verbose") and args.verbose:
                _log(traceback.format_exc())

        sys.exit(1)
