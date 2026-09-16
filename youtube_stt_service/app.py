import os
import sys
import json
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Query, HTTPException  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.responses import StreamingResponse, FileResponse  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from pydantic import BaseModel  # type: ignore
import uvicorn  # type: ignore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from downloader import YouTubeDownloader
    from stt_service import GeminiTranscriber, LANGUAGE_MAP, detect_language_from_text
except ImportError:
    from youtube_stt_service.downloader import YouTubeDownloader  # type: ignore
    from youtube_stt_service.stt_service import GeminiTranscriber, LANGUAGE_MAP, detect_language_from_text  # type: ignore
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="YouTube Audio Downloader & Gemini STT Service",
    description="유튜브 영상의 오디오를 다운로드하고 Gemini 3.5 Transcribe로 다국어 전사하는 웹 서비스",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

downloader = YouTubeDownloader(download_dir=DOWNLOAD_DIR)
transcriber = None

def get_transcriber():
    global transcriber
    if transcriber is None:
        transcriber = GeminiTranscriber()
    return transcriber

class URLRequest(BaseModel):
    url: str

@app.get("/")
async def root():
    """웹 프론트엔드 메인 페이지를 반환합니다."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "YouTube STT Web Service is running."}

@app.get("/api/languages")
async def get_languages():
    """지원하는 언어 목록 및 기본 메타데이터를 반환합니다."""
    return {
        "success": True,
        "languages": [
            {"code": k, "name": v["name"], "flag": v["flag"]}
            for k, v in LANGUAGE_MAP.items()
        ]
    }

@app.post("/api/info")
async def get_video_info(req: URLRequest):
    """비디오 URL에 대한 메타데이터와 추천 언어 코드를 확인합니다."""
    try:
        info = downloader.get_video_info(req.url)
        suggested_lang = detect_language_from_text(info.get("title", ""))
        return {
            "success": True,
            "data": {
                **info,
                "suggested_lang": suggested_lang,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream")
async def stream_transcription(
    url: str = Query(..., description="YouTube 비디오 URL"),
    lang: str = Query("auto", description="언어 코드 (ko, en, zh, ja, ru, es, fr, de, hi, vi, th, id, sea, auto)"),
):
    """Server-Sent Events(SSE)를 통해 다운로드 진행률 및 Gemini 다국어 실시간 전사 결과를 스트리밍합니다."""
    async def event_generator() -> AsyncGenerator[str, None]:
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def sse_pack(event_name: str, payload: dict) -> str:
            return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        await queue.put(sse_pack("status", {"step": "info", "message": "유튜브 영상 정보 확인 중..."}))

        def run_pipeline():
            try:
                # 1) 메타데이터 가져오기
                info = downloader.get_video_info(url)
                suggested_lang = detect_language_from_text(info.get("title", ""))
                effective_lang = lang if lang != "auto" else suggested_lang

                asyncio.run_coroutine_threadsafe(
                    queue.put(sse_pack("info", {
                        **info,
                        "suggested_lang": suggested_lang,
                        "selected_lang": lang,
                        "effective_lang": effective_lang,
                    })), loop
                )

                # 2) 다운로드 진행률 콜백
                def on_download_progress(p):
                    asyncio.run_coroutine_threadsafe(
                        queue.put(sse_pack("progress", p)), loop
                    )

                asyncio.run_coroutine_threadsafe(
                    queue.put(sse_pack("status", {"step": "downloading", "message": "오디오 다운로드 시작..."})), loop
                )

                download_res = downloader.download_audio(url, progress_callback=on_download_progress)
                audio_url = f"/downloads/{download_res['file_name']}"

                asyncio.run_coroutine_threadsafe(
                    queue.put(sse_pack("downloaded", {
                        **download_res,
                        "audio_url": audio_url,
                    })), loop
                )

                # 3) Gemini STT 전사 시작
                asyncio.run_coroutine_threadsafe(
                    queue.put(sse_pack("status", {
                        "step": "transcribing",
                        "message": f"Gemini 3.5 Transcribe 음성 인식 시작 (선택 언어: {lang}, 적용 언어: {effective_lang})...",
                    })), loop
                )

                t_engine = get_transcriber()
                stt_stream = t_engine.transcribe_stream(
                    audio_path=download_res["file_path"],
                    mime_type=download_res["mime_type"],
                    language=effective_lang,
                    text_hint=info.get("title", ""),
                )

                accumulated_items = []

                for ev in stt_stream:
                    ev_type = ev.get("type")
                    if ev_type == "chunk":
                        accumulated_items.append(ev)
                        asyncio.run_coroutine_threadsafe(
                            queue.put(sse_pack("chunk", ev)), loop
                        )
                    elif ev_type == "speaker_change":
                        asyncio.run_coroutine_threadsafe(
                            queue.put(sse_pack("speaker_change", ev)), loop
                        )
                    elif ev_type == "status":
                        asyncio.run_coroutine_threadsafe(
                            queue.put(sse_pack("status", {"step": "transcribing", "message": ev.get("message")})), loop
                        )
                    elif ev_type == "complete":
                        plain_txt = t_engine.format_to_plain_text(accumulated_items)
                        md_txt = t_engine.format_to_markdown(accumulated_items, title=info.get("title", "YouTube 전사본"))
                        srt_txt = t_engine.format_to_srt(accumulated_items)

                        asyncio.run_coroutine_threadsafe(
                            queue.put(sse_pack("complete", {
                                **ev,
                                "plain_text": plain_txt,
                                "markdown": md_txt,
                                "srt": srt_txt,
                            })), loop
                        )
                    elif ev_type == "error":
                        asyncio.run_coroutine_threadsafe(
                            queue.put(sse_pack("error", {"message": ev.get("message")})), loop
                        )

            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put(sse_pack("error", {"message": str(e)})), loop
                )
            finally:
                asyncio.run_coroutine_threadsafe(
                    queue.put(None), loop
                )

        loop.run_in_executor(None, run_pipeline)

        while True:
            msg = await queue.get()
            if msg is None:
                break
            yield msg

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
