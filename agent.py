import asyncio  
import os  
import aiohttp  
from typing import Optional  
  
from pipecat.pipeline.pipeline import Pipeline  
from pipecat.pipeline.runner import PipelineRunner  
from pipecat.pipeline.task import PipelineTask, PipelineParams  
from pipecat.processors.aggregators.openai_llm_context import (  
    OpenAILLMContext,  
    OpenAILLMContextFrame,  
)  
from pipecat.processors.transcript_processor import TranscriptProcessor  
from pipecat.frames.frames import LLMMessagesAppendFrame, LLMRunFrame  
from pipecat.audio.vad.silero import SileroVADAnalyzer  
from pipecat.audio.vad.vad_analyzer import VADParams  
from pipecat.adapters.schemas.tools_schema import ToolsSchema, FunctionSchema, AdapterType  
from pipecat.observers.rtvi_observer import RTVIObserver  
  
# Services  
from pipecat.services.deepgram import DeepgramSTTService  
from pipecat.services.google import GoogleLLMService  
from pipecat.services.elevenlabs import ElevenLabsTTSService  
from pipecat.services.heygen.video import HeyGenVideoService  
from pipecat.services.heygen.api import NewSessionRequest, AvatarQuality  
from pipecat.transports.services.daily import DailyTransport, DailyParams  
  
# RTVI  
from pipecat.processors.frameworks.rtvi import RTVIProcessor, RTVIConfig  
  
from loguru import logger  
  
  
# Farm management function handlers  
async def get_weather_handler(params):  
    """Get weather forecast for farm location."""  
    location = params.arguments.get("location", "")  
    days = params.arguments.get("days", 7)  
      
    # Your weather API integration here  
    result = f"Weather forecast for {location} for next {days} days: Sunny, 75°F"  
    await params.result_callback(result)  
  
  
async def get_market_prices_handler(params):  
    """Get current market prices for crops."""  
    crop_type = params.arguments.get("crop_type", "")  
      
    # Your market price API integration here  
    result = f"Current market price for {crop_type}: $3.50/bushel"  
    await params.result_callback(result)  
  
  
async def get_sensor_data_handler(params):  
    """Get IoT sensor data from farm."""  
    sensor_id = params.arguments.get("sensor_id", "")  
      
    # Your IoT sensor integration here  
    result = f"Sensor {sensor_id} readings: Soil moisture 45%, Temperature 72°F"  
    await params.result_callback(result)  
  
  
