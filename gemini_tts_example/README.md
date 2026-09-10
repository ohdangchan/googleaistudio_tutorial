# Gemini 3.1 Flash TTS Preview (다중 화자 음성 합성) 코드 라인별(Line-by-Line) 상세 해설

이 문서는 `gemini_tts_example.py` 스크립트의 동작 원리와 모든 코드 라인을 한 줄씩 상세히 분석하고 설명합니다.

---

## 1. 개요 및 주요 기능

`gemini_tts_example.py`는 Google의 최신 오디오 생성 모델인 **`gemini-3.1-flash-tts-preview`**를 사용하여 텍스트 대본을 실시간 음성(TTS, Text-to-Speech)으로 합성하는 예제입니다.

### 핵심 특징
- **다중 화자 음성 합성 (Multi-Speaker TTS)**: 대본 속 `Speaker 1`과 `Speaker 2`에 서로 다른 음성 페르소나(`Zephyr`, `Algenib`)를 매핑하여 자연스러운 2인 대담 형식의 오디오를 생성합니다.
- **감정 및 연출 태그 반영 (Emotional & Scene Prompting)**: `[confident]`, `[enthusiastic]`, `[surprised]` 등의 감정 태그와 방송 스튜디오 분위기 설정을 음성의 톤과 억양에 반영합니다.
- **실시간 스트리밍 수신 (Streaming Audio)**: 생성되는 오디오 청크(Chunk)를 실시간으로 스트리밍 받아 진행률을 표시합니다.
- **PCM to WAV 헤더 패키징**: 모델이 반환하는 Raw PCM(L16) 오디오 데이터의 MIME 타입을 파싱하여 표준 재생 장치에서 즉시 들을 수 있는 정규 RIFF WAV 파일로 자동 변환 및 저장합니다.

---

## 2. 사전 준비 및 의존성

코드 실행을 위해 필요한 패키지:
```bash
pip install google-genai python-dotenv
```

프로젝트 루트의 `.env` 파일에 Google AI Studio API 키가 설정되어 있어야 합니다:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

---

## 3. 코드 Line-by-Line 상세 해설

### [Lines 1 ~ 2] 의존성 안내 주석
```python
# To run this code you need to install the following dependencies:
# pip install google-genai
```
- **Line 1~2**: 코드 실행에 필요한 핵심 라이브러리(`google-genai`) 설치 명령어를 안내합니다.

---

### [Lines 4 ~ 11] 모듈 및 라이브러리 임포트 (Import)
```python
import io
import os
import re
import wave
from dotenv import load_dotenv
from google import genai
from google.genai import types
```
- **Line 4 (`import io`)**: 메모리 상에서 바이너리 버퍼(`io.BytesIO`)를 생성하여 디스크 I/O 없이 순수 메모리 내에서 WAV 오디오 컨테이너를 조립할 수 있게 합니다.
- **Line 5 (`import os`)**: API 키 조회(`os.environ.get`) 등 운영체제 환경 변수에 접근하기 위해 사용합니다.
- **Line 6 (`import re`)**: 정규 표현식 모듈입니다. MIME 타입 문자열(예: `audio/l16; rate=24000; channels=1`)에서 비트 심도(Bit depth) 숫자(예: `16`)를 추출할 때 사용합니다.
- **Line 7 (`import wave`)**: 파이썬 표준 라이브러리의 WAV 파일 포맷 생성/인코딩 모듈입니다. 샘플 레이트, 채널 수, 샘플 너비를 헤더에 기록합니다.
- **Line 8 (`from dotenv import load_dotenv`)**: `.env` 파일에 기록된 환경 변수를 현재 프로세스 환경으로 로드합니다.
- **Line 9 (`from google import genai`)**: Google GenAI SDK의 메인 클라이언트 클래스를 가져옵니다.
- **Line 10 (`from google.genai import types`)**: TTS 설정에 필요한 `Content`, `Part`, `SpeechConfig`, `MultiSpeakerVoiceConfig`, `GenerateContentConfig` 등 Pydantic/데이터 타입 클래스를 가져옵니다.

---

