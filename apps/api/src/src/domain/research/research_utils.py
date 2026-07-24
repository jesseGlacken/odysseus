# src/domain/research/research_utils.py
"""Shared utilities for the deep research system.

Moved from src/research_utils.py to src/domain/research/research_utils.py (ODY-19 / P2.2).
The original location keeps a backward-compat shim.

Centralizes text cleaning, quality filtering, and other logic
used across deep_research.py, research_handler.py, and visual_report.py.
"""


def strip_thinking(text):
    """Strip thinking / reasoning patterns from LLM output."""
    if text is None:
        return None
    from src.text_helpers import strip_think
    return strip_think(text, prose=False, prompt_echo=True)


LOW_QUALITY_MARKERS = [
    "insufficient to",
    "content is insufficient",
    "no substantive data",
    "does not contain",
    "not relevant to",
    "no relevant information",
    "unable to extract",
    "completely unrelated",
    "boilerplate",
    "footer text",
    "cookie consent",
    "cookie banner",
    "cookie notice",
    "copyright notice",
    "copyright footer",
    "all rights reserved",
]


def is_low_quality(summary: str) -> bool:
    """Check if a finding summary indicates useless or irrelevant content."""
    try:
        if not isinstance(summary, str) or not summary:
            return True
        low = summary.lower()
        return any(marker in low for marker in LOW_QUALITY_MARKERS)
    except Exception:
        return False
