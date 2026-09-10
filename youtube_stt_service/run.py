import os
import sys
import webbrowser
import threading
import time
import uvicorn

def open_browser(port: int = 8000):
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == "__main__":
    port = 8000
    print("=" * 60)
    print(" YouTube Audio & Gemini 3.5 STT Web Service")
    print(f" URL: http://127.0.0.1:{port}")
    print("=" * 60)

    # 브라우저 자동 오픈 스레드 실행
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # FastAPI 서버 구동
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=False)
