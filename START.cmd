@echo off
cd /d "%~dp0"
"runtime\python.exe" paneladmin\launcher.py
if errorlevel 1 pause
