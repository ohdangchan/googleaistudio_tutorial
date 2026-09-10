# YouTube Audio Downloader & Gemini 3.5 Transcribe Web Service

유튜브 영상 URL을 입력하면 고음질 오디오 스트림(m4a/webm)을 다운로드하고, Google의 최신 음성 인식 모델 **Gemini 3.5 Transcribe**를 통해 실시간으로 화자 분리(Diarization) 및 트랜스크립트를 추출하는 웹 서비스입니다.

---

## 🚀 주요 기능

1. **YouTube 오디오 직접 다운로드**:
   - `yt-dlp` 기반으로 외부 `ffmpeg` 설치 없이도 m4a/webm 오디오 스트림을 고속으로 직접 다운로드합니다.
   - 이미 다운로드된 영상은 캐싱되어 재요청 시 즉시 처리됩니다.
2. **실시간 SSE(Server-Sent Events) 스트리밍**:
   - 메타데이터 조회 ➔ 오디오 다운로드(진행률/속도) ➔ Gemini 3.5 전사가 실시간으로 웹 브라우저에 표시됩니다.
3. **화자 분리(Speaker Diarization)**:
   - 영상 내 다중 화자(`[화자 1]`, `[화자 2]`, ...)를 자동으로 구분하여 화자별 배지와 색상으로 말풍선을 렌더링합니다.
4. **오디오 플레이어 내장**:
   - 다운로드된 오디오를 브라우저에서 바로 재생할 수 있으며, 오디오 파일 직접 다운로드도 지원합니다.
5. **다양한 포맷 내보내기**:
   - 원클릭 클립보드 복사
   - `.txt` 텍스트 파일 저장
   - `.md` 마크다운 문서 저장
   - `.srt` 타임스탬프 자막 파일 저장

---

## 📁 프로젝트 구조

```plaintext
youtube_stt_service/
├── app.py              # FastAPI 백엔드 (SSE 스트리밍, 정적 파일 서빙)
├── downloader.py       # yt-dlp 기반 유튜브 메타데이터 및 오디오 다운로더
├── stt_service.py      # Gemini 3.5 Transcribe STT 엔진 및 포맷터
├── run.py              # 파이썬 실행기 (서버 구동 및 브라우저 자동 오픈)
├── run.bat             # 윈도우 원클릭 배치 실행 파일
├── requirements.txt    # 필요 패키지 목록
├── static/             # 웹 프론트엔드
│   ├── index.html      # 모던 UI (Tailwind CSS, Lucide Icons)
│   └── app.js          # 실시간 SSE 이벤트 핸들러 및 플레이어 로직
└── downloads/          # 다운로드된 오디오 캐시 저장소
```

---

## 🛠️ 실행 방법

### 1. 배치 파일로 실행 (가장 간편한 방법)
`run.bat` 파일을 더블 클릭하면 브라우저(`http://127.0.0.1:8000`)가 자동으로 열리며 서비스가 실행됩니다.

### 2. 터미널 명령어로 실행
```bash
# 가상환경 활성화 (myenv)
conda activate myenv

# 디렉토리 이동 및 실행
cd youtube_stt_service
python run.py
```

---

## ⚙️ 환경 변수 설정
프로젝트 루트 또는 시스템 환경 변수에 `GEMINI_API_KEY`가 등록되어 있어야 합니다.
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
