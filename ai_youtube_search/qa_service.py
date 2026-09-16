import os
import json
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class GeminiQAService:
    """Gemini 3.8 Flash 기반 영상 내용 질의응답 및 타임스탬프 시맨틱 검색 서비스."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
                self.api_key, _ = winreg.QueryValueEx(key, "GEMINI_API_KEY")
                winreg.CloseKey(key)
            except Exception:
                pass

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-3.8-flash"

    def answer_question(
        self,
        query: str,
        transcript_context: str,
        video_title: str = "영상",
    ) -> str:
        """질문과 트랜스크립트 맥락을 철저히 검증한 후 정확한 답변과 재생 시간[MM:SS]을 제공합니다."""
        if not query or not query.strip():
            raise ValueError("질문 내용이 비어 있습니다.")
        if len(query.strip()) > 500:
            raise ValueError("질문은 최대 500자 이하여야 합니다.")
        if not transcript_context or not transcript_context.strip():
            raise ValueError("분석할 트랜스크립트 맥락이 없습니다.")

        system_instruction = (
            "당신은 세계 최고의 영상 분석 AI 전문가입니다.\n"
            "영상 트랜스크립트(타임스탬프와 발언 내용)를 기반으로 사용자의 질문에 한국어로 친절하고 명확하게 답변하세요.\n"
            "규칙:\n"
            "1. 질문과 관련된 내용이 언급되는 시간 위치를 반드시 '[MM:SS]' (또는 '[HH:MM:SS]') 형식으로 명시하세요.\n"
            "2. 사용자가 클릭하여 바로 영상을 재생할 수 있도록 가장 핵심적인 시점을 우선하여 안내하세요.\n"
            "3. 영상에 없는 내용은 지어내지 말고, 트랜스크립트에 근거하여 설명하세요."
        )

        user_prompt = (
            f"🎬 영상 제목: {video_title}\n\n"
            f"📜 영상 전체 타임스탬프 트랜스크립트:\n{transcript_context}\n\n"
            f"❓ 사용자 질문/검색어: {query.strip()}\n\n"
            f"답변을 작성해주세요:"
        )

        resp = self.client.models.generate_content(
            model=self.model,
            contents=[user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
            ),
        )
        return resp.text.strip() if resp.text else "답변을 생성할 수 없습니다."

    def generate_smart_chapters(
        self,
        transcript_context: str,
        video_title: str = "영상",
    ) -> List[Dict[str, Any]]:
        """트랜스크립트를 분석하여 핵심 챕터 목록(JSON)을 생성합니다."""
        if not transcript_context or not transcript_context.strip():
            return []

        prompt = (
            f"영상 제목: {video_title}\n\n"
            f"트랜스크립트:\n{transcript_context}\n\n"
            "영상의 주요 흐름을 3~6개의 핵심 챕터로 나누어 다음 JSON 배열 포맷으로만 응답하세요.\n"
            '[{"time": "00:00", "seconds": 0, "title": "챕터 제목", "summary": "1줄 요약"}]'
        )

        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            raw = (resp.text or "[]").strip()
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []
