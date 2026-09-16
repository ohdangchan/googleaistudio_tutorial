import os
import re
from typing import Generator, Dict, Any, List, Optional
from dotenv import load_dotenv  # type: ignore
from google import genai  # type: ignore
from google.genai import types  # type: ignore

load_dotenv()

LANGUAGE_MAP: Dict[str, Dict[str, Any]] = {
    "ko": {
        "name": "한국어 (Korean)",
        "codes": ["ko-KR"],
        "flag": "🇰🇷",
    },
    "en": {
        "name": "영어 (English)",
        "codes": ["en-US", "en-GB"],
        "flag": "🇺🇸",
    },
    "zh": {
        "name": "중국어 (Chinese)",
        "codes": ["zh-CN", "zh-TW"],
        "flag": "🇨🇳",
    },
    "ja": {
        "name": "일본어 (Japanese)",
        "codes": ["ja-JP"],
        "flag": "🇯🇵",
    },
    "ru": {
        "name": "러시아어 (Russian)",
        "codes": ["ru-RU"],
        "flag": "🇷🇺",
    },
    "es": {
        "name": "스페인어 (Spanish)",
        "codes": ["es-ES", "es-US", "es-419"],
        "flag": "🇪🇸",
    },
    "fr": {
        "name": "프랑스어 (French)",
        "codes": ["fr-FR"],
        "flag": "🇫🇷",
    },
    "de": {
        "name": "독일어 (German)",
        "codes": ["de-DE"],
        "flag": "🇩🇪",
    },
    "hi": {
        "name": "인도어/힌디어 (Hindi & Indian)",
        "codes": ["hi-IN", "ta-IN", "te-IN", "bn-IN"],
        "flag": "🇮🇳",
    },
    "vi": {
        "name": "베트남어 (Vietnamese)",
        "codes": ["vi-VN"],
        "flag": "🇻🇳",
    },
    "th": {
        "name": "태국어 (Thai)",
        "codes": ["th-TH"],
        "flag": "🇹🇭",
    },
    "id": {
        "name": "인도네시아어 (Indonesian)",
        "codes": ["id-ID"],
        "flag": "🇮🇩",
    },
    "fil": {
        "name": "필리핀/타갈로그어 (Filipino)",
        "codes": ["fil-PH", "tl-PH"],
        "flag": "🇵🇭",
    },
    "sea": {
        "name": "동남아어 통합 (Southeast Asian)",
        "codes": ["vi-VN", "th-TH", "id-ID", "fil-PH", "ms-MY"],
        "flag": "🌏",
    },
    "auto": {
        "name": "자동 감지 (Auto Detect)",
        "codes": [
            "ko-KR", "en-US", "ja-JP", "zh-CN", "ru-RU", "es-ES",
            "fr-FR", "de-DE", "hi-IN", "vi-VN", "th-TH", "id-ID"
        ],
        "flag": "🌐",
    },
}