### [Lines 13 ~ 17] 바이너리 파일 저장 유틸리티 함수
```python
def save_binary_file(file_name: str, data: bytes):
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")
```
- **Line 13**: 바이너리 데이터를 특정 경로의 파일로 저장하는 보조 함수 `save_binary_file`의 정의입니다.
- **Line 14~15**: 바이너리 쓰기 모드(`"wb"`)로 파일을 열어 완성된 오디오 `data`를 디스크에 기록합니다.
- **Line 16**: 저장이 완료된 파일 경로를 콘솔에 출력합니다.

---

### [Lines 19 ~ 25] 메인 음성 생성 함수 선언 및 API 키 검증
```python
def generate(output_file: str = "output.wav"):
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되어 있지 않습니다.")
```
- **Line 19**: 음성 생성 메인 함수 `generate`의 정의입니다. 기본 저장 파일명은 `"output.wav"`입니다.
- **Line 20 (`load_dotenv()`)**: `.env` 파일을 로드합니다.
- **Line 22~24**: `GEMINI_API_KEY` 환경 변수가 누락되었는지 확인하고, 없을 경우 즉시 `ValueError`를 발생시켜 조기 실패하도록 처리합니다.

---

### [Lines 26 ~ 28] GenAI 클라이언트 인스턴스화 및 모델 지정
```python
    client = genai.Client(api_key=api_key)

    model = "gemini-3.1-flash-tts-preview"
```
- **Line 26**: 발급받은 API 키를 전달하여 `genai.Client` 인스턴스를 초기화합니다.
- **Line 28**: 음성 합성 전용 모델인 `"gemini-3.1-flash-tts-preview"`를 지정합니다.

---

### [Lines 29 ~ 54] 프롬프트 구성 (Scene, Context, 대본 및 감정 태그)
```python
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
```
- **Line 29~32**: 사용자의 요청 컨텐츠를 구성하는 `types.Content` 객체입니다.
- **Line 33~35 (`## Scene:`)**: 오디오 환경적 배경(방송 스튜디오 분위기, 또렷한 마이크)을 지시하여 음향의 울림과 톤을 지시합니다.
- **Line 36~38 (`## Sample Context:`)**: 대화의 전체 상황 맥락(테크 뉴스 앵커와 기자의 속보 보도)을 부여하여 캐릭터의 역할 몰입도를 높입니다.
- **Line 39~52 (`## Transcript:`)**:
  - `Speaker 1`과 `Speaker 2`의 턴(Turn)을 명시하여 화자 전환 타이밍을 모델에 전달합니다.
  - `[confident]`, `[enthusiastic]`, `[surprised]`, `[curious]`, `[intrigued]`, `[excited]` 등의 감정 태그(Emotion Tags)를 사용하여 음성의 어조, 에너지 레벨, 말의 속도와 억양을 세밀하게 디렉팅합니다.

---

### [Lines 55 ~ 82] 모델 생성 설정 (다중 화자 및 보이스 매핑)
```python
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
```
- **Line 55**: `GenerateContentConfig` 설정을 정의합니다.
- **Line 56 (`temperature=1`)**: 음성 억양과 감정 표현의 풍부함을 위해 온도값을 1로 설정합니다.
- **Line 57~59 (`response_modalities=["audio"]`)**: 모델의 출력 모달리티를 텍스트가 아닌 **순수 오디오**로 지정하는 핵심 파라미터입니다.
- **Line 60~62 (`speech_config=types.SpeechConfig(...)`)**: 음성 합성 세부 구성을 담당합니다. `MultiSpeakerVoiceConfig`를 사용하여 여러 화자의 음색을 개별 지정합니다.
- **Line 63~70 (`speaker="Speaker 1"`)**: 대본 속 `Speaker 1`의 목소리로 사전 빌드된 보이스 중 차분하고 신뢰감 있는 `"Zephyr"` 보이스를 바인딩합니다.
- **Line 71~78 (`speaker="Speaker 2"`)**: 대본 속 `Speaker 2`의 목소리로 활기찬 `"Algenib"` 보이스를 바인딩합니다.

---

