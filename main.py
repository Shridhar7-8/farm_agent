import asyncio
import uuid
import logging
import signal
import sys
import re
from typing import Dict, Any
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.observability.logging_setup import setup_logging
from src.config.config import config
from src.core.agents import farm_management_agent
from src.core.memory import enhanced_session_manager
from src.tools.utils import logger, JsonUtils
from src.core.processors import cleanup_all_processors
from src.observability.observability import initialize_laminar, observe_if_available, log_observability_status, is_observability_enabled
from src.core.warmup import warmup_all

setup_logging(debug_mode=True)  # Toggle via env

# Initialize Laminar observability (non-blocking)
initialize_laminar()

# Global cleanup flag
cleanup_in_progress = False

async def cleanup_application():
    """Clean up all application resources."""
    global cleanup_in_progress
    if cleanup_in_progress:
        return
    
    cleanup_in_progress = True
    logger.info("Starting application cleanup...")
    
    try:
        # Clean up HTTP sessions and processors
        await cleanup_all_processors()
        
        # Force cleanup of any remaining aiohttp sessions
        import gc
        import aiohttp
        
        # Collect garbage to ensure sessions are cleaned up
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
        
        # Try to close any remaining aiohttp sessions
        for obj in gc.get_objects():
            if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
                try:
                    await obj.close()
                    logger.info("Force-closed lingering aiohttp session")
                except Exception as session_error:
                    logger.warning(f"Failed to close lingering session: {session_error}")
        
        logger.info("Application cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during application cleanup: {e}")
    finally:
        cleanup_in_progress = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n\nShutdown signal received. Cleaning up...")
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    
    # Force cleanup and exit immediately
    try:
        # Try to run cleanup synchronously to avoid async issues
        import asyncio
        if asyncio._get_running_loop() is None:
            asyncio.run(cleanup_application())
        else:
            # If we're in an async context, we need to handle it differently
            print("Forcing immediate cleanup...")
            logger.warning("Forcing immediate cleanup due to signal")
    except Exception as e:
        logger.error(f"Signal handler cleanup failed: {e}")
    finally:
        print("Cleanup completed. Goodbye!")
        sys.exit(0)

@observe_if_available(name="extract_conversation_context")
def extract_context_from_conversation(query: str, response: str) -> Dict[str, Any]:
    """Simple keyword-based context extraction for memory enhancement."""
    extracted = {}
    query_lower = query.lower()
    response_lower = response.lower()
    
    # Extract crop mentions
    crop_mentions = []
    crop_keywords = ['rice', 'wheat', 'cotton', 'corn', 'maize', 'soybean', 'basmati', 'jasmine']
    for crop in crop_keywords:
        if crop in query_lower or crop in response_lower:
            crop_mentions.append(crop)
    if crop_mentions:
        extracted['crops'] = crop_mentions
    
    # Extract location mentions
    location_keywords = ['punjab', 'haryana', 'up', 'uttar pradesh', 'bihar', 'maharashtra']
    for location in location_keywords:
        if location in query_lower or location in response_lower:
            extracted['location'] = location.title()
            break
    
    return extracted

def _format_for_speech(response_text: str) -> str:
    if not response_text:
        return response_text

    lines = [line.strip() for line in response_text.splitlines() if line.strip()]

    if len(lines) == 1:
        return lines[0]

    summary_line = re.sub(r"^[\-*•\d.\s]+", "", lines[0])
    details = []
    for line in lines[1:]:
        cleaned = re.sub(r"^[\-*•\d.\s]+", "", line)
        if cleaned:
            cleaned = cleaned.replace("**", "")
            details.append(cleaned)

    if not details:
        return summary_line

    detail_sentence = "; ".join(details)
    return f"{summary_line}. {detail_sentence}"


