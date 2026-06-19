"""Kubernetes investigation layer (placeholder).

Phase 2 implements read-only, JSON-parsed kubectl evidence gathering. Per CLAUDE.md:
read-only only (no apply/edit/delete/scale/patch), every call uses ``-o json``, and
LLM-suggested commands are never executed.
"""


def inspect_pods():
    """Placeholder — implemented in Phase 2."""
    ...
