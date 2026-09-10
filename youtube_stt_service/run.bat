@echo off
chcp 65001 > nul
echo ============================================================
echo   YouTube Audio Downloader ^& Gemini STT Service
echo ============================================================

set PYTHON_EXE=C:\Users\HB_OPERATION_NICK\.conda\envs\myenv\python.exe

if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

cd /d "%~dp0"
"%PYTHON_EXE%" run.py

pause
