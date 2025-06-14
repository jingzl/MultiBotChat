@echo off
cd %~dp0
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload 