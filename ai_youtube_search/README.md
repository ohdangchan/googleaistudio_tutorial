# CINE-AI : Universal Omnilingual AI YouTube Search Engine

Wix `Production Company (Exciting) - Film & TV` 템플릿 레이아웃 기반의 **전방위 다국어 동시 감지(Omnilingual) & CSV 캐시 연동 AI 유튜브 영상 검색기**입니다.

---

## 🌟 핵심 특징

1. **한 영상 내 모든 언어 전방위 동시 감지 (Omnilingual STT)**:
   - 한 영상에서 단 한 가지 언어만 감지하는 제약을 완전히 제거했습니다.
   - 한국어, 영어, 일본어, 중국어, 스페인어, 프랑스어, 독일어, 러시아어, 인도어, 동남아어 등 영상 내에서 발화되는 **모든 언어와 오디오를 제한 없이 실시간 감지**하여 원문 스크립트를 생성합니다.
   - 각 발화 단위(Segment)마다 언어 감지 태그(예: `🇺🇸 영어`, `🇰🇷 한국어`, `🇯🇵 일본어`)를 자동으로 부착합니다.
2. **엄격한 쿼리 검증 & 클린 코드 구조 (Clean Code Architecture)**:
   - **유튜브 URL 철저 검증**: `youtube.com/watch`, `youtu.be`, `shorts`, `embed` 등 모든 정상 규격을 정밀 정규식으로 검증하고 비정상/악성 주소는 사전에 안전하게 차단합니다.
   - **QA 및 검색 쿼리 검증**: 빈 문자열, 공백만 입력된 쿼리, 500자 초과 쿼리, 유효하지 않은 맥락 등을 Pydantic 및 비즈니스 로직 레벨에서 이중 검증합니다.
   - **간결하고 모듈화된 클린 코드**: 불필요한 보일러플레이트를 제거하고 가독성과 유지보수성을 극대화했습니다.
3. **CSV 기반 영구 저장 및 재검색 캐시**:
   - `transcripts_db.csv`에 영상 URL, 감지된 언어 목록, 전사 텍스트, 타임스탬프 JSON, 챕터 JSON을 Excel 호환 `utf-8-sig`로 자동 영구 저장합니다.
   - 동일 영상 재검색 시 **오디오 다운로드 및 Gemini API 호출 없이 0.1초 만에 즉시 로드 (비용 0원)**합니다.
4. **YouTube IFrame 플레이어 & 커스텀 볼륨 조절**:
   - 상단 검색창에 URL 입력 시 영상 즉시 임베드 (마이크, +, 알림 기능 제외).
   - 커스텀 0~100% 음향 크기(볼륨) 조절 슬라이더 및 원클릭 음소거 토글 지원.
5. **Gemini 3.8 Flash 영상 Q&A & 자동 이동/PLAY**:
   - AI 답변 내 타임스탬프(`[MM:SS]`) 클릭 시 영상의 해당 시간 위치로 즉시 이동하여 자동 재생(Play)됩니다.

---

## 🛠️ 실행 방법

### 1. 배치 파일로 실행 (권장)
`ai_youtube_search/run.bat` 더블 클릭 -> 브라우저(`http://127.0.0.1:8080`) 자동 실행.

### 2. 터미널 실행
```bash
conda activate myenv
cd ai_youtube_search
python run.py
```

---

## 📁 디렉토리 구조

```plaintext
ai_youtube_search/
├── app.py              # FastAPI 백엔드 (엄격한 Pydantic 검증, SSE 스트리밍)
├── downloader.py       # 엄격한 유튜브 URL 검증기 & 고음질 오디오 다운로더
├── stt_service.py      # Gemini 3.5 Transcribe 전방위 다국어 동시 감지 엔진
├── qa_service.py       # Gemini 3.8 Flash 영상 Q&A 및 시맨틱 타임스탬프 탐색기
├── csv_db.py           # 엑셀 호환 UTF-8 BOM CSV 데이터베이스
├── transcripts_db.csv  # 영구 저장된 트랜스크립트 데이터베이스
├── run.py              # 원클릭 서버 기동 및 브라우저 오픈 스크립트
├── run.bat             # 윈도우 배치 실행 파일
├── static/
│   ├── index.html      # 시네마 프로덕션 웹 UI
│   ├── app.js          # 플레이어 제어, 볼륨, 다국어 태그 렌더링, 점프 재생
│   └── style.css       # 다크 글래스모피즘 스타일
└── downloads/          # 오디오 캐시 저장소
```
