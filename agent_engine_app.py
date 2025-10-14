"""
Agent Engine Entry Point for Farm Management Agent

This file provides the Agent Engine-compatible wrapper for the farm management system.
It wraps the existing farm_management_agent in an AdkApp for deployment to Vertex AI Agent Engine.
"""

import os
import vertexai
from vertexai import agent_engines
from google.adk.agents import Agent
from src.core.agents import farm_management_agent
from src.config.config import config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Vertex AI (using config values)
PROJECT_ID = config.vertexai.project_id
LOCATION = config.vertexai.location
STAGING_BUCKET = os.getenv("STAGING_BUCKET", "gs://digitalhuman-445007-agent-staging")

logger.info(f"Initializing Vertex AI with project: {PROJECT_ID}, location: {LOCATION}")

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

# Wrap the farm management agent in an AdkApp for Agent Engine deployment
app = agent_engines.AdkApp(
    agent=farm_management_agent,
    enable_tracing=True,
)

logger.info("Farm Management Agent wrapped for Agent Engine deployment")

# Export the app for deployment
__all__ = ["app", "farm_management_agent"]