import asyncio
from typing import Dict, Any
from google.adk.tools import FunctionTool
from src.core.processors import weather_processor, market_price_processor, sheet_processor
from src.core.planning import sequential_planner, reflection_agent, farming_planner  # Import from planning.py
from src.tools.utils import JsonUtils, VertexAIFactory, logger
from src.config.config import config
from google.adk.tools.retrieval import VertexAiRagRetrieval  
from vertexai.preview import rag  
from vertexai.generative_models import GenerativeModel, Tool
import vertexai
import logging
from src.observability.observability import observe_if_available


rag_logger = logging.getLogger('farm_agent.tools.rag')



@observe_if_available(name="weather_tool")
async def get_weather_tool(location: str, tool_context) -> Dict[str, Any]:
    """Get weather information for a location."""
    weather_data = await weather_processor.get_weather_data(location)
    
    if not weather_data:
        return {"status": "error", "message": f"Could not retrieve weather for {location}"}
    
    # Use JsonUtils for safe serialization if needed, but direct dict is fine
    return {
        "status": "success",
        "location": weather_data.location,
        "temperature": weather_data.current_temperature,
        "condition": weather_data.condition,
        "high": weather_data.high_temperature,
        "low": weather_data.low_temperature,
        "humidity": weather_data.humidity,
        "wind_speed": weather_data.wind_speed
    }

@observe_if_available(name="market_price_tool")
async def get_market_price_tool(crop_type: str, tool_context) -> Dict[str, Any]:
    """Get market prices for a crop."""
    price_data = await market_price_processor.get_market_price(crop_type)
    
    if not price_data:
        return {"status": "error", "message": f"Could not find prices for {crop_type}"}
    
    return {
        "status": "success",
        "commodity": price_data.commodity,
        "market": price_data.market,
        "state": price_data.state,
        "price_modal": price_data.price_modal,
        "price_min": price_data.price_min,
        "price_max": price_data.price_max,
        "unit": price_data.unit,
        "arrival": price_data.arrival
    }

@observe_if_available(name="customer_data_tool")
async def get_customer_data_tool(customer_id: str, tool_context) -> Dict[str, Any]:
    """Get customer data from Google Sheets."""
    customer_data = await sheet_processor.get_customer_data(customer_id)
    
    if not customer_data:
        return {"status": "error", "message": f"Could not find customer data for ID: {customer_id}"}
    
    return {
        "status": "success",
        "customer_data": customer_data
    }

# @observe_if_available(name="agricultural_rag_tool")
# async def get_agricultural_knowledge_tool(agricultural_query: str, tool_context) -> Dict[str, Any]:
#     """Get agricultural knowledge using RAG from the agricultural corpus."""
#     try:
#         # Initialize Vertex AI
#         VertexAIFactory.init_vertexai(config)
        
#         # Note: Vertex AI may create internal HTTP sessions that we can't directly control
#         # The cleanup will be handled by our application-level cleanup functions
        
#         # Configure RAG retrieval
#         rag_retrieval_config = rag.RagRetrievalConfig(
#             top_k=5,
#             filter=rag.Filter(vector_distance_threshold=0.4),
#         )
        
#         # Create RAG retrieval tool
#         rag_retrieval_tool = Tool.from_retrieval(
#             retrieval=rag.Retrieval(
#                 source=rag.VertexRagStore(
#                     rag_resources=[
#                         rag.RagResource(
#                             rag_corpus=config.vertexai.rag_corpus_name,
#                         )
#                     ],
#                     rag_retrieval_config=rag_retrieval_config,
#                 ),
#             )
#         )
        
#         # Create RAG-enhanced model
#         rag_model = VertexAIFactory.create_model(
#             model_name="gemini-2.0-flash-001",
#             tools=[rag_retrieval_tool],
#             system_instruction="""You are an expert agricultural advisor with access to comprehensive agricultural knowledge.

# **Your Role:**
# - Provide detailed, practical farming advice based on retrieved agricultural knowledge
# - Help farmers with crop cultivation, pest management, fertilization, and irrigation
# - Give specific recommendations including varieties, doses, timing, and methods

# **Response Guidelines:**
# - Be specific and practical for farmers
# - Include exact quantities (kg/ha, quintals, days after sowing) when available
# - Mention specific crop varieties and chemical names when available
# - Provide step-by-step guidance when needed
# - Use clear, farmer-friendly language
# - Focus on Indian agricultural conditions and practices"""
#         )
        
#         # Generate RAG-enhanced response
#         rag_logger.debug("-----------------------------------------------------------")
#         rag_logger.debug("LLM Request to RAG model:")
#         rag_logger.debug(f"Model: gemini-2.0-flash-001")
#         rag_logger.debug(f"System Instruction: You are an expert agricultural advisor...")
#         rag_logger.debug(f"Query: {agricultural_query}")
#         rag_logger.debug("Tools: RAG retrieval tool enabled")
#         rag_logger.debug("-----------------------------------------------------------")
        
#         response = rag_model.generate_content(agricultural_query)
        
#         rag_logger.debug("-----------------------------------------------------------")
#         rag_logger.debug("LLM Response from RAG model:")
#         if response and response.text:
#             rag_logger.debug(f"Response text: {response.text[:500]}...")
#         else:
#             rag_logger.warning("No response received from RAG model")
#         rag_logger.debug("-----------------------------------------------------------")
        
