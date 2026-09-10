# Gemini 3.5 Transcribe (STT) 코드 라인별(Line-by-Line) 상세 해설

이 문서는 `gemini_35_stt_example.py` 스크립트의 동작 원리와 모든 코드 라인을 한 줄씩 상세히 분석하고 설명합니다.

---

## 1. 개요 및 주요 기능

`gemini_35_stt_example.py`는 Google의 음성 인식 전용 모델인 **`gemini-3.5-transcribe`**를 활용하여 오디오 파일의 음성을 실시간 스트리밍 방식으로 텍스트로 변환(STT, Speech-to-Text)하는 예제입니다.

### 핵심 특징
- **스트리밍 전사 (Streaming Transcription)**: 전체 오디오를 한 번에 처리하지 않고, 실시간으로 들어오는 청크 단위로 텍스트를 즉시 출력합니다.
- **화자 분리 (Diarization)**: 오디오 내의 여러 발화자(예: `Speaker 1`, `Speaker 2` 등)를 구분하여 화자가 변경될 때마다 화자 태그를 달아 출력합니다.
- **단어별 타임스탬프 (Word Timestamps)**: 옵션 활성화 시 각 단어가 발화된 시작/종료 시점 오프셋(offset) 정보를 제공합니다.
- **CLI 파일 지정 지원**: 커맨드라인 인자로 원하는 오디오 파일 경로를 넘겨 손쉽게 테스트할 수 있습니다.

---

## 2. 사전 준비 및 의존성

코드 실행을 위해 필요한 패키지:
```bash
pip install google-genai python-dotenv
```

또한 프로젝트 루트에 `.env` 파일이 존재해야 하며, Google AI Studio에서 발급받은 API 키가 설정되어 있어야 합니다:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

---

## 3. 코드 Line-by-Line 상세 해설

### [Lines 1 ~ 2] 의존성 주석
```python
# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv
```
- **Line 1~2**: 이 코드를 실행하기 위해 설치해야 하는 파이썬 패키지(`google-genai`, `python-dotenv`)를 안내하는 주석입니다.

---

### [Lines 4 ~ 10] 모듈 및 라이브러리 임포트 (Import)
```python
import mimetypes
import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
```
- **Line 4 (`import mimetypes`)**: 파이썬 내장 모듈입니다. 파일 확장자를 기반으로 오디오 파일의 MIME 타입(예: `audio/wav`, `audio/mp3` 등)을 동적으로 감지하는 데 사용됩니다.
- **Line 5 (`import os`)**: 파일 경로 존재 여부 검사(`os.path.exists`), 파일 크기 확인(`os.path.getsize`), 환경 변수 조회(`os.environ.get`) 등 OS 레벨의 파일 및 환경 작업을 수행합니다.
- **Line 6 (`import sys`)**: CLI 실행 시 사용자가 넘겨준 인자(`sys.argv`)를 읽어와 전사할 오디오 파일 경로를 동적으로 지정할 수 있도록 합니다.
- **Line 7 (`from dotenv import load_dotenv`)**: `.env` 파일에 기록된 환경 변수를 현재 프로세스의 환경 변수 풀(`os.environ`)로 로드하는 함수입니다.
- **Line 8 (`from google import genai`)**: Google의 차세대 통합 GenAI SDK 클라이언트를 불러옵니다.
- **Line 9 (`from google.genai import types`)**: SDK에서 사용하는 데이터 구조 및 설정 클래스(예: `types.Part`, `types.GenerateContentConfig`, `types.AudioTranscriptionConfig` 등)를 가져옵니다.

---

