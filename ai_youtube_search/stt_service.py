import os
import re
from typing import Generator, Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def detect_segment_language(text: str) -> Dict[str, str]:
    """문장 내 문자 체계를 분석하여 해당 세그먼트의 언어 코드와 라벨을 반환합니다."""
    if not text:
        return {"code": "und", "label": "미상", "flag": "🌐"}
    if re.search(r"[\uac00-\ud7a3\u1100-\u11ff]", text):
        return {"code": "ko", "label": "한국어", "flag": "🇰🇷"}
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
        return {"code": "ja", "label": "일본어", "flag": "🇯🇵"}
    if re.search(r"[\u4e00-\u9fff]", text):
        return {"code": "zh", "label": "중국어", "flag": "🇨🇳"}
    if re.search(r"[\u0400-\u04ff]", text):
        return {"code": "ru", "label": "러시아어", "flag": "🇷🇺"}
    if re.search(r"[\u0900-\u097f]", text):
        return {"code": "hi", "label": "인도어", "flag": "🇮🇳"}
    if re.search(r"[\u0e00-\u0e7f]", text):
        return {"code": "th", "label": "태국어", "flag": "🇹🇭"}
    if re.search(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", text, re.I):
        return {"code": "vi", "label": "베트남어", "flag": "🇻🇳"}
    if re.search(r"[a-zA-Z]", text):
        return {"code": "en", "label": "영어", "flag": "🇺🇸"}
    return {"code": "mul", "label": "다국어", "flag": "🌐"}

def sec_to_str(sec: float) -> str:
    """초를 'MM:SS' 또는 'HH:MM:SS' 포맷 문자열로 변환합니다."""
    s = int(sec)
    h, m, sec_rem = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{sec_rem:02d}" if h > 0 else f"{m:02d}:{sec_rem:02d}"

def parse_offset(offset_val: Any) -> float:
    """오프셋 값을 초 단위 float으로 변환합니다."""
    try:
        return float(str(offset_val).replace("s", "").strip())
    except Exception:
        return 0.0

class GeminiTranscriber:
    """한 영상 내 모든 언어를 동시 감지(Omnilingual)하는 Gemini 3.5 Transcribe 서비스."""

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
        self.model = "gemini-3.5-transcribe"

    def transcribe_stream(
        self,
        audio_path: str,
        mime_type: str = "audio/mp4",
    ) -> Generator[Dict[str, Any], None, None]:
        """한 영상에 포함된 모든 언어를 제한 없이 실시간 감지하여 타임스탬프와 함께 스트리밍 전사합니다."""
        if not os.path.exists(audio_path):
            yield {"type": "error", "message": f"오디오 파일을 찾을 수 없습니다: {audio_path}"}
            return

        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        yield {
            "type": "status",
            "message": f"전방위 다국어 동시 감지 시작 ({size_mb:.1f} MB)",
        }

        upload_ref = None
        try:
            if size_mb > 20.0:
                upload_ref = self.client.files.upload(file=audio_path)
                contents = [upload_ref]
            else:
                with open(audio_path, "rb") as f:
                    contents = [types.Part.from_bytes(data=f.read(), mime_type=mime_type)]

            # 언어 코드 제한을 두지 않고 모든 언어를 전방위 동시 감지
            config = types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                audio_transcription_config=types.AudioTranscriptionConfig(
                    word_timestamp=True,
                    diarization=True,
                ),
            )

            all_speakers = set()
            detected_languages_set = set()
            accumulated_blocks: List[Dict[str, Any]] = []

            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            ):
                if not chunk.candidates:
                    continue

                for cand in chunk.candidates:
                    if not cand.content or not cand.content.parts:
                        continue

                    for part in cand.content.parts:
                        text = ""
                        speaker = "spk:0"
                        words = []
                        start_sec, end_sec = 0.0, 0.0

                        if part.audio_transcription:
                            at = part.audio_transcription
                            speaker = (at.speaker_label or "").strip() or "spk:0"
                            text = (at.text or "").strip()
                            if at.words:
                                for w in at.words:
                                    ws = parse_offset(w.start_offset)
                                    we = parse_offset(w.end_offset)
                                    words.append({"word": w.word, "start": ws, "end": we})
                                start_sec = words[0]["start"]
                                end_sec = words[-1]["end"]
                        elif part.text and part.text.strip():
                            text = part.text.strip()

                        if text:
                            all_speakers.add(speaker)
                            lang_info = detect_segment_language(text)
                            detected_languages_set.add(lang_info["label"])

                            block = {
                                "speaker": speaker,
                                "text": text,
                                "start_sec": start_sec,
                                "end_sec": end_sec,
                                "start_str": sec_to_str(start_sec),
                                "end_str": sec_to_str(end_sec),
                                "lang": lang_info,
                                "words": words,
                            }
                            accumulated_blocks.append(block)
                            yield {"type": "chunk", "block": block}

            all_languages = sorted(list(detected_languages_set)) or ["다국어"]
            full_context = "\n".join(
                f"[{b['start_str']}] {b['speaker']} ({b['lang']['label']}): {b['text']}"
                for b in accumulated_blocks
            )

            yield {
                "type": "complete",
                "total_speakers": len(all_speakers) or 1,
                "speakers": sorted(list(all_speakers)),
                "detected_languages": all_languages,
                "blocks": accumulated_blocks,
                "full_transcript": full_context,
            }

        except Exception as e:
            yield {"type": "error", "message": f"음성 전사 오류: {str(e)}"}
        finally:
            if upload_ref:
                try:
                    self.client.files.delete(name=upload_ref.name)
                except Exception:
                    pass
