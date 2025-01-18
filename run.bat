@echo off
:: Set PYTHONPATH to include the project root directory
set PYTHONPATH=%CD%

:: Run the desktop assistant application as a Python module
python -m desktopassistant.main

:: Keep the window open if there are any errors
pause
