import os
from typing import Generator, Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class GeminiTranscriber:
    """Gemini 3.5 Transcribe 모델을 활용한 음성 전사(STT) 및 화자 분리 서비스."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            # 윈도우 환경 변수 재시도
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

    def transcribe_stream(
        self,
        audio_path: str,
        mime_type: str = "audio/mp4",
    ) -> Generator[Dict[str, Any], None, None]:
        """오디오 파일을 Gemini 3.5 Transcribe 모델로 전사하며 실시간 이벤트를 yield합니다.

        Yields:
            dict: {
                "type": "status" | "chunk" | "speaker_change" | "complete" | "error",
                ...
            }
        """
        if not os.path.exists(audio_path):
            yield {"type": "error", "message": f"파일을 찾을 수 없습니다: {audio_path}"}
            return

        file_size_bytes = os.path.getsize(audio_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        yield {
            "type": "status",
            "message": f"오디오 파일 준비 완료 ({file_size_mb:.2f} MB, 형식: {mime_type})",
        }

        uploaded_file = None
        try:
            # 20MB 기준: 대용량은 Google File API 업로드, 소용량은 인메모리 바이트 전송
            if file_size_mb > 20.0:
                yield {"type": "status", "message": "대용량 오디오를 Google File API로 업로드 중..."}
                uploaded_file = self.client.files.upload(file=audio_path)
                contents = [uploaded_file]
                yield {"type": "status", "message": "Google File API 업로드 완료. 전사 스트림 시작..."}
            else:
                yield {"type": "status", "message": "오디오 데이터를 읽는 중..."}
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                contents = [
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                ]
                yield {"type": "status", "message": "Gemini 3.5 Transcribe 스트리밍 시작..."}

            # 전사 설정 (화자 분리 & 단어 타임스탬프 활성화)
            generate_content_config = types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                audio_transcription_config=types.AudioTranscriptionConfig(
                    word_timestamp=True,
                    diarization=True,
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
                            speaker = at.speaker_label or "speaker"
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
                        elif part.text:
                            # 텍스트 단독 청크 폴백
                            yield {
                                "type": "chunk",
                                "speaker": current_speaker or "speaker",
                                "text": part.text,
                                "is_new_speaker": False,
                                "words": [],
                            }

            # 최종 완료 이벤트
            yield {
                "type": "complete",
                "total_speakers": len(all_speakers),
                "speakers": sorted(list(all_speakers)),
                "accumulated_items": accumulated_items,
            }

        except Exception as e:
            yield {"type": "error", "message": f"STT 전사 중 오류 발생: {str(e)}"}
        finally:
            # File API로 업로드한 임시 파일이 있다면 정리
            if uploaded_file:
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
            spk = item.get("speaker", "speaker")
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
            spk = item.get("speaker", "speaker")
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
            # 오프셋 형식 예: "0.500s" 또는 float초
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
            spk = item.get("speaker", "speaker")
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
