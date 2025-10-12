"""
Farm Agent Package

A modular, pythonic farm management agent system with simple classes and functions
for beginner and intermediate level programmers.

Key Components:
- config: Configuration management
- models: Data models and processors  
- tools: Tool functions for weather, prices, etc.
- memory: Conversation and session memory
- guardrails: Safety and validation system
- agents: Agent classes and configurations
- main: Main orchestrator and interface

Usage:
    from farm_agent import farm_agent
    
    # Chat interface
    response = await farm_agent.chat("Help me with pest management")
    
    # Direct tool access
    weather = await farm_agent.get_weather("Punjab, India")
    prices = await farm_agent.get_market_prices("Rice")
"""

from .main import (
    run_agent_async_with_memory,
    main
)

from .config import config
from .models import WeatherData, MarketPriceData
from .memory import ConversationMemoryManager, EnhancedSessionManager
from .guardrails import GuardrailChecker
from .planning import (
    FarmingPlanningAgent,
    SequentialPlanningAgent, 
    ReflectionAgent
)

__version__ = "1.0.0"
__author__ = "Farm Agent Team"
__description__ = "Modular Farm Management AI Agent System"

# Main exports
__all__ = [
    # Main interface
    "run_agent_async_with_memory",
    "main",
    
    # Configuration
    "config",
    
    # Classes for advanced usage
    "ConversationMemoryManager",
    "EnhancedSessionManager",
    "GuardrailChecker",
    "FarmingPlanningAgent",
    "SequentialPlanningAgent",
    "ReflectionAgent",
    
    # Data models
    "WeatherData",
    "MarketPriceData"
]