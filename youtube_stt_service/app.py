import os
import json
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from downloader import YouTubeDownloader
from stt_service import GeminiTranscriber

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="YouTube Audio Downloader & Gemini STT Service",
    description="유튜브 영상의 오디오를 다운로드하고 Gemini 3.5 Transcribe로 전사하는 웹 서비스",
    version="1.0.0",
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

@app.post("/api/info")
async def get_video_info(req: URLRequest):
    """비디오 URL에 대한 메타데이터를 신속하게 확인합니다."""
    try:
        info = downloader.get_video_info(req.url)
        return {"success": True, "data": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream")
async def stream_transcription(url: str = Query(..., description="YouTube 비디오 URL")):
    """Server-Sent Events(SSE)를 통해 다운로드 진행률 및 Gemini 실시간 전사 결과를 스트리밍합니다."""
    async def event_generator() -> AsyncGenerator[str, None]:
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def sse_pack(event_name: str, payload: dict) -> str:
            return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # 1. 메타데이터 조회
        await queue.put(sse_pack("status", {"step": "info", "message": "유튜브 영상 정보 확인 중..."}))

        def run_pipeline():
            try:
                # 1) 메타데이터 가져오기
                info = downloader.get_video_info(url)
                asyncio.run_coroutine_threadsafe(
                    queue.put(sse_pack("info", info)), loop
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
                    queue.put(sse_pack("status", {"step": "transcribing", "message": "Gemini 3.5 Transcribe 음성 인식 시작..."})), loop
                )

                t_engine = get_transcriber()
                stt_stream = t_engine.transcribe_stream(
                    audio_path=download_res["file_path"],
                    mime_type=download_res["mime_type"],
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
                        # 마크다운, 플레인 텍스트, SRT 등 완성
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

        # 백그라운드 스레드에서 다운로드 & STT 파이프라인 가동
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

# 다운로드된 오디오 및 정적 파일 마운트
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
