@echo off
:: Set PYTHONPATH to include the project root directory
set PYTHONPATH=%CD%

:: Run the desktop assistant application
python desktopassistant/main.py

:: Keep the window open if there are any errors
pause
