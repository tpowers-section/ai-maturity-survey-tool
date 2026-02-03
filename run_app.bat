@echo off
echo Starting AI Maturity Survey Analysis Tool...
echo.
echo If this is your first time running, please wait while packages install...
echo.

REM Install requirements
pip install -r requirements.txt

REM Run the app
streamlit run survey_app.py

pause
