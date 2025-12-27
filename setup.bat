@echo off
echo ======================================
echo Voicemail Drop System - Setup
echo ======================================
echo.

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo √ .env file created with API key
) else (
    echo √ .env file already exists
)

if not exist results mkdir results

echo.
echo ======================================
echo Setup Complete!
echo ======================================
echo.
echo To run the demo:
echo   python demo.py
echo.
pause
