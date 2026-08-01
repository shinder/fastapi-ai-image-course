@echo off
rem start.bat — 啟動開發伺服器（Windows 版，對應 start.sh 的最後一步）
rem
rem --host 0.0.0.0：綁定所有網路介面，同網段的手機／平板才連得進來（教材 4.5）。
rem 只在自己電腦測試的話可以省略。

uv run uvicorn app.main:app --reload --host 0.0.0.0
