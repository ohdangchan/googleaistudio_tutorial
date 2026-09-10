# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import mimetypes
import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types


def generate(audio_path: str = "output.wav", show_word_timestamps: bool = False):
    """Gemini 3.5 Transcribe 모델을 사용하여 오디오 파일의 음성을 텍스트로 변환(STT)합니다.
    
    - 화자 분리 (Diarization): 발화자별(spk:0, spk:1 ...) 구분
    - 단어별 타임스탬프 (Word timestamp): 시작/종료 시점 파악
    """
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되어 있지 않습니다. .env 파일을 확인해주세요.")

    if not os.path.exists(audio_path):
        # 스크립트 디렉터리 또는 상위 루트 디렉터리에서도 파일 탐색
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path1 = os.path.join(script_dir, audio_path)
        alt_path2 = os.path.join(script_dir, "..", audio_path)
        if os.path.exists(alt_path1):
            audio_path = alt_path1
        elif os.path.exists(alt_path2):
            audio_path = alt_path2
        else:
            print(f"오류: 오디오 파일 '{audio_path}'을(를) 찾을 수 없습니다.")
            print("참고: 먼저 'gemini_tts_example.py'를 실행하여 'output.wav'를 생성하거나, 존재하는 오디오 파일 경로를 넘겨주세요.")
            return

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print("=" * 60)
    print("Gemini 3.5 Transcribe (음성 인식 & 화자 분리)")
    print("=" * 60)
    print(f"입력 파일: {audio_path} ({file_size_mb:.2f} MB)")

    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type or not mime_type.startswith("audio/"):
        mime_type = "audio/wav"

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    client = genai.Client(api_key=api_key)

    model = "gemini-3.5-transcribe"
    contents = [
        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
    ]

    generate_content_config = types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        audio_transcription_config=types.AudioTranscriptionConfig(word_timestamp=True, diarization=True),  # type: ignore
    )

    print("음성 인식(STT) 스트리밍 시작...\n")

    current_speaker = None
    all_speakers = set()

    for chunk in client.models.generate_content_stream(
        model=model,
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

                    # 화자가 바뀌었을 때 줄바꿈 및 화자 라벨 출력
                    if speaker != current_speaker:
                        current_speaker = speaker
                        print(f"\n[{speaker}] ", end="", flush=True)

                    if at.text:
                        print(at.text, end="", flush=True)

                    if show_word_timestamps and at.words:
                        print("\n  [단어 타임스탬프]")
                        for w in at.words:
                            print(f"    - {w.start_offset} ~ {w.end_offset}: {w.word}")
                elif part.text:
                    print(part.text, end="", flush=True)

    print("\n\n" + "=" * 60)
    print(f"전사 완료 (감지된 화자 수: {len(all_speakers)}명)")
    print("=" * 60)


if __name__ == "__main__":
    # 실행 시 인자로 다른 파일 경로를 전달할 수 있습니다. 예: python gemini_35_stt_example.py my_voice.wav
    target_file = sys.argv[1] if len(sys.argv) > 1 else "output.wav"
    generate(target_file)
