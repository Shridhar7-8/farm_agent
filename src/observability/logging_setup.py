import logging
from loguru import logger as loguru_logger
import os

def setup_logging(debug_mode: bool = True):
    """Hierarchical logging setup (file + console, no duplication)."""
    
    # Check if already configured to prevent duplicate setup
    if hasattr(setup_logging, '_configured'):
        return
    
    # Root config (file-only to avoid terminal duplication)
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler('farm_agent.log', encoding='utf-8')  # Only file logging to avoid duplication
        ]
    )
    
    # Console handler for detailed debugging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    
    # Custom loggers with console output (hierarchical, propagate=False to avoid duplication)
    loggers = [
        'farm_agent',           # Root
        'farm_agent.memory',    # Memory-related
        'farm_agent.planning',  # Planning and reflection
        'farm_agent.guardrails',# Guardrails
        'farm_agent.tools',     # General tools
        'farm_agent.tools.weather',  # Weather tool
        'farm_agent.tools.market',   # Market tool
        'farm_agent.tools.rag',      # RAG tool
        'farm_agent.tools.sheets',   # Sheets tool
        'farm_agent.llm',      # LLM interactions
        'google_adk'           # ADK-specific
    ]
    for name in loggers:
        lg = logging.getLogger(name)
        # Clear existing handlers to prevent duplicates
        lg.handlers.clear()
        lg.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        lg.addHandler(console_handler)
        lg.propagate = False  # Prevent propagation to root to avoid duplication
    
    # Enable Google ADK DEBUG logs on console
    adk_logger = logging.getLogger('google_adk')
    adk_logger.handlers.clear()  # Clear existing handlers
    adk_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    adk_logger.addHandler(console_handler)
    adk_logger.propagate = False
    
    # Configure loguru for file-only logging (no console duplication)
    loguru_logger.remove()  # Remove default console handler
    loguru_logger.add("farm_agent_loguru.log", rotation="10 MB", retention="7 days", level="INFO")
    
    # Mark as configured to prevent duplicate setup
    setup_logging._configured = True
    
    # Log setup completion
    logging.getLogger('farm_agent').info(f"Logging setup complete (debug_mode={debug_mode})")