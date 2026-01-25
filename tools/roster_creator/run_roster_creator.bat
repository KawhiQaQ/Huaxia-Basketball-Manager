@echo off
cd /d "%~dp0"
cd ../..
python tools/roster_creator/roster_creator.py
pause
