import asyncio  
import os  
import aiohttp  
from typing import Optional  
import openai  
from openai import OpenAI
from typing import List
from pydantic import BaseModel, Field
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
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor, RTVIServerMessageFrame, RTVIAction, RTVIActionArgument
from pipecat.runner.utils import create_transport

# Services  
from pipecat.services.deepgram.stt import DeepgramSTTService  
from pipecat.services.google.llm import GoogleLLMService  
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService  
from pipecat.services.heygen.video import HeyGenVideoService  
from pipecat.services.heygen.api import NewSessionRequest, AvatarQuality  
from pipecat.transports.services.daily import DailyTransport, DailyParams  
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
# RTVI  
from pipecat.processors.frameworks.rtvi import RTVIProcessor, RTVIConfig  
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from dotenv import load_dotenv  
from pipecat.runner.types import RunnerArguments
load_dotenv()
from loguru import logger  


rtvi_processor: None
context = []


class FollowUpQuestions(BaseModel):
    questions: List[str]

class OpenAIFollowUpProcessor:
    """Follow-up question generator using OpenAI API with Pydantic."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"

    async def generate_follow_ups(self, assistant_response: str):
        """Generate follow-up questions using OpenAI with structured output."""
        global context

        context.append(assistant_response)
        if len(context) > 5:
            context.pop(0)

        try:
            prompt = f"""Based on this AI assistant response, generate 2-3 short, relevant follow-up questions that users might naturally ask next.

            Assistant Response: "{assistant_response}"
            Context: {context}

            Generate natural, conversational questions that would logically follow from this response. Keep them empathetic and engaging."""

            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=FollowUpQuestions,
                temperature=0.7
            )

            questions_obj = response.choices[0].message.parsed
            if questions_obj and questions_obj.questions and len(questions_obj.questions) >= 2:
                return questions_obj.questions[:3]
            
            # Fallback
            return ["Tell me more about that", "What else should I know?"]

        except Exception as e:
            logger.error(f"Error generating follow-ups: {e}")
            return ["Can you explain further?", "What's next?"]
        

async def send_follow_up_questions(questions: list):
    """Send follow-up questions to the UI."""
    global rtvi_processor
    
    if rtvi_processor and questions:
        try:
            frame = RTVIServerMessageFrame(
                data={
                    "type": "ui_update_follow_up",
                    "payload": {
                        "questions": questions,
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            )
            await rtvi_processor.push_frame(frame)
            logger.debug(f"Sent follow-up questions: {questions}")
        except Exception as e:
            logger.error(f"Error sending follow-up questions: {e}")


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
  
  
# async def main():  
#     """Main application entry point."""  
      
#     # Daily transport with VAD configuration  
#     transport = DailyTransport(  
#         room_url=os.getenv("DAILY_ROOM_URL"),  
#         token=os.getenv("DAILY_TOKEN"),  
#         bot_name="Farm Assistant",  
#         params=DailyParams(  
#             audio_in_enabled=True,  
#             audio_out_enabled=True,  
#             video_out_enabled=True,  
#             video_out_is_live=True,  
#             video_out_width=1280,  
#             video_out_height=720,  
#             vad_analyzer=SileroVADAnalyzer(  
#                 params=VADParams(  
#                     confidence=0.5,  
#                     min_volume=0.5,  
#                     start_secs=0.2,  
#                     stop_secs=0.3  
#                 )  
#             ),  
#         ),  
#     )  
  
#     async with aiohttp.ClientSession() as session:  
transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_out_enabled=True,
        video_out_is_live=True,
        video_out_width=1280,
        video_out_height=720,
        video_out_bitrate=2_000_000,  # 2MBps
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
    ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_out_enabled=True,
        video_out_is_live=True,
        video_out_width=1280,
        video_out_height=720,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
    ),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")
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
        
         # Follow-up processor
        follow_up_processor = OpenAIFollowUpProcessor()

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

        async def generate_and_send_follow_ups(assistant_response: str):
            """Generate and send follow-up questions."""
            try:
                questions = await follow_up_processor.generate_follow_ups(assistant_response)
                await send_follow_up_questions(questions)
            except Exception as e:
                logger.error(f"Error in follow-up generation: {e}")
  
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

                # If assistant message, generate follow-up questions
                if message.role == "assistant" and message.content:
                    await generate_and_send_follow_ups(message.content)
  
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

async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)

if __name__ == "__main__":
    from pipecat.runner.run import main
    asyncio.run(main())