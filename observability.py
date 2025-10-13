"""
Observability and tracing integration for the Farm Management System.
This module integrates Laminar for comprehensive LLM and agent tracing.
"""

import os
import logging
import asyncio
import inspect
from typing import Optional
from functools import wraps

# Initialize logger
logger = logging.getLogger('farm_agent.observability')

# Global flag to track initialization
_laminar_initialized = False

def initialize_laminar() -> bool:
    """
    Initialize Laminar tracing with proper error handling.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global _laminar_initialized
    
    if _laminar_initialized:
        logger.debug("Laminar already initialized, skipping...")
        return True
    
    try:
        # Check for API key
        api_key = os.getenv('LMNR_PROJECT_API_KEY')
        if not api_key:
            logger.warning("LMNR_PROJECT_API_KEY not found in environment variables. Laminar tracing disabled.")
            return False
        
        # Import and initialize Laminar
        from lmnr import Laminar
        
        Laminar.initialize(project_api_key=api_key)
        
        _laminar_initialized = True
        logger.info("✅ Laminar observability initialized successfully")
        logger.info("🔍 LLM calls and agent interactions will now be traced")
        return True
        
    except ImportError as e:
        logger.warning(f"Laminar not available: {e}. Continuing without observability.")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Laminar: {e}. Continuing without observability.")
        return False

def observe_if_available(name: Optional[str] = None):
    """
    Decorator that applies Laminar observe functionality if available.
    Falls back gracefully if Laminar is not available or not initialized.
    Handles both sync and async functions properly by avoiding pickle issues.
    
    Args:
        name: Optional name for the span. If not provided, uses function name.
    
    Returns:
        Decorator function that may or may not apply tracing
    """
    def decorator(func):
        # Check if Laminar is available and initialized
        if not _laminar_initialized:
            # Return the original function without modification
            return func
        
        try:
            from lmnr import observe
            
            # Check if function is async
            if inspect.iscoroutinefunction(func):
                # For async functions, we'll skip Laminar's observe decorator to avoid pickle issues
                # Laminar's automatic instrumentation will still capture LLM calls within these functions
                logger.debug(f"Skipping observe decorator for async function {func.__name__} (automatic instrumentation active)")
                return func
            else:
                # For sync functions, apply Laminar observe safely
                try:
                    if name:
                        return observe(name=name)(func)
                    else:
                        return observe()(func)
                except Exception as observe_error:
                    logger.debug(f"Failed to apply observe decorator to {func.__name__}: {observe_error}")
                    return func
                
        except ImportError:
            logger.debug("Laminar not available, returning original function")
            return func
        except Exception as e:
            logger.debug(f"Failed to apply observe decorator: {e}, returning original function")
            return func
    
    return decorator

def is_observability_enabled() -> bool:
    """
    Check if observability is currently enabled.
    
    Returns:
        bool: True if Laminar is initialized and available
    """
    return _laminar_initialized

def log_observability_status():
    """Log the current observability status for debugging."""
    if _laminar_initialized:
        logger.info("🔍 Observability Status: ENABLED - Laminar tracing active")
        logger.info("📊 Metrics being tracked: LLM calls, agent interactions, token usage, latency")
    else:
        logger.info("🔍 Observability Status: DISABLED - Add LMNR_PROJECT_API_KEY to enable tracing")
        logger.info("ℹ️  To enable: Set LMNR_PROJECT_API_KEY environment variable with your Laminar API key")