### [Lines 84 ~ 88] 스트리밍 상태 관리 변수 초기화
```python
    print("음성 생성 스트리밍을 시작합니다...")
    audio_chunks: list[bytes] = []
    detected_mime_type = ""
    chunk_count = 0
```
- **Line 84**: 사용자 콘솔에 오디오 생성 스트리밍 시작을 출력합니다.
- **Line 85 (`audio_chunks`)**: 네트워크를 통해 조각조각 수신되는 오디오 바이너리 청크들을 순서대로 저장할 리스트입니다.
- **Line 86 (`detected_mime_type`)**: 모델 응답 헤더에서 추출할 오디오 MIME 타입(예: `audio/l16; rate=24000; channels=1`)을 저장할 문자열 변수입니다.
- **Line 87 (`chunk_count`)**: 수신된 총 청크 개수를 카운트합니다.

---

### [Lines 89 ~ 106] 실시간 오디오 스트림 수신 루프
```python
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
```
- **Line 89~93**: `client.models.generate_content_stream(...)`을 호출하여 오디오 데이터가 생성되는 즉시 네트워크 스트림으로 받아옵니다.
- **Line 94~95**: 청크 내 `parts`가 비어있으면 다음 청크로 건너뜁니다.
- **Line 96~97**: `part.inline_data`가 있고 실제 바이너리 `data`가 포함되어 있는지 확인합니다.
- **Line 98**: 청크 수 카운터를 1 증가시킵니다.
- **Line 99~100**: 아직 `detected_mime_type`이 기록되지 않은 경우 첫 번째 청크에서 전송된 MIME 타입을 저장합니다.
- **Line 101**: 수신된 바이너리 오디오 조각을 `audio_chunks` 리스트에 누적합니다.
- **Line 102~103**: 현재까지 누적된 바이트 크기를 계산하고, 캐리지 리턴(`\r`)과 `flush=True`를 활용해 한 줄에서 실시간으로 수신 진행률을 갱신 출력합니다.
- **Line 104~105**: 오디오 외에 텍스트 응답이 함께 반환되는 예외 상황에 대비하여 텍스트를 출력합니다.

---

### [Lines 107 ~ 115] 스트림 병합 및 결과 통계 출력
```python
    print("\n스트림 수신 완료.")

    if not audio_chunks:
        print("수신된 오디오 데이터가 없습니다.")
        return

    full_audio_data = b"".join(audio_chunks)
    print(f"총 오디오 크기: {len(full_audio_data):,} bytes (MIME 타입: {detected_mime_type})")
```
- **Line 107**: 스트림 수신이 완료되었음을 출력합니다.
- **Line 109~111**: 수신된 청크가 전혀 없을 경우 안내 메시지를 띄우고 함수를 안전하게 조기 종료합니다.
- **Line 113**: 조각난 바이트 청크 리스트를 `b"".join(...)`으로 하나의 연속된 바이트 시퀀스로 합칩니다.
- **Line 114**: 최종 생성된 오디오의 총 바이트 수와 감지된 MIME 타입을 출력합니다.

---

### [Lines 116 ~ 124] WAV 포맷 검증, 헤더 추가 및 파일 저장
```python
    # 이미 WAV 헤더가 포함되어 있지 않은 경우 WAV 헤더 추가
    if full_audio_data.startswith(b"RIFF"):
        wav_data = full_audio_data
    else:
        wav_data = convert_to_wav(full_audio_data, detected_mime_type)

    save_binary_file(output_file, wav_data)
    print(f"단일 WAV 파일 저장 완료: {output_file}")
```
- **Line 116~118**: 오디오 데이터의 첫 4바이트가 `RIFF` 매직 넘버인지 확인하여 이미 WAV 파일 헤더를 포함하고 있는지 검사합니다.
- **Line 119~120**: `RIFF`로 시작하지 않는 경우(대부분 순수 PCM Raw 데이터인 `audio/l16` 형태), `convert_to_wav` 함수를 호출하여 표준 WAV 헤더를 붙여줍니다.
- **Line 122~123**: 최종 WAV 바이너리를 지정된 파일명(`output_file`)으로 저장하고 완료 메시지를 출력합니다.

