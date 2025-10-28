from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
import uuid
from src.tools.utils import JsonUtils
from src.config.config import config
from typing import Optional
from src.core.guardrails import guardrail_checker, GuardrailEvaluation
from src.core.memory import enhanced_session_manager
from src.tools.utils import logger

def combined_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """Merged: Guardrail -> Memory Injection (DRY, orthogonal)."""
    # Extract user message (robust)
    last_message = ""
    if llm_request and llm_request.contents:
        last_content = llm_request.contents[-1]
        if last_content.role == 'user' and last_content.parts:
            last_message = last_content.parts[0].text or ""

    # Guardrail
    evaluation = guardrail_checker.check_violations(last_message)
    logger.info(f"Guardrail: {evaluation.compliance_status} (Risk: {evaluation.risk_level})")
    if evaluation.compliance_status == "non-compliant":
        blocking_msg = f"""🛡️ **Request Blocked**: {evaluation.evaluation_summary}\n\nViolations:\n{chr(10).join(evaluation.triggered_policies)}\n\nValid topics: crops, weather, markets..."""  # [Shortened]
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=blocking_msg)]))

    # Memory Injection (farmer + enriched)
    session_id = getattr(callback_context, 'session_id', None) or "default_session"
    enriched = enhanced_session_manager.get_enriched_context(session_id)

    if enriched:
        summarized_context = enriched.get("conversation_summary", "") or "No previous conversation history."
        if len(summarized_context) > config.performance.max_memory_summary_chars:
            summarized_context = summarized_context[: config.performance.max_memory_summary_chars] + "..."

        recent_conversations = enriched.get("recent_conversations", "")
        if isinstance(recent_conversations, str):
            if len(recent_conversations) > config.performance.max_memory_recent_chars:
                recent_conversations = recent_conversations[: config.performance.max_memory_recent_chars] + "..."
        elif isinstance(recent_conversations, list):
            recent_conversations = recent_conversations[: config.performance.max_memory_context_conversations]

        filtered_context = {
            "farmer_profile": enriched.get("farmer_profile", {}),
            "conversation_summary": summarized_context,
            "recent_conversations": recent_conversations,
            "memory_status": enriched.get("memory_status", "")
        }

        memory_context = f"""[MEMORY]\n{JsonUtils.safe_dumps(filtered_context)}\n[/MEMORY]\n\nUser Query: """

        if llm_request.contents:
            for content in llm_request.contents:
                if content.role == 'user' and content.parts and content.parts[0].text:
                    original_text = content.parts[0].text
                    content.parts[0].text = memory_context + original_text
                    break

    return None