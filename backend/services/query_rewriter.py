"""
Rule-first follow-up query rewriting.

The goal is conservative context retention: fill in missing intent from recent
chat context without inventing filters the user did not ask for.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


FOLLOW_UP_PATTERNS = [
    re.compile(r"^\s*(what|how)\s+about\s+(?P<target>.+?)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*(and|also)\s+(for|in|at)\s+(?P<target>.+?)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*(for|in|at)\s+(?P<target>.+?)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*(same|repeat)\s+(for|in|at)\s+(?P<target>.+?)\??\s*$", re.IGNORECASE),
]

METRIC_TERMS = {
    "revenue",
    "sales",
    "production",
    "units",
    "alerts",
    "issues",
    "forecast",
    "tasks",
    "schedule",
}

AGGREGATION_TERMS = {
    "total",
    "average",
    "avg",
    "count",
    "highest",
    "lowest",
    "top",
    "trend",
    "compare",
}

TIME_PATTERN = re.compile(
    r"\b(q[1-4]\s+\d{4}|q[1-4]|week\s+\d+|w\d+|this\s+\w+|last\s+\w+|next\s+\w+|"
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"\d{4})\b",
    re.IGNORECASE,
)


@dataclass
class RewriteResult:
    refined_query: str
    was_rewritten: bool
    reason: str
    needs_clarification: bool = False
    context_block: dict[str, Any] | None = None


def rewrite_query(current_query: str, context_block: dict[str, Any] | list[dict[str, Any]]) -> RewriteResult:
    """
    Convert incomplete follow-ups into standalone queries.

    Examples:
      "Total revenue in Q1 2026" + "What about Dearborn?"
      -> "Total revenue in Q1 2026 for Dearborn"
    """
    current = _clean_query(current_query)
    context = _normalise_context(context_block)
    previous_query = _latest_refined_query(context)

    if not current:
        return RewriteResult(current_query, False, "empty_query", needs_clarification=True)

    if not previous_query:
        return RewriteResult(current, False, "no_context", context_block=_as_context_block(context_block, current))

    if _is_standalone(current):
        return RewriteResult(current, False, "standalone_query", context_block=_as_context_block(context_block, current))

    follow_up_target = _extract_follow_up_target(current)
    if follow_up_target:
        refined = _merge_follow_up(previous_query, follow_up_target)
        return RewriteResult(
            refined_query=refined,
            was_rewritten=refined != current,
            reason="follow_up_filter_merge",
            context_block=_as_context_block(context_block, current),
        )

    if _looks_like_bare_entity(current):
        refined = _merge_follow_up(previous_query, current)
        return RewriteResult(
            refined_query=refined,
            was_rewritten=True,
            reason="bare_entity_follow_up",
            context_block=_as_context_block(context_block, current),
        )

    if len(current.split()) <= 4 and not _has_domain_anchor(current):
        return RewriteResult(
            refined_query=current,
            was_rewritten=False,
            reason="ambiguous_short_follow_up",
            needs_clarification=True,
            context_block=_as_context_block(context_block, current),
        )

    return RewriteResult(current, False, "no_rewrite_needed", context_block=_as_context_block(context_block, current))


def build_prompt_context(context_block: dict[str, Any], refined_query: str) -> list[dict[str, str]]:
    """
    Convert memory context to a chat-history shape accepted by llm_service.
    The refined query remains the user message; this block gives the LLM the
    structured prior state without relying on client-side history.
    """
    previous_context = context_block.get("previous_context", []) if context_block else []
    summary = context_block.get("conversation_summary", "") if context_block else ""

    content = {
        "previous_context": previous_context,
        "conversation_summary": summary,
        "current_query": context_block.get("current_query") if context_block else refined_query,
        "refined_query": refined_query,
        "instruction": "Use prior context only to resolve references. Do not add filters not present in prior context or the current query.",
    }

    return [{"role": "user", "content": f"CONVERSATION_CONTEXT:\n{content}"}]


def _normalise_context(context_block: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(context_block, dict):
        return context_block.get("previous_context", []) or []
    return context_block or []


def _as_context_block(context_block: dict[str, Any] | list[dict[str, Any]], current_query: str) -> dict[str, Any]:
    if isinstance(context_block, dict):
        return {**context_block, "current_query": current_query}
    return {"previous_context": context_block or [], "current_query": current_query}


def _latest_refined_query(context: list[dict[str, Any]]) -> str | None:
    for item in reversed(context):
        query = item.get("refined_query") or item.get("query")
        if query:
            return str(query)
    return None


def _clean_query(query: str) -> str:
    return re.sub(r"\s+", " ", query or "").strip()


def _is_standalone(query: str) -> bool:
    q = query.lower()
    has_metric = any(term in q for term in METRIC_TERMS)
    has_aggregation = any(term in q for term in AGGREGATION_TERMS)
    return has_metric or (has_aggregation and bool(TIME_PATTERN.search(q)))


def _extract_follow_up_target(query: str) -> str | None:
    for pattern in FOLLOW_UP_PATTERNS:
        match = pattern.match(query)
        if match:
            return _clean_target(match.group("target"))
    return None


def _looks_like_bare_entity(query: str) -> bool:
    if query.strip().lower().rstrip("?.,") in {"same", "repeat", "it", "that", "there", "them"}:
        return False
    if len(query.split()) > 3:
        return False
    if _has_domain_anchor(query):
        return False
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\s\-.&]+[?]?$", query.strip()))


def _has_domain_anchor(query: str) -> bool:
    q = query.lower()
    return any(term in q for term in METRIC_TERMS | AGGREGATION_TERMS) or bool(TIME_PATTERN.search(q))


def _clean_target(target: str) -> str:
    target = _clean_query(target).rstrip("?.,")
    target = re.sub(r"^(for|in|at)\s+", "", target, flags=re.IGNORECASE)
    return target


def _merge_follow_up(previous_query: str, target: str) -> str:
    target = _clean_target(target)
    if not target:
        return previous_query

    if _is_time_target(target):
        return _replace_or_append_time(previous_query, target)

    return _replace_or_append_filter(previous_query, target)


def _is_time_target(target: str) -> bool:
    return bool(TIME_PATTERN.search(target.lower()))


def _replace_or_append_time(previous_query: str, target: str) -> str:
    if TIME_PATTERN.search(previous_query):
        return TIME_PATTERN.sub(target, previous_query, count=1)
    return f"{previous_query} in {target}"


def _replace_or_append_filter(previous_query: str, target: str) -> str:
    filter_pattern = re.compile(
        r"\b(for|in|at)\s+([A-Z][A-Za-z0-9\-&]*(?:\s+[A-Z][A-Za-z0-9\-&]*){0,2})\b"
    )
    matches = list(filter_pattern.finditer(previous_query))
    if matches:
        last = matches[-1]
        existing = last.group(2)
        if not TIME_PATTERN.search(existing):
            return previous_query[: last.start(2)] + target + previous_query[last.end(2) :]

    if re.search(r"\b(by|per)\s+(plant|model|department|week|month|quarter)\b", previous_query, re.IGNORECASE):
        return f"{previous_query} filtered for {target}"
    return f"{previous_query} for {target}"