#         if response and response.text:
#             logger.info(f"RAG tool successfully processed query about: {agricultural_query[:50]}...")
#             return {
#                 "status": "success",
#                 "query": agricultural_query,
#                 "agricultural_advice": response.text,
#                 "source": "RAG Agricultural Knowledge Base"
#             }
#         else:
#             return {
#                 "status": "error", 
#                 "message": "Could not generate response from agricultural knowledge base"
#             }
            
#     except Exception as e:
#         logger.error(f"Error in RAG agricultural knowledge tool: {e}")
#         return {
#             "status": "error",
#             "message": f"Error accessing agricultural knowledge: {str(e)}"
#         }

agricultural_rag_tool = VertexAiRagRetrieval(  
    name="get_agricultural_knowledge",  
    description="Retrieve agricultural knowledge about crops, pests, fertilizers, irrigation, and farming techniques from the agricultural corpus",  
    rag_resources=[rag.RagResource(rag_corpus=config.vertexai.rag_corpus_name)],  
    similarity_top_k=5,  
    vector_distance_threshold=0.4  
)

@observe_if_available(name="validated_farming_plan_tool")
async def get_validated_farming_plan_tool(problem_description: str, tool_context) -> Dict[str, Any]:
    """Get a comprehensive, quality-validated farming plan using sequential planning+reflection."""
    
    # Extract context from tool_context if available
    context = {}
    if hasattr(tool_context, 'session_state') and tool_context.session_state:
        farmer_info = tool_context.session_state.get("farmer_info", {})
        context.update({
            "location": farmer_info.get("location", ""),
            "crop_type": farmer_info.get("crops", []),
            "farm_size": farmer_info.get("farm_size", ""),
            "experience": farmer_info.get("experience", "intermediate")
        })
    
    # Use sequential planning agent for comprehensive plan with quality validation
    result = await sequential_planner.create_validated_agricultural_plan(problem_description, context)
    
    if result["status"] == "success":
        return {
            "status": "success",
            "validated_farming_plan": result["final_plan"],
            "quality_score": result["quality_score"],
            "approval_status": result["approval_status"],
            "refinement_iterations": result["refinement_iterations"],
            "process_summary": result["process_summary"],
            "message": f"Quality-validated farming plan generated (Score: {result['quality_score']:.2f})"
        }
    else:
        return {
            "status": "error", 
            "message": result.get("message", "Failed to create validated farming plan")
        }

@observe_if_available(name="farming_plan_tool")
async def get_farming_plan_tool(problem_description: str, tool_context) -> Dict[str, Any]:
    """Get a comprehensive farming plan for complex agricultural challenges."""
    
    # Extract context from tool_context if available
    context = {}
    if hasattr(tool_context, 'session_state') and tool_context.session_state:
        farmer_info = tool_context.session_state.get("farmer_info", {})
        context.update({
            "location": farmer_info.get("location", ""),
            "crop_type": farmer_info.get("crops", []),
            "farm_size": farmer_info.get("farm_size", ""),
            "experience": farmer_info.get("experience", "intermediate")
        })
    
    plan_result = await farming_planner.create_farming_plan(problem_description, context)
    
    if plan_result["status"] == "success":
        return {
            "status": "success",
            "farming_plan": plan_result["plan"],
            "message": "Comprehensive farming plan generated successfully"
        }
    else:
        return {
            "status": "error", 
            "message": plan_result.get("message", "Failed to create farming plan")
        }

@observe_if_available(name="advice_quality_evaluation_tool")
async def evaluate_advice_quality_tool(advice_text: str, tool_context) -> Dict[str, Any]:
    """Evaluate the quality of agricultural advice using reflection agent."""
    
    # Extract context for evaluation
    context = {}
    if hasattr(tool_context, 'session_state') and tool_context.session_state:
        farmer_info = tool_context.session_state.get("farmer_info", {})
        context.update({
            "location": farmer_info.get("location", ""),
            "crop_type": farmer_info.get("crops", []),
            "experience": farmer_info.get("experience", "intermediate")
        })
    
    evaluation_result = await reflection_agent.evaluate_agricultural_advice(advice_text, context)
    
    if evaluation_result["status"] == "success":
        return {
            "status": "success",
            "quality_evaluation": evaluation_result["evaluation"],
            "meets_quality_threshold": evaluation_result["meets_threshold"],
            "message": "Quality evaluation completed successfully"
        }
    else:
        return {
            "status": "error",
            "message": evaluation_result.get("message", "Failed to evaluate advice quality")
        }

# Agent Tools
weather_tool = FunctionTool(get_weather_tool)
market_price_tool = FunctionTool(get_market_price_tool)
customer_data_tool = FunctionTool(get_customer_data_tool)
# agricultural_knowledge_tool = FunctionTool(get_agricultural_knowledge_tool)
validated_farming_plan_tool = FunctionTool(get_validated_farming_plan_tool)
farming_plan_tool = FunctionTool(get_farming_plan_tool)
evaluate_advice_quality_tool = FunctionTool(evaluate_advice_quality_tool)