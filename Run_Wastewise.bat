@echo off
setlocal
cd /d "%~dp0"
title Wastewise - setup and start

echo.
echo  Wastewise - first-time setup and launch
echo  --------------------------------------
echo  This window will stay open while the app runs.
echo.

where py >nul 2>&1
if errorlevel 1 goto no_python_launcher
py -3.12 --version >nul 2>&1
if errorlevel 1 goto no_python312

if not exist ".venv-ml\Scripts\python.exe" (
    echo Creating the app environment with Python 3.12...
    py -3.12 -m venv .venv-ml
    if errorlevel 1 goto setup_failed
)

set "PYTHON=%CD%\.venv-ml\Scripts\python.exe"

"%PYTHON%" -c "import streamlit, PIL, tensorflow" >nul 2>&1
if errorlevel 1 (
    echo Installing app and image-model packages. This needs internet and may take a few minutes...
    "%PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 goto setup_failed
    "%PYTHON%" -m pip install -r requirements.txt -r requirements-ml.txt
    if errorlevel 1 goto setup_failed
)

if not exist "models\wastewise.keras" (
    echo.
    echo Training the educational image model. The first run downloads pretrained image weights.
    echo Training can take several minutes; please keep this window open.
    "%PYTHON%" train.py --data data_wastewise --epochs 12 --fine-tune-epochs 4
    if errorlevel 1 goto training_failed
)

echo.
echo Starting Wastewise. Your browser should open when the app is ready.
echo To stop the app, press Ctrl+C in this window.
echo.
"%PYTHON%" -m streamlit run app.py
goto finished

:no_python_launcher
echo Python Launcher was not found. Install 64-bit Python 3.12, including the Python Launcher, then double-click this file again.
start "" "https://www.python.org/downloads/windows/"
pause
goto finished

:no_python312
echo Python 3.12 was not found. Install 64-bit Python 3.12, then double-click this file again.
echo The current project environment uses Python 3.13; TensorFlow training needs Python 3.12.
start "" "https://www.python.org/downloads/windows/"
pause
goto finished

:setup_failed
echo.
echo Setup did not finish. Check the messages above; package installation needs an internet connection.
pause
goto finished

:training_failed
echo.
echo Model training did not finish. Check the messages above. You can run this launcher again after resolving the issue.
pause

:finished
endlocal