async def main():  
    """Main application entry point."""  
      
    # Daily transport with VAD configuration  
    transport = DailyTransport(  
        room_url=os.getenv("DAILY_ROOM_URL"),  
        token=os.getenv("DAILY_TOKEN"),  
        bot_name="Farm Assistant",  
        params=DailyParams(  
            audio_in_enabled=True,  
            audio_out_enabled=True,  
            video_out_enabled=True,  
            video_out_is_live=True,  
            video_out_width=1280,  
            video_out_height=720,  
            vad_analyzer=SileroVADAnalyzer(  
                params=VADParams(  
                    confidence=0.5,  
                    min_volume=0.5,  
                    start_secs=0.2,  
                    stop_secs=0.3  
                )  
            ),  
        ),  
    )  
  
    async with aiohttp.ClientSession() as session:  
        # Initialize STT service  
        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY") or "")  
  
        # Initialize TTS service  
        tts = ElevenLabsTTSService(  
            api_key=os.getenv("ELEVENLABS_API_KEY") or "",  
            voice_id=os.getenv("ELEVENLABS_VOICE") or "21m00Tcm4TlvDq8ikWAM",  
        )  
  
        # Define farm management functions  
        weather_function = FunctionSchema(  
            name="get_weather",  
            description="Get weather forecast for farm location. Helps farmers plan irrigation and field work.",  
            properties={  
                "location": {  
                    "type": "string",  
                    "description": "Farm location (e.g., 'Iowa', 'Central Valley, CA')"  
                },  
                "days": {  
                    "type": "integer",  
                    "description": "Number of days to forecast",  
                    "default": 7  
                }  
            },  
            required=["location"]  
        )  
  
        market_prices_function = FunctionSchema(  
            name="get_market_prices",  
            description="Get current market prices for crops to help with selling decisions.",  
            properties={  
                "crop_type": {  
                    "type": "string",  
                    "description": "Type of crop (e.g., 'corn', 'wheat', 'soybeans')"  
                }  
            },  
            required=["crop_type"]  
        )  
  
        sensor_data_function = FunctionSchema(  
            name="get_sensor_data",  
            description="Get real-time IoT sensor data from farm equipment and fields.",  
            properties={  
                "sensor_id": {  
                    "type": "string",  
                    "description": "Sensor identifier (e.g., 'field-1-moisture', 'barn-temp')"  
                }  
            },  
            required=["sensor_id"]  
        )  
  
        # Google search tool for additional farm knowledge  
        search_tool = {"google_search": {}}  
  
        # Create tools schema  
        tools = ToolsSchema(  
            custom_tools={AdapterType.GEMINI: [search_tool]},  
            standard_tools=[weather_function, market_prices_function, sensor_data_function],  
        )  
  
        # System instruction for farm management  
        system_instruction = """  
        You are an expert farm management assistant with deep knowledge of agriculture.  
          
        GUIDELINES:  
        - Help farmers with crop management, weather planning, livestock care, and financial decisions  
        - Provide practical, actionable advice based on current conditions  
        - Use simple, clear language that's easy to understand  
        - Say "degrees" not "°", "dollars" not "$", "percent" not "%"  
        - Keep responses concise for simple questions (1-2 sentences)  
        - For complex topics, break information into digestible chunks  
        - Always be supportive and encouraging  
          
        Tools available:  
        - Weather: Use get_weather for forecasts and planning  
        - Market prices: Use get_market_prices for crop pricing  
        - Sensors: Use get_sensor_data for real-time field conditions  
          
        Your goal is to help farmers make informed decisions and improve their operations.  
        """  
  
        # Initialize Google LLM service  
        llm = GoogleLLMService(  
            api_key=os.getenv("GOOGLE_API_KEY") or "",  
            model=os.getenv("GOOGLE_MODEL") or "gemini-2.0-flash",  
            system_instruction=system_instruction,  
        )  
  
        # Register function handlers  
        llm.register_function("get_weather", get_weather_handler)  
        llm.register_function("get_market_prices", get_market_prices_handler)  
        llm.register_function("get_sensor_data", get_sensor_data_handler)  
  
        # Configure HeyGen avatar  
        heyGen = HeyGenVideoService(  
            api_key=os.getenv("HEYGEN_API_KEY") or "",  
            session=session,  
            session_request=NewSessionRequest(  
                avatar_id="Katya_Chair_Sitting_public",  
                quality=AvatarQuality.high,  
            ),  
        )  
  
        # LLM Context and Aggregator  
        context = OpenAILLMContext(  
            [{"role": "user", "content": "Say hello and introduce yourself as a farm management assistant."}],  
        )  
        context_aggregator = llm.create_context_aggregator(context)  
  
        # RTVI processor  
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))  
  
        # Transcript processor  
        transcript = TranscriptProcessor()  
  
        # Build pipeline  
        pipeline = Pipeline(  
            [  
                transport.input(),           # Transport user input  
                stt,                         # Speech-to-text  
                transcript.user(),           # User transcript  
                rtvi,                        # RTVI protocol  
                context_aggregator.user(),   # User context aggregation  
                llm,                         # Google LLM  
                tts,                         # Text-to-speech  
                heyGen,                      # HeyGen avatar  
                transport.output(),          # Transport bot output  
                transcript.assistant(),      # Assistant transcript  
                context_aggregator.assistant(),  # Assistant context aggregation  
            ]  
        )  
  
        # Create task with metrics and interruptions enabled  
        task = PipelineTask(  
            pipeline,  
            params=PipelineParams(  
                enable_metrics=True,  
                enable_usage_metrics=True,  
                allow_interruptions=True,  
            ),  
            observers=[RTVIObserver(rtvi)],  
        )  
  
        # Event handlers  
        @rtvi.event_handler("on_client_ready")  
        async def on_client_ready(rtvi):  
            logger.info("🚀 RTVI client ready - farm assistant is online!")  
            await rtvi.set_bot_ready()  
  
        @transcript.event_handler("on_transcript_update")  
        async def handle_transcript_update(processor, frame):  
            """Log transcript updates."""  
            for message in frame.messages:  
                logger.info(f"TRANSCRIPT: {message.role}: {message.content}")  
  
        @transport.event_handler("on_client_connected")  
        async def on_client_connected(transport, client):  
            logger.info("🔗 Farmer connected to farm assistant")  
            # Start the conversation  
            await task.queue_frames([LLMRunFrame()])  
  
        @transport.event_handler("on_client_disconnected")  
        async def on_client_disconnected(transport, client):  
            logger.info("🔌 Farmer disconnected from farm assistant")  
            await task.cancel()  
  
        # Run the pipeline  
        logger.info("🚀 Starting Farm Management AI Assistant...")  
        runner = PipelineRunner()  
        await runner.run(task)  
  
  
if __name__ == "__main__":  
    # Required environment variables:  
    # DAILY_ROOM_URL, DAILY_TOKEN, DEEPGRAM_API_KEY,   
    # GOOGLE_API_KEY, ELEVENLABS_API_KEY, HEYGEN_API_KEY  
    asyncio.run(main())