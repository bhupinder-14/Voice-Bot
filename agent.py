import logging
import asyncio
from aiofile import async_open as open
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
import random

from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import cartesia, openai, deepgram, silero, turn_detector
from livekit.plugins import google

#from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import openai
from livekit.plugins import elevenlabs
import time
from typing import AsyncIterable, Union
import os
# from llama_index.core import (
#     SimpleDirectoryReader,
#     StorageContext,
#     VectorStoreIndex,
#     load_index_from_storage,
#     Document
# )
# from llama_index.core.schema import MetadataMode
# import json
from livekit import api 
# from llama_index.core.text_splitter import TokenTextSplitter
from silence import SilenceDisconnector
from datetime import datetime , timezone
from info import get_prompt


#Loading Dotenv

load_dotenv(dotenv_path=".env.local",verbose=True)


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger("voice-agent")
logger.setLevel(logging.DEBUG)




groq_stt = openai.stt.STT.with_groq(
   model="whisper-large-v3-turbo",
   detect_language=True,
   language="hi",
 )

groq_llm = openai.llm.LLM.with_groq(
   model="llama3-8b-8192",
   temperature=0.8,
 )

# openai_tts = openai.tts.TTS()
google_llm = google.LLM(
   model="gemini-2.0-flash-exp",
   temperature="0.8",
  vertexai=True,
 )

google_stt = google.STT(
  model="chirp",
  spoken_punctuation=True,
)

google_tts=google.TTS(
            gender="male",
            language="hi-IN",
            voice_name="hi-IN-Neural2-B",
        )

  
        
eleven_tts=elevenlabs.tts.TTS(
    model="eleven_flash_v2_5",
    voice=elevenlabs.tts.Voice(
        id="N2lVS1w4EtoT3dr4eOWO",
        name="Callum",
        category="premade",
        settings=elevenlabs.tts.VoiceSettings(
            stability=0.8,
            similarity_boost= 0.6 , #0.8,
            style=0.3,
            use_speaker_boost=True
        ),
    ),
    streaming_latency=1,
    enable_ssml_parsing=True,
    chunk_length_schedule=[80, 120, 200, 260],
    language="hi"
)
#
#
cartesia_tts = cartesia.tts.TTS(
  model="sonic",
  voice="9b953e7b-86a8-42f0-b625-1434fb15392b",
  language = "hi"
)

deepgram_stt = deepgram.stt.STT(
    model="nova-2",
    interim_results=True,
    smart_format=True,
    punctuate=True,
    filler_words=False,
    profanity_filter=False,
    keywords=[("English, Hindi, Holiday Trip", 1.5)],
    language="hi"
)

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    
# async def entrypoint(ctx: JobContext):
#     system_msg = llm.ChatMessage(
#         role="system",
#         content=(

#             get_prompt(id)
              
#         ),
#     )
    
#     # # Set up recording
#     # file_contents = ""
#     # async with open("decent-habitat-448415-n4-abd8a13a156b.json", "r") as f:
#     #     file_contents = await f.read()

#     # req = api.RoomCompositeEgressRequest(
#     #     room_name=ctx.room.name,
#     #     layout="speaker",
#     #     audio_only=True,
#     #     file_outputs=[api.EncodedFileOutput(
#     #         filepath=f"{ctx.room.name}.mp4",
#     #         disable_manifest=False,
#     #         gcp=api.GCPUpload(
#     #             credentials=file_contents,
#     #             bucket="burger-singh-calls",
#     #         )
#     #     )]
#     # )
    
    
#     # await lkapi.egress.start_room_composite_egress(req)

    
#     initial_ctx = llm.ChatContext()
#     initial_ctx.messages.append(system_msg)
    
#     transcripts = {}
           
#     logger.info(f"connecting to room {ctx.room.name}")
    
#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

#     # Wait for the first participant to connect
#     participant = await ctx.wait_for_participant()
#     logger.info(f"starting voice assistant for participant {participant.kind}")
#     logger.info(f"starting voice assistant for participant {participant.attributes}")
#     logger.info(f"starting voice assistant for participant {ctx}")
#     logger.info(f"starting voice assistant for participant {ctx.room.metadata}")
#     transcripts["room_name"]=ctx.room.name
#     transcripts["transcript"]=[]
#     transcripts["duration"] = time.time()
#     transcripts["date"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
#     id = participant.attributes.get("sip.trunkPhoneNumber")


prompt_cache = {}

async def get_cached_prompt(id):
    if id in prompt_cache:
        logger.info(f"Fetching cached prompt for ID: {id}")
        return prompt_cache[id]
    
    logger.info(f"Fetching new prompt for ID: {id}")
    prompt = get_prompt(id)  # Fetch prompt from your function
    prompt_cache[id] = prompt  # Store in cache
    return prompt



