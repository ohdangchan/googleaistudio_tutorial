import os
import json
import asyncio
from typing import AsyncGenerator, Optional, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, PARENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ai_youtube_search.downloader import YouTubeDownloader
from ai_youtube_search.stt_service import GeminiTranscriber
from ai_youtube_search.qa_service import GeminiQAService
from ai_youtube_search.csv_db import TranscriptCSVDatabase
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="CINE-AI : Universal Omnilingual YouTube Search",
    description="한 영상 내 모든 언어를 동시 감지하는 AI 유튜브 영상 검색기",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

downloader = YouTubeDownloader(download_dir=DOWNLOAD_DIR)
csv_db = TranscriptCSVDatabase()
_transcriber: Optional[GeminiTranscriber] = None
_qa_service: Optional[GeminiQAService] = None

def get_transcriber() -> GeminiTranscriber:
    global _transcriber
    if _transcriber is None:
        _transcriber = GeminiTranscriber()
    return _transcriber

def get_qa_service() -> GeminiQAService:
    global _qa_service
    if _qa_service is None:
        _qa_service = GeminiQAService()
    return _qa_service

# ================= Strict Input Validation Models =================

class URLRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=500, description="유튜브 영상 링크")

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        clean = v.strip()
        YouTubeDownloader.extract_and_validate_video_id(clean)
        return clean

class QARequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="질문 또는 검색어")
    transcript_context: str = Field(..., min_length=5, description="전사 텍스트 맥락")
    video_title: Optional[str] = Field("영상", max_length=200)

class ChapterRequest(BaseModel):
    transcript_context: str = Field(..., min_length=5, description="전사 텍스트 맥락")
    video_title: Optional[str] = Field("영상", max_length=200)

# ================= Routes =================

