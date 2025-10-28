import asyncio
import logging

from src.config.config import config
from src.tools.tools import warmup_rag_model
from src.core.planning import warmup_planning_models
from src.tools.utils import VertexAIFactory

logger = logging.getLogger("farm_agent.warmup")


async def warmup_all() -> None:
    if not config.performance.warmup_enabled:
        logger.info("Warmup disabled via configuration flag")
        return

    logger.info("Starting lightweight warmup")
    try:
        await asyncio.gather(
            warmup_rag_model(),
            warmup_planning_models(),
            _warmup_oauth_token(),
        )
        logger.info("Warmup completed")
    except Exception as exc:
        logger.warning(f"Warmup encountered an error: {exc}")


async def _warmup_oauth_token() -> None:
    try:
        await asyncio.to_thread(_perform_token_warmup_call)
        logger.info("OAuth token warmup completed")
    except Exception as exc:
        logger.debug(f"OAuth token warmup failed: {exc}")


def _perform_token_warmup_call() -> None:
    model = VertexAIFactory.create_model(
        system_instruction="You are a lightweight warmup model."
    )
    model.generate_content("Warmup ping. Reply with OK.")