### [Lines 12 ~ 17] 함수 정의 및 독스트링 (Docstring)
```python
def generate(audio_path: str = "output.wav", show_word_timestamps: bool = False):
    """Gemini 3.5 Transcribe 모델을 사용하여 오디오 파일의 음성을 텍스트로 변환(STT)합니다.
    
    - 화자 분리 (Diarization): 발화자별(spk:0, spk:1 ...) 구분
    - 단어별 타임스탬프 (Word timestamp): 시작/종료 시점 파악
    """
```
- **Line 12**: `generate` 함수의 선언부입니다.
  - `audio_path: str = "output.wav"`: 음성 인식을 수행할 오디오 파일의 경로입니다. 기본값으로 `"output.wav"`를 가집니다.
  - `show_word_timestamps: bool = False`: 단어별 시작/끝 타임스탬프를 콘솔에 출력할지 여부를 결정하는 불리언 플래그입니다. 기본값은 `False`입니다.
- **Line 13~17**: 함수의 목적과 지원하는 주요 기능(화자 분리, 단어별 타임스탬프)을 설명하는 독스트링입니다.

---

### [Lines 18 ~ 23] 환경 변수 및 API 키 로드
```python
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되어 있지 않습니다. .env 파일을 확인해주세요.")
```
- **Line 18 (`load_dotenv()`)**: 작업 디렉토리의 `.env` 파일을 탐색하여 환경 변수를 메모리에 로드합니다.
- **Line 20 (`api_key = os.environ.get("GEMINI_API_KEY")`)**: 환경 변수에서 `GEMINI_API_KEY` 값을 추출합니다.
- **Line 21~22**: API 키가 설정되어 있지 않거나 빈 문자열인 경우 `ValueError` 예외를 발생시켜 비정상적인 호출을 사전에 차단합니다.

---

### [Lines 24 ~ 28] 오디오 파일 존재 검증
```python
    if not os.path.exists(audio_path):
        print(f"오류: 오디오 파일 '{audio_path}'을(를) 찾을 수 없습니다.")
        print("참고: 먼저 'gemini_tts_example.py'를 실행하여 'output.wav'를 생성하거나, 존재하는 오디오 파일 경로를 넘겨주세요.")
        return
```
- **Line 24 (`if not os.path.exists(audio_path):`)**: 지정된 경로에 실제 파일이 존재하는지 검증합니다.
- **Line 25~26**: 파일이 없을 경우 친절한 에러 메시지와 함께 자매 스크립트인 `gemini_tts_example.py`를 먼저 실행하거나 파일 경로를 전달하라는 해결 방법을 출력합니다.
- **Line 27 (`return`)**: 에러 발생 시 더 이상 작업을 진행하지 않고 함수를 안전하게 종료합니다.

---

### [Lines 29 ~ 34] 파일 메타데이터 정보 출력
```python
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print("=" * 60)
    print("Gemini 3.5 Transcribe (음성 인식 & 화자 분리)")
    print("=" * 60)
    print(f"입력 파일: {audio_path} ({file_size_mb:.2f} MB)")
```
- **Line 29**: `os.path.getsize(audio_path)`로 바이트 단위의 파일 크기를 구한 뒤 `1024 * 1024`로 나누어 MB 단위로 변환합니다.
- **Line 30~34**: 사용자 터미널에 깔끔한 구분선과 함께 처리할 오디오 파일의 경로와 크기(소수점 둘째 자리)를 출력합니다.

---

### [Lines 35 ~ 38] 오디오 MIME 타입 추론 및 폴백 처리
```python
    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type or not mime_type.startswith("audio/"):
        mime_type = "audio/wav"
```
- **Line 35**: `mimetypes.guess_type(audio_path)`는 파일명의 확장자를 통해 `("audio/wav", None)`과 같은 튜플을 반환합니다.
- **Line 36~37**: MIME 타입이 감지되지 않거나 `audio/`로 시작하지 않는 오디오 형식이 아닐 경우 기본값인 `"audio/wav"`로 폴백(fallback)하여 안전성을 확보합니다.

---

### [Lines 39 ~ 41] 바이너리 데이터 읽기
```python
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
```
- **Line 39~40**: 오디오 파일을 바이너리 읽기 모드(`"rb"`)로 열고 파일 전체를 `bytes` 객체인 `audio_bytes`에 로드합니다. `with` 문을 통해 파일 디스크립터가 안전하게 자동 반환됩니다.