@app.get("/")
async def serve_index():
    """웹 메인 UI 서빙."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CINE-AI Service is running."}

@app.get("/api/csv/download")
async def download_csv():
    """저장된 전체 트랜스크립트 CSV 파일 다운로드."""
    if not os.path.exists(csv_db.file_path):
        raise HTTPException(status_code=404, detail="저장된 CSV 파일이 없습니다.")
    return FileResponse(
        csv_db.file_path,
        filename="transcripts_db.csv",
        media_type="text/csv; charset=utf-8",
    )

@app.get("/api/csv/list")
async def list_csv_records():
    """CSV에 저장된 영상 목록 반환."""
    return {"success": True, "records": csv_db.list_history()}

@app.post("/api/info")
async def get_video_info(req: URLRequest):
    """유튜브 영상 메타데이터 및 CSV 캐시 유무 조회."""
    try:
        video_id = YouTubeDownloader.extract_and_validate_video_id(req.url)
        cached = csv_db.get_by_video_id(video_id)
        info = downloader.get_video_info(req.url)
        return {
            "success": True,
            "data": {
                **info,
                "cached": cached is not None,
                "created_at": cached.get("created_at") if cached else None,
                "detected_languages": cached.get("detected_languages") if cached else None,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream")
async def stream_transcription(url: str = Query(..., description="유튜브 영상 URL")):
    """한 영상 내 모든 언어를 동시 감지하며 타임스탬프 전사를 SSE로 스트리밍합니다.
    (기존 CSV에 존재하는 영상은 API 호출 없이 즉시 로드)"""
    # 1. URL 사전 엄격 검증
    try:
        video_id = YouTubeDownloader.extract_and_validate_video_id(url)
    except Exception as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    async def event_generator() -> AsyncGenerator[str, None]:
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def pack(event: str, data: Any) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 2. CSV 캐시 확인
        cached = csv_db.get_by_video_id(video_id)
        if cached and cached.get("transcript_blocks"):
            await queue.put(pack("status", {
                "step": "cached",
                "message": f"💾 CSV 데이터베이스에서 기존 기록을 즉시 불러왔습니다 ({cached.get('created_at')}).",
                "cached": True,
            }))
            await queue.put(pack("info", {
                "video_id": cached.get("video_id"),
                "title": cached.get("title"),
                "channel": cached.get("channel"),
                "duration_str": cached.get("duration_str"),
                "detected_languages": cached.get("detected_languages"),
                "cached": True,
            }))

            for b in cached.get("transcript_blocks", []):
                await queue.put(pack("chunk", b))

            await queue.put(pack("complete", {
                "cached": True,
                "total_speakers": len(set(b.get("speaker", "spk:0") for b in cached.get("transcript_blocks", []))) or 1,
                "detected_languages": cached.get("detected_languages", "다국어"),
                "blocks": cached.get("transcript_blocks", []),
                "full_transcript": cached.get("transcript_text", ""),
                "chapters": cached.get("chapters", []),
            }))
            await queue.put(None)

            while True:
                msg = await queue.get()
                if msg is None:
                    break
                yield msg
            return

        # 3. CSV에 없으면 전방위 다국어 다운로드 및 Gemini 3.5 Transcribe 파이프라인 가동
        await queue.put(pack("status", {"step": "info", "message": "유튜브 영상 정보 확인 중..."}))

        def run_pipeline():
            try:
                info = downloader.get_video_info(url)
                asyncio.run_coroutine_threadsafe(queue.put(pack("info", info)), loop)

                def on_progress(p):
                    asyncio.run_coroutine_threadsafe(queue.put(pack("progress", p)), loop)

                asyncio.run_coroutine_threadsafe(
                    queue.put(pack("status", {"step": "downloading", "message": "고음질 오디오 다운로드 중..."})), loop
                )

                dl = downloader.download_audio(url, progress_callback=on_progress)
                asyncio.run_coroutine_threadsafe(
                    queue.put(pack("downloaded", {**dl, "audio_url": f"/downloads/{dl['file_name']}"})), loop
                )

                asyncio.run_coroutine_threadsafe(
                    queue.put(pack("status", {"step": "transcribing", "message": "Gemini 3.5 전방위 모든 언어 동시 감지 중..."})), loop
                )

                trans_stream = get_transcriber().transcribe_stream(
                    audio_path=dl["file_path"],
                    mime_type=dl["mime_type"],
                )

                accumulated = []
                for ev in trans_stream:
                    ev_type = ev.get("type")
                    if ev_type == "chunk":
                        accumulated.append(ev.get("block"))
                        asyncio.run_coroutine_threadsafe(queue.put(pack("chunk", ev.get("block"))), loop)
                    elif ev_type == "status":
                        asyncio.run_coroutine_threadsafe(queue.put(pack("status", {"step": "transcribing", "message": ev.get("message")})), loop)
                        # CSV에 영구 저장
                        saved_ok = False
                        try:
                            saved_ok = csv_db.save_record(
                                video_id=info["video_id"],
                                url=url,
                                title=info.get("title", ""),
                                channel=info.get("channel", ""),
                                duration_str=info.get("duration_str", ""),
                                detected_languages=ev.get("detected_languages", []),
                                transcript_text=ev.get("full_transcript", ""),
                                transcript_blocks=accumulated,
                            )
                            print(f"[CSV 저장 성공] video_id: {info['video_id']}, blocks: {len(accumulated)}")
                        except Exception as save_err:
                            print(f"[CSV 저장 오류]: {save_err}")

                        asyncio.run_coroutine_threadsafe(
                            queue.put(pack("complete", {**ev, "cached": False, "saved_to_csv": saved_ok})),
                            loop
                        )
                    elif ev_type == "error":
                        asyncio.run_coroutine_threadsafe(queue.put(pack("error", {"message": ev.get("message")})), loop)

            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(pack("error", {"message": str(e)})), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(None, run_pipeline)

        while True:
            msg = await queue.get()
            if msg is None:
                break
            yield msg

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

@app.post("/api/qa")
async def answer_question(req: QARequest):
    """Gemini 3.8 Flash 영상 Q&A 및 시맨틱 타임스탬프 위치 탐색."""
    try:
        answer = get_qa_service().answer_question(
            query=req.query,
            transcript_context=req.transcript_context,
            video_title=req.video_title or "영상",
        )
        return {"success": True, "answer": answer}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chapters")
async def generate_chapters(req: ChapterRequest):
    """Gemini 3.8 Flash 스마트 챕터 생성."""
    try:
        chapters = get_qa_service().generate_smart_chapters(
            transcript_context=req.transcript_context,
            video_title=req.video_title or "영상",
        )
        return {"success": True, "chapters": chapters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
