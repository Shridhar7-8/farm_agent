from pydantic import BaseModel, Field
from typing import List, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

class VertexAIConfig(BaseModel):
    project_id: str = Field(default_factory=lambda: os.getenv("PROJECT_ID", "digitalhuman-445007"))
    location: str = Field(default_factory=lambda: os.getenv("LOCATION", "us-east4"))
    model_name: str = Field(default_factory=lambda: os.getenv("MODEL", "gemini-2.0-flash-001"))
    rag_corpus_name: str = Field(default_factory=lambda: os.getenv("RAG_CORPUS_NAME", "projects/digitalhuman-445007/locations/us-east4/ragCorpora/7991637538768945152"))

class PerformanceConfig(BaseModel):
    enable_observability: bool = Field(default_factory=lambda: os.getenv("ENABLE_LAMINAR_TRACING", "false").lower() == "true")
    max_memory_context_conversations: int = Field(default_factory=lambda: int(os.getenv("MAX_MEMORY_CONTEXT_CONVERSATIONS", "3")))
    max_memory_summary_chars: int = Field(default_factory=lambda: int(os.getenv("MAX_MEMORY_SUMMARY_CHARS", "600")))
    max_memory_recent_chars: int = Field(default_factory=lambda: int(os.getenv("MAX_MEMORY_RECENT_CHARS", "1200")))
    warmup_enabled: bool = Field(default_factory=lambda: os.getenv("WARMUP_ENABLED", "true").lower() == "true")


class AppConfig(BaseModel):
    vertexai: VertexAIConfig = VertexAIConfig()
    performance: PerformanceConfig = PerformanceConfig()
    cache_duration_weather: int = 600  # seconds
    cache_duration_market: int = 86400
    cache_duration_sheets: int = 300
    max_detailed_conversations: int = 8
    quality_threshold: float = 0.75
    max_refinement_iterations: int = 2
    base_url_sheets: str = Field(default_factory=lambda: os.getenv("SHEETS_BASE_URL", "https://us-central1-digitalhuman-445007.cloudfunctions.net/sheet-assistant"))

config = AppConfig()