import json
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from farm_agent.config import config
import vertexai
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger(__name__)

class JsonUtils:
    @staticmethod
    def extract_and_parse_json(text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from markdown or plain text (handles ```json blocks)."""
        if not text:
            return None
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        json_str = match.group(1) if match else text
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")
            return None

    @staticmethod
    def safe_dumps(data: Any) -> str:
        """Safely dump to JSON string."""
        try:
            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            logger.error(f"JSON dump failed: {e}")
            return str(data)

class VertexAIFactory:
    @staticmethod
    def init_vertexai(config):
        """Initialize Vertex AI once (DRY)."""
        try:
            vertexai.init(project=config.vertexai.project_id, location=config.vertexai.location)
        except Exception as e:
            logger.debug(f"Vertex AI init skipped (already done): {e}")

    @staticmethod
    def create_model(system_instruction: str, model_name: str = None, tools=None) -> GenerativeModel:
        """Factory for models (avoids repetition)."""
        model_name = model_name or config.vertexai.model_name
        VertexAIFactory.init_vertexai(config)
        return GenerativeModel(
            model_name=model_name,
            tools=tools,
            system_instruction=system_instruction
        )