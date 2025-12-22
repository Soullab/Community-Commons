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

        print(f"\n🧠 Spawning committee with {len(framings)} agents...")

        # Show available providers
        available = router.get_available_providers()
        if verbose:
            print(f"   Available providers: {', '.join([p[1].name for p in available])}")
        print()

        # Create agents
        agents = [
            Agent(f["name"], f["framing"], context)
            for f in framings
        ]

        # Parallel execution
        print("⚡ Running parallel deliberation...")
        start_time = datetime.now()

        responses = await asyncio.gather(*[
            agent.respond(question, verbose=False) for agent in agents  # Don't spam verbose per agent
        ])

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"✅ Collected {len(responses)} responses in {elapsed:.1f}s\n")

        # Build response dict
        agent_responses = {
            agents[i].name: {
                "framing": agents[i].framing,
                "response": responses[i]
            }
            for i in range(len(agents))
        }

        # Synthesize
        print("🔮 Generating dialectical synthesis...")
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
            print(f"Error: File not found: {file_path}")
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


async def main():
    """CLI interface for AIN orchestrator"""

    if len(sys.argv) < 2:
        print("""
AIN Committee Orchestrator

Usage:
  python3 ain_orchestrator.py deliberate "<question>"
  python3 ain_orchestrator.py review-writing <file-path>
  python3 ain_orchestrator.py custom-deliberate "<question>" <config.json>

Examples:
  python3 ain_orchestrator.py deliberate "How should we implement emergence detection v2?"
  python3 ain_orchestrator.py review-writing ~/soullab-workspace/writing/blog-post.md

For custom deliberations, create a JSON file with framings:
{
  "framings": [
    {"name": "Agent 1", "framing": "Your lens description"},
    {"name": "Agent 2", "framing": "Your lens description"}
  ],
  "context": "Optional shared context"
}
""")
        sys.exit(1)

    orchestrator = CommitteeOrchestrator()
    command = sys.argv[1]

    if command == "deliberate":
        if len(sys.argv) < 3:
            print("Error: Question required")
            sys.exit(1)

        question = sys.argv[2]

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

        result = await orchestrator.deliberate(question, framings)

        # Print results
        print("\n" + "="*80)
        print(f"QUESTION: {question}")
        print("="*80)

        for name, data in result["responses"].items():
            print(f"\n### {name}")
            print(f"*{data['framing']}*\n")
            print(data['response'])
            print()

        print("\n" + "="*80)
        print("SYNTHESIS")
        print("="*80)
        print(result["synthesis"])
        print()

    elif command == "review-writing":
        if len(sys.argv) < 3:
            print("Error: File path required")
            sys.exit(1)

        file_path = sys.argv[2]
        result = await orchestrator.review_writing(file_path)

        if result:
            # Print results
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

    elif command == "custom-deliberate":
        if len(sys.argv) < 4:
            print("Error: Question and config file required")
            sys.exit(1)

        question = sys.argv[2]
        config_path = sys.argv[3]

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

        framings = config.get("framings", [])
        context = config.get("context", "")

        result = await orchestrator.deliberate(question, framings, context)

        # Print results
        print("\n" + "="*80)
        print(f"QUESTION: {question}")
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

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
