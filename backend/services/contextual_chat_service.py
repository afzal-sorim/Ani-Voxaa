"""
Context-aware chat orchestration.

This wrapper keeps the existing automotive agent intact while adding:
1. session memory retrieval
2. follow-up query rewriting
3. structured prompt context injection
4. post-response memory persistence
"""

from __future__ import annotations

from typing import AsyncGenerator

try:
    from backend.agents.automotive_agent import process_query, stream_query
    from backend.services.memory_manager import get_memory_manager
    from backend.services.query_rewriter import build_prompt_context, rewrite_query
except ImportError:
    from agents.automotive_agent import process_query, stream_query
    from services.memory_manager import get_memory_manager
    from services.query_rewriter import build_prompt_context, rewrite_query


async def process_contextual_query(
    query: str,
    session_id: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    memory = get_memory_manager()
    context_block = memory.get_context_block(session_id, query)
    rewrite = rewrite_query(query, context_block)

    if rewrite.needs_clarification:
        response = (
            "I can use the previous conversation, but this follow-up is still ambiguous. "
            "Which metric, plant, model, or time period should I apply it to?"
        )
        memory.append_interaction(
            session_id=session_id,
            user_query=query,
            refined_query=query,
            generated_query=None,
            response=response,
            metadata={"rewrite_reason": rewrite.reason, "needs_clarification": True},
        )
        return {
            "response": response,
            "refined_query": query,
            "context_used": context_block,
            "was_rewritten": False,
        }

    refined_query = rewrite.refined_query
    injected_history = _merge_histories(
        build_prompt_context(context_block, refined_query),
        conversation_history,
    )
    response = await process_query(refined_query, injected_history)

    memory.append_interaction(
        session_id=session_id,
        user_query=query,
        refined_query=refined_query,
        generated_query=refined_query,
        response=response,
        metadata={"rewrite_reason": rewrite.reason, "was_rewritten": rewrite.was_rewritten},
    )

    return {
        "response": response,
        "refined_query": refined_query,
        "context_used": context_block,
        "was_rewritten": rewrite.was_rewritten,
    }


async def stream_contextual_query(
    query: str,
    session_id: str,
    conversation_history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    memory = get_memory_manager()
    context_block = memory.get_context_block(session_id, query)
    rewrite = rewrite_query(query, context_block)

    if rewrite.needs_clarification:
        response = (
            "I can use the previous conversation, but this follow-up is still ambiguous. "
            "Which metric, plant, model, or time period should I apply it to?"
        )
        memory.append_interaction(
            session_id=session_id,
            user_query=query,
            refined_query=query,
            generated_query=None,
            response=response,
            metadata={"rewrite_reason": rewrite.reason, "needs_clarification": True},
        )
        yield response
        return

    refined_query = rewrite.refined_query
    injected_history = _merge_histories(
        build_prompt_context(context_block, refined_query),
        conversation_history,
    )

    chunks: list[str] = []
    async for token in stream_query(refined_query, injected_history):
        chunks.append(token)
        yield token

    response = "".join(chunks)
    memory.append_interaction(
        session_id=session_id,
        user_query=query,
        refined_query=refined_query,
        generated_query=refined_query,
        response=response,
        metadata={"rewrite_reason": rewrite.reason, "was_rewritten": rewrite.was_rewritten},
    )


def _merge_histories(
    memory_history: list[dict],
    client_history: list[dict] | None,
) -> list[dict]:
    history: list[dict] = []
    history.extend(memory_history)
    if client_history:
        history.extend(client_history[-8:])
    return history
