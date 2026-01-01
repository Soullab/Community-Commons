#!/usr/bin/env python3
"""
Practices Kernel Service
HTTP wrapper for practice generation capability

Run: python practices_service.py
Listens on: http://localhost:5300
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request

APP_PORT = int(os.getenv("PRACTICES_PORT", "5300"))
BEHAVIOR_VERSION_DEFAULT = os.getenv("SK_DEFAULT_BEHAVIOR_VERSION", "2026-01")

app = Flask(__name__)


def now_ms() -> int:
    return int(time.time() * 1000)


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(v)
        return max(lo, min(hi, n))
    except Exception:
        return default


def normalize_str(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def pick_element_from_facet(facet_code: str) -> str:
    """Simple, stable mapping by first letter."""
    if not facet_code:
        return "aether"
    ch = facet_code[0].upper()
    return {
        "F": "fire",
        "W": "water",
        "E": "earth",
        "A": "air",
    }.get(ch, "aether")


def build_practices(
    facet_code: str,
    element_preference: Optional[str],
    duration_min: int,
    difficulty: str,
    contraindications: List[str],
) -> List[Dict[str, Any]]:
    element = (element_preference or pick_element_from_facet(facet_code)).lower().strip()
    difficulty = (difficulty or "easy").lower().strip()
    contraindications = [c for c in contraindications if isinstance(c, str) and c.strip()]

    # Minimal practice library (stable v1). Expand later.
    library: Dict[str, List[Dict[str, Any]]] = {
        "fire": [
            {
                "title": "Spark List + One Brave Step",
                "minutes": 10,
                "steps": [
                    "Write 10 sparks (ideas, desires, calls). No editing.",
                    "Circle ONE that feels alive.",
                    "Take ONE 5-minute action toward it today.",
                ],
                "tags": ["agency", "momentum", "creation"],
            },
            {
                "title": "Heat-to-Heart Breath (4-4-6)",
                "minutes": 8,
                "steps": [
                    "Inhale 4, hold 4, exhale 6.",
                    "On exhale: soften jaw/shoulders, return to the heart area.",
                    "Repeat 8-12 rounds.",
                ],
                "tags": ["regulation", "energy", "clarity"],
            },
            {
                "title": "Boundary as Blessing",
                "minutes": 12,
                "steps": [
                    "Name one place you leak energy (yes-when-no).",
                    "Write a single sentence boundary you can hold.",
                    "Rehearse it aloud 3 times.",
                ],
                "tags": ["boundaries", "power", "integrity"],
            },
        ],
        "water": [
            {
                "title": "Witness + Name the Feeling",
                "minutes": 10,
                "steps": [
                    "Write: 'Right now I feel...' and name 3 feelings.",
                    "Write: 'What this feeling wants me to know is...'",
                    "End with: 'It makes sense that...'",
                ],
                "tags": ["emotion", "witnessing", "integration"],
            },
            {
                "title": "Grief Bowl (symbolic release)",
                "minutes": 12,
                "steps": [
                    "Place a bowl/cup in front of you as a symbol.",
                    "Speak one sentence of truth into it (no fixing).",
                    "Rinse the bowl/cup with water as a release gesture.",
                ],
                "tags": ["ritual", "release", "truth"],
            },
            {
                "title": "Dream Thread Capture",
                "minutes": 8,
                "steps": [
                    "Write 5 lines: images, emotions, and one phrase.",
                    "Underline one symbol.",
                    "Ask: 'What part of me is this symbol protecting?'",
                ],
                "tags": ["dreamwork", "symbol", "depth"],
            },
        ],
        "earth": [
            {
                "title": "One Surface, One Stack",
                "minutes": 15,
                "steps": [
                    "Choose one surface (desk/table). Clear it fully.",
                    "Make one stack: 'next actions' (max 5 items).",
                    "Do the first 2-minute task immediately.",
                ],
                "tags": ["grounding", "order", "momentum"],
            },
            {
                "title": "Body Anchor Scan",
                "minutes": 10,
                "steps": [
                    "Feet -> legs -> pelvis -> belly -> chest -> face.",
                    "At each zone: relax 10% more than you think you can.",
                    "End by pressing feet gently into the floor.",
                ],
                "tags": ["embodiment", "nervous-system", "stability"],
            },
            {
                "title": "Practical Kindness Plan",
                "minutes": 12,
                "steps": [
                    "Name one need (sleep, food, support, time).",
                    "Write 2 realistic steps to meet it.",
                    "Schedule one of them in your calendar.",
                ],
                "tags": ["care", "structure", "support"],
            },
        ],
        "air": [
            {
                "title": "Thought Distillation (3 sentences)",
                "minutes": 10,
                "steps": [
                    "Sentence 1: 'Here's what I'm thinking...'",
                    "Sentence 2: 'Here's what's actually true right now...'",
                    "Sentence 3: 'The next helpful question is...'",
                ],
                "tags": ["clarity", "reframe", "insight"],
            },
            {
                "title": "Two-Column Perspective Shift",
                "minutes": 12,
                "steps": [
                    "Left: 'My fear says...' (5 bullets).",
                    "Right: 'My wisdom says...' (5 bullets).",
                    "Circle one wisdom bullet to act on.",
                ],
                "tags": ["cognition", "perspective", "agency"],
            },
            {
                "title": "Signal-to-Noise Diet (15 min)",
                "minutes": 15,
                "steps": [
                    "Pick one source of noise (tabs, news, inbox).",
                    "Close it for 15 minutes.",
                    "Write 5 lines of your own thinking before reopening.",
                ],
                "tags": ["attention", "focus", "mental-space"],
            },
        ],
        "aether": [
            {
                "title": "Still Point (90 seconds)",
                "minutes": 2,
                "steps": [
                    "Sit. Feel the center behind the sternum.",
                    "Let thoughts pass without negotiating.",
                    "Ask: 'What's the truest next step?'",
                ],
                "tags": ["presence", "inner-guide", "orientation"],
            },
            {
                "title": "Symbol of the Day",
                "minutes": 8,
                "steps": [
                    "Choose one symbol (word/image/object).",
                    "Write: 'If this symbol could speak, it would say...'",
                    "Write one action that honors it today.",
                ],
                "tags": ["symbol", "meaning", "alignment"],
            },
            {
                "title": "Integrity Check (3 gates)",
                "minutes": 10,
                "steps": [
                    "Gate 1: Does this increase coherence?",
                    "Gate 2: Does this respect consent?",
                    "Gate 3: Does this support life?",
                ],
                "tags": ["ethics", "coherence", "discernment"],
            },
        ],
    }

    candidates = library.get(element, library["aether"])

    # Return up to 3 practices, fit to duration
    out: List[Dict[str, Any]] = []
    for p in candidates[:3]:
        minutes = min(p["minutes"], duration_min) if duration_min > 0 else p["minutes"]
        out.append(
            {
                "id": gen_id("prac"),
                "facet_code": facet_code or "UNK",
                "element": element,
                "title": p["title"],
                "duration_min": minutes,
                "difficulty": difficulty,
                "steps": p["steps"],
                "tags": p["tags"],
                "contraindications": contraindications,
            }
        )
    return out


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "practices",
            "version": "1.0.0",
            "capabilities": ["generate"],
            "behavior_version_default": BEHAVIOR_VERSION_DEFAULT,
            "ts_ms": now_ms(),
        }
    )


@app.route("/generate", methods=["POST"])
def generate():
    payload = request.get_json(silent=True) or {}
    facet_code = normalize_str(payload.get("facet_code"))
    element_preference = normalize_str(payload.get("element_preference")) or None
    duration = clamp_int(payload.get("duration_available_min"), 1, 120, 15)
    difficulty = normalize_str(payload.get("difficulty")) or "easy"
    contraindications = payload.get("contraindications") or []
    if not isinstance(contraindications, list):
        contraindications = []

    behavior_version = normalize_str(payload.get("behavior_version")) or BEHAVIOR_VERSION_DEFAULT

    practices = build_practices(
        facet_code=facet_code,
        element_preference=element_preference,
        duration_min=duration,
        difficulty=difficulty,
        contraindications=contraindications,
    )

    # Trace headers (pass-through for observability)
    trace_id = request.headers.get("X-SK-Trace-Id") or ""

    return jsonify(
        {
            "practices": practices,
            "behavior_version": behavior_version,
            "trace_id": trace_id,
        }
    )


if __name__ == "__main__":
    print(f"Starting Practices Kernel Service on port {APP_PORT}")
    app.run(host="0.0.0.0", port=APP_PORT, debug=False)
