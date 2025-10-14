from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
import uuid
from src.tools.utils import JsonUtils
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
    # CallbackContext doesn't have session_id directly, so we'll use a default session
    # The actual session management is handled in main.py
    session_id = getattr(callback_context, 'session_id', None) or "default_session"
    enriched = enhanced_session_manager.get_enriched_context(session_id)
    
    # Inject memory as user context since Gemini doesn't support multiple system messages
    memory_context = f"""[CONTEXT] 🧠 **FARMER MEMORY & PROFILE**:\n{JsonUtils.safe_dumps(enriched)}\n---\n\nUser Query: """
    
    # Find the user message and prepend memory context to it
    if llm_request.contents:
        for content in llm_request.contents:
            if content.role == 'user' and content.parts and content.parts[0].text:
                # Prepend memory context to user message
                original_text = content.parts[0].text
                content.parts[0].text = memory_context + original_text
                break

    return None