---

### [Lines 42 ~ 48] GenAI 클라이언트 생성 및 페이로드 구성
```python
    client = genai.Client(api_key=api_key)

    model = "gemini-3.5-transcribe"
    contents = [
        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
    ]
```
- **Line 42**: API 키를 전달하여 Google GenAI 클라이언트 인스턴스(`genai.Client`)를 생성합니다.
- **Line 44**: 음성 인식 전용 모델인 `"gemini-3.5-transcribe"`를 모델 이름으로 지정합니다.
- **Line 45~47**: SDK의 `types.Part.from_bytes(...)` 메서드를 통해 순수 오디오 바이트 데이터와 MIME 타입을 감싸는 멀티모달 파트(Part) 객체를 생성하고, 요청 컨텐츠 리스트(`contents`)에 담습니다.

---

### [Lines 49 ~ 55] 전사 모델 상세 설정 (Config)
```python
    generate_content_config = types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        audio_transcription_config=types.AudioTranscriptionConfig(
            word_timestamp=True,
            diarization=True,
        ),
    )
```
- **Line 49**: 요청 설정을 위한 `GenerateContentConfig` 객체를 정의합니다.
- **Line 50 (`automatic_function_calling=... disable=True`)**: 자동 도구 호출(함수 호출) 기능을 비활성화하여 오직 음성 인식 및 전사에만 리소스와 토큰이 집중되도록 합니다.
- **Line 51~54 (`audio_transcription_config=types.AudioTranscriptionConfig(...)`)**:
  - `word_timestamp=True`: 각 단어별 타임스탬프 정보 수집을 활성화합니다.
  - `diarization=True`: 여러 명의 화자를 자동으로 구분하여 라벨링하는 화자 분리(Diarization)를 활성화합니다.

---

### [Lines 57 ~ 61] 스트리밍 상태 변수 초기화
```python
    print("음성 인식(STT) 스트리밍 시작...\n")

    current_speaker = None
    all_speakers = set()
```
- **Line 57**: 스트리밍 수신이 시작됨을 사용자에게 알립니다.
- **Line 59 (`current_speaker = None`)**: 현재 발화 중인 화자의 라벨을 기억하는 변수입니다. 화자가 바뀔 때 줄바꿈과 화자명을 새로 출력하기 위한 상태 추적용입니다.
- **Line 60 (`all_speakers = set()`)**: 전체 오디오에서 발견된 모든 화자 식별자를 중복 없이 저장하기 위한 집합(Set)입니다.

---

### [Lines 62 ~ 66] 실시간 스트리밍 호출 루프
```python
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
```
- **Line 62~66**: `client.models.generate_content_stream(...)`을 호출하여 서버로부터 실시간 청크 단위의 응답을 반복 수신합니다. 전체 오디오 처리가 끝날 때까지 기다리지 않고 첫 음성 변환 결과부터 즉시 받아볼 수 있습니다.

---

### [Lines 67 ~ 73] 청크 유효성 검사 및 파트 순회
```python
        if not chunk.candidates:
            continue

        for candidate in chunk.candidates:
            if not candidate.content or not candidate.content.parts:
                continue

            for part in candidate.content.parts:
```
- **Line 67~68**: 수신된 `chunk`에 생성된 후보군(`candidates`)이 없으면 무시하고 다음 청크로 넘어갑니다.
- **Line 70~72**: 각 `candidate` 내부에 `content`나 `parts`가 비어 있는지 확인하는 방어적 코드입니다.
- **Line 74**: candidate 내의 각 파트(`part`)를 순회합니다.

---

