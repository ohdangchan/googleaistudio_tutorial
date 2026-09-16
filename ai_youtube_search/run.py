import os
import time
import webbrowser
import threading
import uvicorn

def open_browser():
    """서버가 구동된 후 1.5초 뒤에 기본 브라우저를 엽니다."""
    time.sleep(1.5)
    url = "http://127.0.0.1:8080"
    print(f"\n🌐 브라우저를 엽니다: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 65)
    print("🎬 CINE-AI : AI 유튜브 영상 검색기 (Gemini 3.5 & 3.8 연동)")
    print("=" * 65)
    print("• 오디오 다운로드 & 타임스탬프 전사: Gemini 3.5 Transcribe")
    print("• 영상 질의응답 & 시맨틱 위치 검색: Gemini 3.8 Flash")
    print("• 볼륨 조절 & 타임스탬프 클릭 시 자동 점프/재생 지원")
    print("• 웹 서버 주소: http://127.0.0.1:8080")
    print("=" * 65)

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=False)