def detect_language_from_text(text: str) -> str:
    """영상 제목이나 텍스트를 분석하여 가장 가능성 높은 언어 코드를 판별합니다."""
    if not text:
        return "auto"

    # 한글 문자 검사
    if re.search(r"[\uac00-\ud7a3\u1100-\u11ff]", text):
        return "ko"
    # 일본어 (히라가나, 가타카나)
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
        return "ja"
    # 키릴 문자 (러시아어)
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
    # 데바나가리 (힌디어/인도어)
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    # 태국어
    if re.search(r"[\u0e00-\u0e7f]", text):
        return "th"
    # 베트남어 특수 성조 부호
    if re.search(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", text, re.IGNORECASE):
        return "vi"
    # 한자 (중국어)
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"

    # 영문/라틴어 기본
    return "en"


class GeminiTranscriber:
    """Gemini 3.5 Transcribe 모델을 활용한 다국어 음성 전사(STT) 및 화자 분리 서비스."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            # 윈도우 사용자 환경 변수 재조회
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
                self.api_key, _ = winreg.QueryValueEx(key, "GEMINI_API_KEY")
                winreg.CloseKey(key)
            except Exception:
                pass

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY가 설정되어 있지 않습니다. .env 파일 또는 시스템 환경 변수를 확인해주세요."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-3.5-transcribe"

    def resolve_language_codes(self, lang_key: str, text_hint: str = "") -> List[str]:
        """선택된 언어 키 및 텍스트 힌트에 따라 최적의 BCP-47 언어 코드 리스트를 구성합니다."""
        lang_key = (lang_key or "auto").lower()

        # 직접 지정된 언어인 경우
        if lang_key in LANGUAGE_MAP and lang_key != "auto":
            return LANGUAGE_MAP[lang_key]["codes"]

        # 자동 감지 모드인 경우 텍스트 힌트(제목 등)로 우선 언어 추출
        hinted_lang = detect_language_from_text(text_hint)
        if hinted_lang != "auto" and hinted_lang in LANGUAGE_MAP:
            prioritized = LANGUAGE_MAP[hinted_lang]["codes"]
            # 우선순위 언어를 맨 앞에 배치하고 나머지 주요 언어들을 힌트로 추가
            base_codes = LANGUAGE_MAP["auto"]["codes"]
            combined = list(prioritized)
            for c in base_codes:
                if c not in combined:
                    combined.append(c)
            return combined

        return LANGUAGE_MAP["auto"]["codes"]

    def transcribe_stream(
        self,
        audio_path: str,
        mime_type: str = "audio/mp4",
        language: str = "auto",
        text_hint: str = "",
    ) -> Generator[Dict[str, Any], None, None]:
        """오디오 파일을 지정된 언어 힌트와 함께 Gemini 3.5 Transcribe 모델로 전사하며 실시간 이벤트를 yield합니다.

        Args:
            audio_path: 오디오 파일 경로
            mime_type: 오디오 MIME 타입
            language: 언어 코드 ('ko', 'en', 'zh', 'ja', 'ru', 'es', 'fr', 'de', 'hi', 'vi', 'th', 'id', 'sea', 'auto')
            text_hint: 영상 제목 등 언어 추론을 위한 힌트 텍스트
        """
        if not os.path.exists(audio_path):
            yield {"type": "error", "message": f"파일을 찾을 수 없습니다: {audio_path}"}
            return

        file_size_bytes = os.path.getsize(audio_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        target_lang_codes = self.resolve_language_codes(language, text_hint)
        lang_display = LANGUAGE_MAP.get(language, {}).get("name", language)

        yield {
            "type": "status",
            "message": f"오디오 준비 완료 ({file_size_mb:.2f} MB) | 설정 언어: {lang_display} ({', '.join(target_lang_codes[:3])})",
        }

        uploaded_file = None
        try:
            # 20MB 기준: 대용량은 Google File API 업로드, 소용량은 인메모리 바이트 전송
            if file_size_mb > 20.0:
                yield {"type": "status", "message": "대용량 오디오를 Google File API로 업로드 중..."}
                uploaded_file = self.client.files.upload(file=audio_path)
                contents = [uploaded_file]
                yield {"type": "status", "message": "Google File API 업로드 완료. 모델 연결 중..."}
            else:
                yield {"type": "status", "message": "오디오 데이터를 읽는 중..."}
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                contents = [
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                ]
                yield {"type": "status", "message": f"Gemini 3.5 Transcribe 실시간 전사 시작 ({lang_display})..."}

            # 다국어 BCP-47 언어 코드 및 화자 분리/단어 타임스탬프 설정
            generate_content_config = types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                audio_transcription_config=types.AudioTranscriptionConfig(  # type: ignore
                    language_codes=target_lang_codes,  # type: ignore
                    word_timestamp=True,  # type: ignore
                    diarization=True,  # type: ignore
                ),
            )

            current_speaker: Optional[str] = None
            all_speakers = set()
            accumulated_items: List[Dict[str, Any]] = []

            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            ):
                if not chunk.candidates:
                    continue

                for candidate in chunk.candidates:
                    if not candidate.content or not candidate.content.parts:
                        continue

                    for part in candidate.content.parts:
                        if part.audio_transcription:
                            at = part.audio_transcription
                            speaker = (at.speaker_label or "").strip() or "spk:0"
                            all_speakers.add(speaker)

                            is_new_speaker = speaker != current_speaker
                            if is_new_speaker:
                                current_speaker = speaker
                                yield {
                                    "type": "speaker_change",
                                    "speaker": speaker,
                                }

                            words_data = []
                            if at.words:
                                for w in at.words:
                                    words_data.append({
                                        "word": w.word,
                                        "start": w.start_offset,
                                        "end": w.end_offset,
                                    })

                            text = at.text or ""
                            if text:
                                item = {
                                    "speaker": speaker,
                                    "text": text,
                                    "words": words_data,
                                }
                                accumulated_items.append(item)
                                yield {
                                    "type": "chunk",
                                    "speaker": speaker,
                                    "text": text,
                                    "is_new_speaker": is_new_speaker,
                                    "words": words_data,
                                }
                        elif part.text and part.text.strip():
                            # 텍스트 단독 청크 누락 방지
                            speaker = current_speaker or "spk:0"
                            all_speakers.add(speaker)
                            item = {
                                "speaker": speaker,
                                "text": part.text,
                                "words": [],
                            }
                            accumulated_items.append(item)
                            yield {
                                "type": "chunk",
                                "speaker": speaker,
                                "text": part.text,
                                "is_new_speaker": False,
                                "words": [],
                            }

            if not all_speakers:
                all_speakers.add("spk:0")

            # 최종 완료 이벤트
            yield {
                "type": "complete",
                "total_speakers": len(all_speakers),
                "speakers": sorted(list(all_speakers)),
                "accumulated_items": accumulated_items,
                "detected_language": lang_display,
            }

        except Exception as e:
            yield {"type": "error", "message": f"STT 전사 중 오류 발생: {str(e)}"}
        finally:
            if uploaded_file and uploaded_file.name:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass

    @staticmethod
    def format_to_plain_text(items: List[Dict[str, Any]]) -> str:
        """대화 청크 목록을 일반 텍스트 형태로 변환합니다."""
        lines = []
        curr_spk = None
        curr_texts = []

        for item in items:
            spk = item.get("speaker", "spk:0")
            text = item.get("text", "")
            if spk != curr_spk:
                if curr_spk is not None and curr_texts:
                    lines.append(f"[{curr_spk}] {''.join(curr_texts).strip()}")
                curr_spk = spk
                curr_texts = [text]
            else:
                curr_texts.append(text)

        if curr_spk is not None and curr_texts:
            lines.append(f"[{curr_spk}] {''.join(curr_texts).strip()}")

        return "\n\n".join(lines)

    @staticmethod
    def format_to_markdown(items: List[Dict[str, Any]], title: str = "YouTube 트랜스크립트") -> str:
        """대화 청크 목록을 마크다운 문서로 변환합니다."""
        md = [f"# {title}\n"]
        curr_spk = None
        curr_texts = []

        for item in items:
            spk = item.get("speaker", "spk:0")
            text = item.get("text", "")
            if spk != curr_spk:
                if curr_spk is not None and curr_texts:
                    md.append(f"**{curr_spk}**\n> {''.join(curr_texts).strip()}\n")
                curr_spk = spk
                curr_texts = [text]
            else:
                curr_texts.append(text)

        if curr_spk is not None and curr_texts:
            md.append(f"**{curr_spk}**\n> {''.join(curr_texts).strip()}\n")

        return "\n".join(md)

    @staticmethod
    def format_to_srt(items: List[Dict[str, Any]]) -> str:
        """단어 타임스탬프를 기반으로 SRT 자막 파일 형식으로 변환합니다."""
        srt_entries = []
        idx = 1

        def parse_offset_to_srt_time(offset_str: str) -> str:
            try:
                s = float(str(offset_str).replace("s", "").strip())
                hrs = int(s // 3600)
                mins = int((s % 3600) // 60)
                secs = int(s % 60)
                millis = int((s - int(s)) * 1000)
                return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"
            except Exception:
                return "00:00:00,000"

        for item in items:
            spk = item.get("speaker", "spk:0")
            words = item.get("words", [])
            text = item.get("text", "").strip()
            if not text:
                continue

            if words:
                start_time = parse_offset_to_srt_time(words[0].get("start", 0))
                end_time = parse_offset_to_srt_time(words[-1].get("end", 0))
            else:
                start_time = "00:00:00,000"
                end_time = "00:00:05,000"

            srt_entries.append(f"{idx}\n{start_time} --> {end_time}\n[{spk}] {text}\n")
            idx += 1

        return "\n".join(srt_entries)