async def entrypoint(ctx: JobContext):
    
    # Wait for the first participant to connect
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
 
    participant = await ctx.wait_for_participant()

   
    

    # Extract participant ID
    id = participant.attributes.get("sip.trunkPhoneNumber", "Unknown")

    await asyncio.sleep(1)

    logger.info(f"Participant ID: {id}")

    lkapi = api.LiveKitAPI()
    # Fetch prompt based on the participant ID
    prompt = await get_cached_prompt(id)

    # Create initial system message
    system_msg = llm.ChatMessage(
        role="system",
        content=prompt,  
    )

    # Initialize chat context
    initial_ctx = llm.ChatContext()
    initial_ctx.messages.append(system_msg)

    # Connect to room



    


    transcripts = {
        "room_name": ctx.room.name,
        "transcript": [],
        "duration": time.time(),
        "date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    }


    logger.info(f"connecting to room {ctx.room.name}")
    print(f"DEBUG: connecting to room {ctx.room.name}")
    logger.info(f"starting voice assistant for participant {participant.kind}")
    logger.info(f"starting voice assistant for participant {participant.attributes}")
    logger.info(f"starting voice assistant for participant {ctx}")
    logger.info(f"starting voice assistant for participant {ctx.room.metadata}")



    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram_stt,
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=eleven_tts,
        turn_detector=turn_detector.EOUModel(),
        min_endpointing_delay=0.1,
        max_endpointing_delay=3.0,
        chat_ctx=initial_ctx,
        interrupt_min_words=2
    )

    usage_collector = metrics.UsageCollector()

    # 2. Track the current filler task
    state = {"filler_task": None}
    
    FILLERS = [
        "hm...",
        "अच्छा...",
        "Okay...",
        "Got it...",
        "हां...",
        "Alright!",
        "वैसे…",
        "ठीक…"
    ]
    
    async def play_filler():
        await agent.say(random.choice(FILLERS), allow_interruptions=True, add_to_chat_ctx=False)

    @agent.on("agent_speech_interrupted")
    def on_agent_speech_interrupted():
        agent.interrupt(interrupt_all=True)

    @agent.on("metrics_collected")
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)
        
        
    #transcription generation
    log_queue = asyncio.Queue()

    async def hangup():
        try:
            await lkapi.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=ctx.room.name,
                    identity=participant.identity,
                )
            )
            ctx.shutdown(reason="Session ended, call cut.")
        except Exception as e:
            logger.info(f"received error while ending call: {e}")


    silence_detector = SilenceDisconnector(agent, hangup, timeout_sec=7.0)
    
    @agent.on("user_started_speaking")
    def on_user_started_speaking():
        silence_detector.on_user_started_speaking()
        
    @agent.on("user_stopped_speaking")
    def on_user_stopped_speaking():
        silence_detector.on_user_stopped_speaking()
        state["filler_task"] = asyncio.create_task(play_filler())
        
    @agent.on("agent_started_speaking")
    def on_agent_started_speaking():
        silence_detector.on_agent_started_speaking()
        if state["filler_task"] and not state["filler_task"].done():
            state["filler_task"].cancel()
        
    @agent.on("agent_stopped_speaking")
    def on_agent_stopped_speaking():
        silence_detector.on_agent_stopped_speaking()
    
    silence_detector.start()
           
    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        logger.debug(f"User speech event triggered with message: {msg.content}")
        if isinstance(msg.content, list):
            msg.content = "\n".join(
                "[image]" if isinstance(x, llm.ChatImage) else x for x in msg
            )
        log_queue.put_nowait({"speaker": "user", "message": msg.content, "timestamp": timestamp})
        
    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        logger.debug(f"Agent speech event triggered with message: {msg.content}")
        log_queue.put_nowait({"speaker": "agent", "message": msg.content, "timestamp": timestamp})
        if any(keyword in msg.content.lower() for keyword in ["travel advisor", "goodbye"]):
            asyncio.create_task(hangup())
        #if "travel advisor" in msg.content.lower():
            #asyncio.create_task(hangup())
    
    
    async def write_transcription():
        while True:
            msg = await log_queue.get()
            if msg is None:
                call_start_time = transcripts["duration"]
                transcripts["duration"] = round(time.time() - call_start_time, 2)
                logger.info(f"final: {transcripts} and duration {transcripts['duration']}")
                break
            transcripts["transcript"].append(msg)
               

    write_task = asyncio.create_task(write_transcription())

    async def finish_queue():
        log_queue.put_nowait(None)
        await write_task
        silence_detector.stop()
        await lkapi.aclose()

    ctx.add_shutdown_callback(finish_queue)

    agent.start(ctx.room, participant)

    # The agent should be polite and greet the user when it joins :)
    await agent.say("नमस्ते! मैं Testing Bot hu Mera naam Alpha Hai । मैं आपकी कैसे मदद कर सकता हूँ?", allow_interruptions=True)
    

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="inbound-agent",
        ),
    )
