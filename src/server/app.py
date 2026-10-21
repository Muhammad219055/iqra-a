"""
FastAPI Server for Quran Recitation Tutor.
Serves web interface and handles WebSocket streaming sessions.
"""

from pathlib import Path
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from src.asr.engine import QuranASREngine
from src.server.ws_handler import RecitationSession
from src.server.db import init_db, save_session, get_recent_sessions
from scripts.download_quran_text import download_surah_words

app = FastAPI(title="Quran Recitation Tutor (Local-First)")

# Single global ASR engine loaded on startup
asr_engine: QuranASREngine = None


@app.on_event("startup")
async def startup_event():
    global asr_engine
    print("Initializing local Quran ASR Engine on startup...")
    init_db()
    asr_engine = QuranASREngine()
    # Pre-cache Surah 1 text
    download_surah_words(1)


@app.get("/api/surah/{surah_id}")
async def get_surah(surah_id: int):
    data = download_surah_words(surah_id)
    return JSONResponse(data)


@app.get("/api/reciters")
async def get_reciters():
    return JSONResponse({
        "reciters": [
            {"id": "mishari", "name": "Mishari Rashid al-`Afasy", "default": True},
            {"id": "husary", "name": "Mahmoud Khalil Al-Husary", "default": False},
        ]
    })


@app.post("/api/sessions/save")
async def save_session_endpoint(request: Request):
    payload = await request.json()
    session_id = save_session(
        surah=payload.get("surah", 1),
        start_time=payload.get("start_time", 0),
        end_time=payload.get("end_time", 0),
        total_words_matched=payload.get("total_words_matched", 0),
        total_mistakes=payload.get("total_mistakes", 0),
        total_prompts=payload.get("total_prompts", 0),
        total_peeks=payload.get("total_peeks", 0),
        accuracy=payload.get("accuracy", 0.0),
        mistakes_list=payload.get("mistakes", []),
    )
    return JSONResponse({"status": "ok", "session_id": session_id})


@app.get("/api/sessions/history")
async def get_history_endpoint():
    history = get_recent_sessions(limit=10)
    return JSONResponse({"history": history})


@app.websocket("/ws/recite")
async def websocket_recite_endpoint(websocket: WebSocket):
    session = RecitationSession(websocket, asr_engine)
    await session.run()


# Mount static web UI directory
web_dir = Path("web")
web_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/")
async def index():
    return FileResponse(web_dir / "index.html")
