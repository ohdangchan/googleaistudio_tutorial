@echo off
chcp 65001 > nul
title CINE-AI : AI 유튜브 영상 검색기

echo =================================================================
echo   CINE-AI : AI 유튜브 영상 검색기 (Gemini 3.5 & 3.8 연동)
echo =================================================================
echo.

cd /d "%~dp0"

if exist "C:\Users\HB_OPERATION_NICK\.conda\envs\myenv\python.exe" (
    set "PYTHON_EXE=C:\Users\HB_OPERATION_NICK\.conda\envs\myenv\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [1/2] 파이썬 환경 확인: %PYTHON_EXE%
echo [2/2] CINE-AI 서버 구동 및 브라우저 실행 중...
echo.

"%PYTHON_EXE%" run.py

pause
