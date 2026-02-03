#!/bin/bash
echo "Starting AI Maturity Survey Analysis Tool..."
echo ""
echo "If this is your first time running, please wait while packages install..."
echo ""

# Install requirements
pip3 install -r requirements.txt

# Run the app
streamlit run survey_app.py
