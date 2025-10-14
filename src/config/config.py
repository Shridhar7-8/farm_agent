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

class AppConfig(BaseModel):
    vertexai: VertexAIConfig = VertexAIConfig()
    cache_duration_weather: int = 600  # seconds
    cache_duration_market: int = 86400
    cache_duration_sheets: int = 300
    max_detailed_conversations: int = 8
    quality_threshold: float = 0.75
    max_refinement_iterations: int = 2
    base_url_sheets: str = Field(default_factory=lambda: os.getenv("SHEETS_BASE_URL", "https://us-central1-digitalhuman-445007.cloudfunctions.net/sheet-assistant"))

config = AppConfig()