---

### [Lines 126 ~ 147] `convert_to_wav` 함수 (Raw PCM을 WAV 컨테이너로 변환)
```python
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
```
- **Line 126~135**: 함수 시그니처 및 독스트링입니다. Raw PCM 바이트 데이터를 입력받아 표준 헤더가 포함된 WAV 바이트를 반환합니다.
- **Line 136 (`parameters = parse_audio_mime_type(mime_type)`)**: MIME 타입 문자열을 파싱하여 비트 심도, 샘플레이트, 채널 수를 딕셔너리로 얻습니다.
- **Line 137~139**: 파싱된 파라미터 값들을 로컬 변수에 할당합니다.
- **Line 141 (`with io.BytesIO() as wav_buffer:`)**: 인메모리 바이너리 스트림을 생성합니다.
- **Line 142 (`with wave.open(wav_buffer, "wb") as wav_file:`)**: 메모리 버퍼를 대상으로 바이너리 쓰기 모드로 WAV 파일 핸들러를 엽니다.
- **Line 143 (`wav_file.setnchannels(num_channels)`)**: 채널 수를 설정합니다 (모노 = 1, 스테레오 = 2).
- **Line 144 (`wav_file.setsampwidth(bits_per_sample // 8)`)**: 샘플당 바이트 크기를 설정합니다 (16비트일 경우 `16 // 8 = 2` 바이트).
- **Line 145 (`wav_file.setframerate(sample_rate)`)**: 오디오의 샘플레이트(Hz)를 설정합니다 (기본 24,000Hz).
- **Line 146 (`wav_file.writeframes(audio_data)`)**: 실제 PCM 오디오 프레임 데이터를 기록합니다. 이때 표준 44바이트 RIFF WAV 헤더가 자동으로 앞에 붙습니다.
- **Line 147 (`return wav_buffer.getvalue()`)**: 완성된 WAV 바이너리 바이트 시퀀스를 반환합니다.

---

### [Lines 149 ~ 188] `parse_audio_mime_type` 함수 (MIME 속성 파싱)
```python
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
```
- **Line 149~157**: 함수 선언 및 독스트링입니다.
- **Line 158~160**: 안전한 기본값(16비트, 24,000Hz, 모노 1채널)을 초기화합니다.
- **Line 162~163**: 전달받은 `mime_type`이 비어있으면 기본값 딕셔너리를 즉시 반환합니다.
- **Line 165 (`parts = mime_type.split(";")`)**: 세미콜론(`;`)으로 구분된 MIME 속성들을 분할합니다 (예: `["audio/l16", " rate=24000", " channels=1"]`).
- **Line 166~167**: 각 속성 앞뒤 공백을 제거하고 소문자로 변환하여 순회합니다.
- **Line 168~172**: `rate=`로 시작하는 경우 등호 뒤의 숫자를 정수로 파싱하여 `rate`에 저장합니다.
- **Line 173~177**: `channels=`로 시작하는 경우 채널 수를 정수로 파싱하여 `channels`에 저장합니다.
- **Line 178~186**: 파라미터에 `l`이 포함된 경우(예: `audio/l16`), 정규식 `l(\d+)`을 통해 비트 수(16)를 찾아 `bits_per_sample`에 저장합니다.
- **Line 187**: 최종 결정된 세 가지 파라미터를 딕셔너리로 묶어 반환합니다.

---

### [Lines 190 ~ 192] 메인 진입점
```python
if __name__ == "__main__":
    generate()
```
- **Line 190~191**: 파이썬 인터프리터에서 스크립트를 직접 실행할 때 `generate()` 함수를 호출하여 기본 파일명 `"output.wav"`로 음성을 생성 및 저장합니다.

---

## 4. 실행 방법

### 기본 실행
```bash
python gemini_tts_example.py
```

실행이 완료되면 디렉토리에 **`output.wav`** 파일이 생성되며, 미디어 플레이어로 열어 두 명의 화자가 대담하는 고품질 음성을 들을 수 있습니다.
이 파일은 `gemini_35_stt_example.py`의 입력 테스트 오디오로 바로 사용할 수 있습니다.
