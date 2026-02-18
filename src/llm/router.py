"""
Hybrid LLM Router — decides between local (Ollama) and cloud (Claude) backends.

Uses keyword heuristics to classify query complexity. Simple queries go to
the local Qwen3 model for low latency; complex queries route to Claude API
for better reasoning.

The classifier is intentionally simple (<1ms, no ML model, CPU-only).
"""

import re
from typing import Generator

# Patterns that indicate a COMPLEX query (route to cloud)
CLOUD_PATTERNS = [
    # Reasoning / analysis
    r"\bwhy\b",
    r"\bexplain\b",
    r"\bcompare\b",
    r"\banalyz[es]?\b",
    r"\bdifference between\b",
    r"\bpros and cons\b",
    # Creative / generative
    r"\bwrite\b",
    r"\bcreate\b",
    r"\bcompose\b",
    r"\bdraft\b",
    r"\bsummariz[es]?\b",
    # Multi-step / planning
    r"\bhow would\b",
    r"\bwhat if\b",
    r"\bhelp me\b",
    r"\bstep by step\b",
    r"\bwalk me through\b",
    # Code / technical
    r"\bdebug\b",
    r"\brefactor\b",
    r"\bimplement\b",
    r"\barchitect\b",
]

# Patterns that indicate a SIMPLE query (keep local)
LOCAL_PATTERNS = [
    # Time / date
    r"\bwhat time\b",
    r"\bwhat day\b",
    r"\bwhat date\b",
    # Quick facts
    r"\bwhat is\b",
    r"\bwho is\b",
    r"\bwhere is\b",
    r"\bdefine\b",
    # Commands
    r"\btimer\b",
    r"\bremind\b",
    r"\balarm\b",
    r"\bplay\b",
    r"\bstop\b",
    r"\bpause\b",
    r"\bvolume\b",
    # Greetings / small talk
    r"\b(hello|hi|hey|thanks|thank you|good morning|good night)\b",
    # Yes/no
    r"^(yes|no|yeah|nah|sure|okay|ok)[\s.!?]*$",
]

# Word count thresholds
SHORT_QUERY_WORDS = 12   # Queries under this lean local
LONG_QUERY_WORDS = 25    # Queries over this lean cloud

# Compiled regex for performance
_cloud_re = [re.compile(p, re.IGNORECASE) for p in CLOUD_PATTERNS]
_local_re = [re.compile(p, re.IGNORECASE) for p in LOCAL_PATTERNS]


def classify(text: str) -> str:
    """
    Classify a query as "local" or "cloud".

    Returns:
        "local" or "cloud"
    """
    text = text.strip()
    if not text:
        return "local"

    word_count = len(text.split())

    # Very short queries almost always belong local
    if word_count <= 5:
        # Unless they match a cloud pattern
        for pattern in _cloud_re:
            if pattern.search(text):
                return "cloud"
        return "local"

    # Check for explicit local patterns first
    for pattern in _local_re:
        if pattern.search(text):
            return "local"

    # Check for cloud patterns
    cloud_signals = sum(1 for p in _cloud_re if p.search(text))

    # Any cloud signal without a competing local signal → cloud
    if cloud_signals >= 1:
        return "cloud"

    # Long queries with no strong signal lean cloud
    if word_count >= LONG_QUERY_WORDS:
        return "cloud"

    return "local"


class QueryRouter:
    """
    Routes queries to the appropriate LLM backend.

    Modes:
        "local"  — Always use Ollama (no cloud calls)
        "cloud"  — Always use Claude API
        "hybrid" — Classify and route dynamically
    """

    def __init__(
        self,
        mode: str = "hybrid",
        local_fn=None,
        cloud_fn=None,
    ):
        if mode not in ("local", "cloud", "hybrid"):
            raise ValueError(f"Invalid router mode: {mode}")

        self.mode = mode
        self._local_fn = local_fn
        self._cloud_fn = cloud_fn

    def route(self, text: str) -> Generator[str, None, None]:
        """
        Route a query to the appropriate backend and stream the response.

        Yields:
            Response text chunks from the selected backend.
        """
        backend = self._decide(text)

        if backend == "cloud" and self._cloud_fn is not None:
            yield from self._cloud_fn(text)
        else:
            # Fallback to local if cloud is unavailable
            yield from self._local_fn(text)

    def _decide(self, text: str) -> str:
        """Decide which backend to use."""
        if self.mode == "local":
            return "local"
        if self.mode == "cloud":
            return "cloud"
        return classify(text)

    def explain(self, text: str) -> dict:
        """Return routing decision with reasoning (for debug/metrics)."""
        decision = self._decide(text)
        cloud_matches = [p.pattern for p in _cloud_re if p.search(text)]
        local_matches = [p.pattern for p in _local_re if p.search(text)]
        return {
            "decision": decision,
            "mode": self.mode,
            "word_count": len(text.split()),
            "cloud_signals": cloud_matches,
            "local_signals": local_matches,
        }
