# To run this code you need to install the following dependencies:
# pip install google-genai

import io
import os
import re
import wave
from dotenv import load_dotenv
from google import genai
from google.genai import types


def save_binary_file(file_name: str, data: bytes):
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")


def generate(output_file: str = "output.wav"):
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되어 있지 않습니다.")

    client = genai.Client(api_key=api_key)

    model = "gemini-3.1-flash-tts-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""## Scene:
전문적인 방송 뉴스 스튜디오, 잡음 없이 선명하고 또렷한 마이크 음향, 깔끔한 방송 룸 분위기

## Sample Context:
구글의 차세대 AI '제미나이 4.0 프로' 출시와 파격적인 초저가 상용화 소식을 긴급 보도하는 테크 뉴스 앵커의 신뢰감 있고 활기찬 오프닝, 뉴스 앵커가 IT 전문 기자와 함께 구글 제미나이 4.0 프로의 성능과 파격적인 가격 정책에 대해 질의응답을 나누는 상황

## Transcript:
Speaker 1: [confident] 시청자 여러분, 안녕하십니까. 오늘 IT 업계를 뒤흔들 메가톤급 소식이 들어왔습니다.

[enthusiastic] 구글이 마침내 차세대 플래그십 인공지능 모델인 '제미나이 4.0 프로'를 전격 출시했습니다!

[surprised] 놀라운 점은 비약적으로 향상된 성능뿐만이 아닙니다. 기존 모델 대비 90% 이상 대폭 인하된 파격적인 가격으로 상용화가 전격 결정되었습니다.

[confident] 고성능 AI의 진입 장벽을 완전히 허물었다는 평가 속에, 과연 글로벌 AI 생태계에 어떤 변화가 불어닥칠지 잠시 후 심층 리포트에서 전해드리겠습니다.

[curious] 김 기자, 오늘 구글이 기습 발표한 '제미나이 4.0 프로' 소식으로 개발자 커뮤니티가 그야말로 발칵 뒤집혔다고요?
Speaker 2: [enthusiastic] 네, 그렇습니다. 이번 제미나이 4.0 프로는 복합 추론과 코딩 능력이 획기적으로 향상되었는데요, [excited] 무엇보다 놀라운 것은 바로 상용화 가격입니다.
Speaker 1: [intrigued] 성능이 좋아졌는데 가격까지 저렴해졌다는 건가요?
Speaker 2: [confident] 맞습니다. 기존 모델 대비 10분의 1도 안 되는 파격적인 요금제로 출시되면서, 이제 누구나 부담 없이 최상위급 AI를 서비스에 도입할 수 있는 '초저가 AI 시대'가 열렸습니다."""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=[
            "audio",
        ],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 1",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Zephyr"
                            )
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 2",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Algenib"
                            )
                        ),
                    ),
                ]
            ),
        ),
    )

    print("음성 생성 스트리밍을 시작합니다...")
    audio_chunks: list[bytes] = []
    detected_mime_type = ""
    chunk_count = 0

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.parts is None:
            continue
        for part in chunk.parts:
            if part.inline_data and part.inline_data.data:
                chunk_count += 1
                if not detected_mime_type and part.inline_data.mime_type:
                    detected_mime_type = part.inline_data.mime_type
                audio_chunks.append(part.inline_data.data)
                total_bytes = sum(len(c) for c in audio_chunks)
                print(f"\r오디오 스트림 수신 중... (청크: {chunk_count}, 수신된 크기: {total_bytes:,} bytes)", end="", flush=True)
            elif part.text:
                print(f"\n[텍스트]: {part.text}")

    print("\n스트림 수신 완료.")

    if not audio_chunks:
        print("수신된 오디오 데이터가 없습니다.")
        return

    full_audio_data = b"".join(audio_chunks)
    print(f"총 오디오 크기: {len(full_audio_data):,} bytes (MIME 타입: {detected_mime_type})")

    # 이미 WAV 헤더가 포함되어 있지 않은 경우 WAV 헤더 추가
    if full_audio_data.startswith(b"RIFF"):
        wav_data = full_audio_data
    else:
        wav_data = convert_to_wav(full_audio_data, detected_mime_type)

    save_binary_file(output_file, wav_data)
    print(f"단일 WAV 파일 저장 완료: {output_file}")


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file with header for the given raw PCM audio data and parameters.

    Args:
        audio_data: The raw PCM audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the complete WAV file.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = parameters["channels"]

    with io.BytesIO() as wav_buffer:
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(bits_per_sample // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        return wav_buffer.getvalue()

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Parses bits per sample, rate, and channels from an audio MIME type string.

    Args:
        mime_type: The audio MIME type string (e.g., "audio/l16; rate=24000; channels=1").

    Returns:
        A dictionary with "bits_per_sample", "rate", and "channels" keys with integer values.
    """
    bits_per_sample = 16
    rate = 24000
    channels = 1

    if not mime_type:
        return {"bits_per_sample": bits_per_sample, "rate": rate, "channels": channels}

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip().lower()
        if param.startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("channels="):
            try:
                channels = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif "l" in param:
            # Matches audio/l16, l16, etc.
            match = re.search(r"l(\d+)", param)
            if match:
                try:
                    bits_per_sample = int(match.group(1))
                except ValueError:
                    pass

    return {"bits_per_sample": bits_per_sample, "rate": rate, "channels": channels}


if __name__ == "__main__":
    generate()