### [Lines 75 ~ 87] 화자 분리 및 실시간 전사 텍스트 출력
```python
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
```
- **Line 75 (`if part.audio_transcription:`)**: 해당 파트에 음성 전사 전용 메타데이터(`audio_transcription`)가 포함되어 있는지 검사합니다.
- **Line 76 (`at = part.audio_transcription`)**: 전사 정보 객체를 로컬 변수 `at`에 할당합니다.
- **Line 77 (`speaker = at.speaker_label or "speaker"`)**: 인식된 화자 라벨(`spk:0`, `spk:1` 등)을 가져오며, 없을 경우 `"speaker"`로 기본값을 둡니다.
- **Line 78 (`all_speakers.add(speaker)`)**: 발견된 화자를 `all_speakers` 집합에 추가합니다.
- **Line 81~83**: 현재 발화자가 직전 발화자와 다를 경우(`speaker != current_speaker`), 줄을 바꾸고 새 화자 라벨(예: `[Speaker 1]`)을 출력합니다. `flush=True`를 주어 버퍼링 없이 즉시 터미널에 표시합니다.
- **Line 85~86**: 전사된 텍스트(`at.text`)가 있으면 줄바꿈 없이 실시간으로 이어붙여 출력합니다.

---

### [Lines 88 ~ 94] 단어별 타임스탬프 및 폴백 텍스트 처리
```python
                    if show_word_timestamps and at.words:
                        print("\n  [단어 타임스탬프]")
                        for w in at.words:
                            print(f"    - {w.start_offset} ~ {w.end_offset}: {w.word}")
                elif part.text:
                    print(part.text, end="", flush=True)
```
- **Line 88~91**: `show_word_timestamps` 옵션이 켜져 있고 단어 정보(`at.words`)가 제공된 경우, 각 단어(`w.word`)의 시작 시간(`w.start_offset`)과 종료 시간(`w.end_offset`)을 들여쓰기하여 출력합니다.
- **Line 92~93**: 만약 `audio_transcription` 객체 대신 일반 `part.text`로 응답이 도착하는 특이 케이스에 대비한 폴백 처리부입니다.

---

### [Lines 95 ~ 97] 전사 완료 요약 정보 출력
```python
    print("\n\n" + "=" * 60)
    print(f"전사 완료 (감지된 화자 수: {len(all_speakers)}명)")
    print("=" * 60)
```
- **Line 95~97**: 모든 스트림 청크 수신이 완료된 후 구분선과 함께 총 몇 명의 화자가 감지되었는지(`len(all_speakers)`)를 출력합니다.

---

### [Lines 100 ~ 104] 메인 진입점 (CLI 인자 처리)
```python
if __name__ == "__main__":
    # 실행 시 인자로 다른 파일 경로를 전달할 수 있습니다. 예: python gemini_35_stt_example.py my_voice.wav
    target_file = sys.argv[1] if len(sys.argv) > 1 else "output.wav"
    generate(target_file)
```
- **Line 100**: 스크립트가 직접 실행되었을 때(`python gemini_35_stt_example.py`)만 내부 코드가 실행되도록 제어하는 표준 파이썬 진입점 관용구입니다.
- **Line 102 (`target_file = sys.argv[1] if len(sys.argv) > 1 else "output.wav"`)**: 사용자가 커맨드라인에서 오디오 파일 경로 인자를 넘겨주었는지 검사하여, 있으면 그 인자(`sys.argv[1]`)를 사용하고 없으면 기본값인 `"output.wav"`를 타깃 파일로 설정합니다.
- **Line 103 (`generate(target_file)`)**: 결정된 파일 경로를 인자로 넘겨 `generate()` 함수를 실행합니다.

---

## 4. 실행 방법

### 기본 실행 (기본 파일: `output.wav`)
```bash
python gemini_35_stt_example.py
```

### 다른 오디오 파일 지정 실행
```bash
python gemini_35_stt_example.py sample_interview.mp3
```

### 단어별 타임스탬프 활성화 방법
코드 내 `generate(target_file, show_word_timestamps=True)`로 변경하여 실행하면 단어 단위의 시간 오프셋 정보까지 상세히 확인할 수 있습니다.
