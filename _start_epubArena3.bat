@echo off
REM Batch-Datei zum Starten von gui3.py mit aktivierter virtueller Umgebung

REM Pfad zum virtuellen Environment (anpassen falls nötig)
set VENV_PATH=.venv

REM Überprüfen ob virtuelle Umgebung existiert
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtuelle Umgebung nicht gefunden unter: %VENV_PATH%
    echo Bitte erstellen Sie eine virtuelle Umgebung mit:
    echo python -m venv venv
    echo und dann: .\venv\Scripts\activate
    echo gefolgt von: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Virtuelle Umgebung aktivieren
call "%VENV_PATH%\Scripts\activate.bat"

REM Python-Skript starten
python gui3.py

REM Pause am Ende (optional, falls Konsolenfenster offen bleiben soll)
pause