@observe_if_available(name="farm_agent_execution")
async def run_agent_async_with_memory(runner: InMemoryRunner, user_query: str, user_id: str = "farmer_123") -> str:
    """Core runner (streamlined event handling)."""
    session, memory_manager = await enhanced_session_manager.get_or_create_session(user_id, runner)
    session_data = enhanced_session_manager.active_sessions.get(user_id)
    session_id = session_data['session_id'] if session_data else str(uuid.uuid4())
    
    final_result = ""
    try:
        print(f"\n{'='*70}")
        print(f"📋 Processing Query: '{user_query}'")
        print(f"{'-'*70}")
        
        # Get current conversation context for logging
        context = memory_manager.get_current_context()
        if context['farmer_profile'].get('name'):
            print(f"🧠 Memory: Recognized {context['farmer_profile']['name']}")
        if context['farmer_profile'].get('crops'):
            print(f"🌾 Context: {', '.join(context['farmer_profile']['crops'])}")
        
        logger.info(f"Starting agent execution loop with memory context")
        
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id,
            new_message=types.Content(role='user', parts=[types.Part(text=user_query)])
        ):
            logger.debug(f"Processing event: {type(event)}")
            
            # Improved event processing with better error handling
            try:
                if hasattr(event, 'is_final_response') and event.is_final_response():
                    logger.debug("Found final response event")
                    
                    # Try multiple ways to extract content
                    content_found = False
                    
                    # Method 1: Direct content access
                    if hasattr(event, 'content') and event.content is not None:
                        if hasattr(event.content, 'parts') and event.content.parts is not None and len(event.content.parts) > 0:
                            if hasattr(event.content.parts[0], 'text') and event.content.parts[0].text:
                                final_result = event.content.parts[0].text
                                content_found = True
                                logger.debug(f"Method 1: Extracted text: {final_result[:100]}...")
                    
                    # Method 2: Try alternative content access
                    if not content_found and hasattr(event, 'data'):
                        try:
                            if hasattr(event.data, 'content'):
                                final_result = str(event.data.content)
                                content_found = True
                                logger.debug(f"Method 2: Extracted from data.content: {final_result[:100]}...")
                        except Exception as e:
                            logger.debug(f"Method 2 failed: {e}")
                    
                    # Method 3: String representation fallback
                    if not content_found:
                        try:
                            event_str = str(event)
                            if event_str and len(event_str) > 50:
                                final_result = event_str
                                content_found = True
                                logger.debug(f"Method 3: Using string representation: {final_result[:100]}...")
                        except Exception as e:
                            logger.debug(f"Method 3 failed: {e}")
                    
                    if not content_found:
                        final_result = "✅ **Planning System Activated**: Your complex farming query was processed by the intelligent planning system. The response was generated but there was a display issue. Please try your query again."
                        logger.warning("No content found in final response, using fallback message")
                    
                    break
                else:
                    logger.debug("Event is not final response, continuing...")
                    
            except Exception as event_error:
                logger.error(f"Error processing event: {event_error}", exc_info=True)
                continue
        
        # Add conversation to memory after getting response
        if final_result and user_query:
            # Extract any context from the response for memory enhancement
            extracted_context = extract_context_from_conversation(user_query, final_result)
            
            # Add to memory
            enhanced_session_manager.add_conversation_to_memory(
                session_id,
                user_query,
                final_result,
                extracted_context
            )
            
            # Show memory status
            memory_stats = memory_manager.get_conversation_count()
            print(f"💭 Memory: {memory_stats['recent_conversations']} recent conversations" +
                  (f" + summary" if memory_stats['has_summary'] else ""))
        
        # Display result if we got one
        if final_result:
            spoken_text = _format_for_speech(final_result)
            print("\n✅ Spoken Response:\n" + spoken_text)
        else:
            print(f"\n⚠️  No response content received")
            
        print(f"{'='*70}\n")
        return final_result
        
    except RuntimeError as e:
        if "aclose(): asynchronous generator is already running" in str(e):
            logger.debug(f"Cleanup warning occurred: {e}")
            return final_result
        else:
            logger.error(f"RuntimeError occurred: {e}", exc_info=True)
            raise
    except Exception as e:
        error_msg = f"An error occurred: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"❌ {error_msg}")
        
        # Ensure cleanup if critical error occurs
        if "ClientSession" in str(e) or "unclosed" in str(e).lower():
            logger.warning("Detected HTTP session issue, triggering cleanup")
            try:
                await cleanup_application()
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed: {cleanup_error}")
        
        return error_msg

