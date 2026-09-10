# YouTube Audio Downloader & Gemini 3.5 다국어 STT Web Service

유튜브 영상 URL을 입력하면 고음질 오디오 스트림(m4a/webm)을 다운로드하고, Google의 최신 음성 인식 모델 **Gemini 3.5 Transcribe**를 통해 **다국어(한국어, 영어, 일본어, 중국어, 러시아어, 스페인어, 프랑스어, 독일어, 인도어, 동남아어 등)** 음성을 실시간 화자 분리(Diarization)와 함께 전사(STT)하는 웹 서비스입니다.

---

## 🌐 지원 언어 (Multilingual Support)

Gemini 3.5 Transcribe의 다국어 BCP-47 힌트 시스템을 통합하여 다음 언어들을 고정확도로 인식합니다:

| 언어 구분 | BCP-47 코드 | 비고 |
| :--- | :--- | :--- |
| 🌐 **자동 감지 (Auto)** | 영상 제목/메타데이터 분석 기반 자동 판별 및 멀티 힌트 | 다국어 혼합 영상 대응 |
| 🇺🇸 **영어 (English)** | `en-US`, `en-GB` | 미국/영국식 영어 고정확도 인식 |
| 🇰🇷 **한국어 (Korean)** | `ko-KR` | 한국어 화자 분리 및 실시간 전사 |
| 🇨🇳 **중국어 (Chinese)** | `zh-CN`, `zh-TW` | 간체 및 번체 음성 인식 |
| 🇯🇵 **일본어 (Japanese)** | `ja-JP` | 일본어 음성 및 화자 분리 |
| 🇷🇺 **러시아어 (Russian)** | `ru-RU` | 키릴 문자 기반 러시아어 인식 |
| 🇪🇸 **스페인어 (Spanish)** | `es-ES`, `es-US`, `es-419` | 유럽 및 라틴 아메리카 스페인어 |
| 🇫🇷 **프랑스어 (French)** | `fr-FR` | 프랑스어 음성 전사 |
| 🇩🇪 **독일어 (German)** | `de-DE` | 독일어 음성 전사 |
| 🇮🇳 **인도어 (Hindi/Indian)** | `hi-IN`, `ta-IN`, `te-IN`, `bn-IN` | 힌디어 및 주요 인도 지역 언어 |
| 🌏 **동남아어 (SE Asia)** | `vi-VN`, `th-TH`, `id-ID`, `fil-PH`, `ms-MY` | 동남아시아 주요 언어 통합 지원 |
| 🇻🇳 **베트남어 (Vietnamese)** | `vi-VN` | 베트남 성조 음성 인식 |
| 🇹🇭 **태국어 (Thai)** | `th-TH` | 태국어 전사 |
| 🇮🇩 **인도네시아어 (Indonesian)** | `id-ID` | 바하사 인도네시아 |
| 🇵🇭 **필리핀어 (Filipino)** | `fil-PH`, `tl-PH` | 타갈로그/필리핀어 |

---

## 🚀 주요 기능

1. **원클릭 언어 선택 및 자동 감지 (Auto-Detect)**:
   - 검색창 옆 드롭다운과 퀵 필(Pill) 버튼을 통해 마우스 클릭 한 번으로 언어 전환 가능.
   - 영상 제목이나 메타데이터의 문자 체계(한글, 알파벳, 한자, 가나, 키릴, 데바나가리 등)를 분석하여 언어를 자동 추천.
2. **YouTube 고음질 오디오 직접 추출**:
   - `yt-dlp` 기반으로 별도 `ffmpeg` 설치 없이 원본 `m4a` / `webm` 오디오 직접 다운로드 및 캐싱.
3. **실시간 SSE 스트리밍**:
   - 다운로드 진행률 및 Gemini 3.5 음성 전사 결과를 지연 없이 실시간 브라우저 스트리밍.
4. **화자 분리 (Speaker Diarization)**:
   - 다중 화자(`화자 1`, `화자 2`, ...)를 식별하여 색상별 말풍선 카드로 표시.
5. **내장 오디오 플레이어 & 타임스탬프**:
   - 브라우저에서 다운로드된 오디오를 즉시 청취하며 전사 텍스트와 대조 가능.
6. **다양한 형식 내보내기**:
   - 원클릭 복사, `.txt`, `.md`(마크다운), `.srt`(자막) 다운로드 지원.

---

## 🛠️ 실행 방법

### 1. 배치 파일로 실행 (권장)
`youtube_stt_service/run.bat` 파일을 더블 클릭하면 브라우저(`http://127.0.0.1:8000`)가 자동으로 열립니다.

### 2. 터미널에서 실행
```bash
conda activate myenv
cd youtube_stt_service
python run.py
```

---

## 📁 프로젝트 구조

```plaintext
youtube_stt_service/
├── app.py              # FastAPI 서버 (다국어 SSE 스트리밍 & REST API)
├── downloader.py       # yt-dlp 기반 오디오 다운로더 및 메타데이터 파서
├── stt_service.py      # Gemini 3.5 Transcribe 다국어 BCP-47 처리 및 STT 엔진
├── run.py              # 파이썬 실행 스크립트 (브라우저 자동 오픈)
├── run.bat             # 윈도우 원클릭 배치 실행 파일
├── requirements.txt    # 의존성 패키지
├── static/             # 웹 프론트엔드
│   ├── index.html      # 모던 반응형 다국어 UI (Tailwind CSS)
│   └── app.js          # 다국어 선택 연동 및 실시간 SSE 수신
└── downloads/          # 오디오 캐시 디렉토리
```
