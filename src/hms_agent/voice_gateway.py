import asyncio
import json
import logging
import io
import wave
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from contextlib import asynccontextmanager
from faster_whisper import WhisperModel
import piper
from huggingface_hub import hf_hub_download

from agent import get_agent, handle_user_message
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.workflow import Context

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI instance is initialized later with lifespan

# MCP Setup
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"

# AI Models Setup
BASE_DIR = Path(__file__).parent
# Load Faster-Whisper (using 'base' for speed on local CPU)
stt_model = WhisperModel("base", device="cpu", compute_type="int8")

# Piper setup
MODELS_DIR = BASE_DIR / "models"
PIPER_MODEL_NAME = "en_US-lessac-medium"
PIPER_MODEL_PATH = MODELS_DIR / f"{PIPER_MODEL_NAME}.onnx"
PIPER_CONFIG_PATH = MODELS_DIR / f"{PIPER_MODEL_NAME}.onnx.json"

def ensure_models():
    """Download models if they don't exist."""
    MODELS_DIR.mkdir(exist_ok=True)
    if not PIPER_MODEL_PATH.exists():
        logger.info(f"Downloading Piper model {PIPER_MODEL_NAME}...")
        hf_hub_download(
            repo_id="rhasspy/piper-voices",
            filename=f"en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            local_dir=MODELS_DIR,
            local_dir_use_symlinks=False
        )
        # Move it to the expected path if name differs
        downloaded = MODELS_DIR / "en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        if downloaded.exists():
            downloaded.rename(PIPER_MODEL_PATH)
            
    if not PIPER_CONFIG_PATH.exists():
        hf_hub_download(
            repo_id="rhasspy/piper-voices",
            filename=f"en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
            local_dir=MODELS_DIR,
            local_dir_use_symlinks=False
        )
        downloaded = MODELS_DIR / "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        if downloaded.exists():
            downloaded.rename(PIPER_CONFIG_PATH)

# Initialize Piper voice on startup
voice = None

def synthesize_speech(text: str) -> bytes:
    """Synthesize text to speech using Piper."""
    global voice
    if voice is None:
        try:
            voice = piper.PiperVoice.load(str(PIPER_MODEL_PATH), config_path=str(PIPER_CONFIG_PATH))
        except Exception as e:
            logger.error(f"Failed to load Piper voice: {e}")
            return b""
    
    output_buffer = io.BytesIO()
    with wave.open(output_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(voice.config.sample_rate)
        voice.synthesize(text, wav_file)
    
    return output_buffer.getvalue()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Voice Gateway...")
    ensure_models()
    yield
    logger.info("Shutting down Voice Gateway...")

app = FastAPI(title="HMS Voice Gateway", lifespan=lifespan)

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Initialize Agent for this session
    mcp_client = BasicMCPClient(MCP_SERVER_URL)
    mcp_tool = McpToolSpec(client=mcp_client)
    agent = await get_agent(mcp_tool)
    agent_context = Context(agent)
    
    # Audio accumulation buffer
    audio_buffer = []
    
    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message:
                user_text = message["text"]
                logger.info(f"Received text message: {user_text}")
                
                try:
                    data = json.loads(user_text)
                    if data.get("type") == "end_audio":
                        # Process accumulated audio
                        if audio_buffer:
                            audio_np = np.concatenate(audio_buffer)
                            audio_buffer = []  # Reset buffer
                            
                            # Transcribe
                            segments, info = stt_model.transcribe(audio_np, beam_size=5)
                            transcription = " ".join([segment.text for segment in segments]).strip()
                            
                            if transcription:
                                logger.info(f"Transcribed: {transcription}")
                                await websocket.send_json({"type": "transcription", "content": transcription})
                                
                                # Process with agent
                                response = await handle_user_message(transcription, agent, agent_context, verbose=True)
                                await websocket.send_json({"type": "text", "content": response})
                                
                                # Synthesize and send audio response
                                audio_bytes = synthesize_speech(response)
                                if audio_bytes:
                                    await websocket.send_bytes(audio_bytes)
                        continue
                except:
                    pass
                
                # Handle direct text input
                response = await handle_user_message(user_text, agent, agent_context, verbose=True)
                await websocket.send_json({"type": "text", "content": response})
                
            elif "bytes" in message:
                audio_data = message["bytes"]
                # Received Int16 PCM chunk from frontend
                chunk_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                audio_buffer.append(chunk_np)
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket: {e}")
        await websocket.close()
# Serve static files for the UI
UI_DIR = Path(__file__).parent / "web"
if not UI_DIR.exists():
    UI_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

@app.get("/")
async def get():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HMS AI Agent</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div id="app">
            <header>
                <h1>HMS AI Assistant</h1>
                <div id="status-dot"></div>
            </header>
            <main id="chat-container">
                <div id="chat-log"></div>
            </main>
            <footer>
                <div class="input-area">
                    <input type="text" id="chat-input" placeholder="Type a message...">
                    <button id="mic-btn" onclick="toggleMic()">🎤</button>
                    <button id="send-btn" onclick="sendMessage()">Send</button>
                </div>
            </footer>
        </div>
        <script src="/static/script.js?v=2.1"></script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