@observe_if_available(name="farm_management_system")
async def main():
    """Main function demonstrating the farm management system with guardrails."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    root_logger = logging.getLogger('farm_agent')
    root_logger.info("Starting Google ADK Farm Management System")
    root_logger.info("System components: Guardrails, Memory, Planning, RAG, Tools")
    root_logger.debug("🔍 DEBUG MODE ACTIVE: Full LLM interaction logging enabled")
    
    # Log observability status
    if is_observability_enabled():
        log_observability_status()
    
    divider = "=" * 70
    print(divider)
    print("[DEBUG MODE] GOOGLE ADK FARM MANAGEMENT SYSTEM WITH GUARDRAILS")
    print(divider)
    print("[DEBUG MODE] Detailed LLM interactions are logged")
    if is_observability_enabled():
        print("[OBSERVABILITY] Laminar tracing active for performance monitoring")
    else:
        print("[OBSERVABILITY] Disabled. Set LMNR_PROJECT_API_KEY to enable tracing")
    print(divider)
    print("\nSystem capabilities:")
    print("  - Input validation and safety guardrails")
    print("  - Domain-specific enforcement (agriculture only)")
    print("  - Protection against jailbreaking attempts")
    print("  - Privacy and security checks")
    if is_observability_enabled():
        print("  - Performance monitoring and LLM call tracing")
    print(divider)

    runner = InMemoryRunner(farm_management_agent, app_name="farm_management_app")
    
    # Example farmer info (for demo; in production, load from session)
    farmer_info = {
        "name": "Rajesh Kumar",
        "location": "Punjab",
        "crops": ["Wheat", "Rice", "Cotton"],
        "farm_size": "10 acres"
    }
    
    print("\nWelcome, Rajesh Kumar!")
    print(f"  Location: {farmer_info['location']}")
    print(f"  Crops: {', '.join(farmer_info['crops'])}")
    print(f"  Farm Size: {farmer_info['farm_size']}")
    print("\n" + divider)
    print("Capabilities overview:")
    print("  - Sequential planning with integrated reflection")
    print("  - Real-time progress visibility")
    print("  - Quality assurance and iterative improvement")
    print("  - Guardrails with domain enforcement")
    print("\nExample queries:")
    print("  - Create a plan to manage pest outbreak in cotton")
    print("  - Convert 5 acres from rice to organic vegetables")
    print("  - Step-by-step drip irrigation setup")
    print("  - Weather forecast for your farm location")
    print("  - Current market prices for your crops")
    print("  - Retrieve customer data from records")
    print("\nSequential planning phases:")
    print("  1. Planning")
    print("  2. Reflection")
    print("  3. Refinement")
    print("  4. Delivery")
    print("\nType 'exit' or 'quit' to end the session.")
    print(divider)
    
    # Interactive query loop
    while True:
        try:
            print("\n" + "-" * 70)
            user_query = input("Your Question: ").strip()
            
            if not user_query:
                continue
                
            if user_query.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                print("\nCleaning up system resources...")
                await cleanup_application()
                print("Thank you for using the Farm Management System!")
                print("Happy Farming!\n")
                break
            
            # Process the query with memory-enhanced system
            result = await run_agent_async_with_memory(runner, user_query, user_id="farmer_123")
            
        except KeyboardInterrupt:
            print("\n\nSession interrupted. Cleaning up...")
            await cleanup_application()
            print("Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue

if __name__ == "__main__":
    try:
        asyncio.run(warmup_all())
        asyncio.run(main())
    except Exception as e:
        print(f"\nApplication error: {e}")
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        # Force cleanup on exit
        try:
            print("\nPerforming final system cleanup...")
            asyncio.run(cleanup_application())
            print("Cleanup completed.")
        except Exception as cleanup_error:
            print(f"Cleanup warning: {cleanup_error}")
            logger.warning(f"Final cleanup warning: {cleanup_error}")

# Test Stub (principle: Test Everything)
import unittest

class TestRefactoredUtils(unittest.TestCase):
    def test_json_extract(self):
        text = "```json {\"key\": \"value\"} ```"
        self.assertEqual(JsonUtils.extract_and_parse_json(text), {"key": "value"})

if __name__ == "__main__":
    unittest.main(argv=[''], exit=False)