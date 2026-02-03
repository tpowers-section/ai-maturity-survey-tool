# Data Folder

## Purpose
This folder contains all client survey Excel files that the app automatically loads.

## How to Add New Surveys

1. Save your client survey Excel file here
2. File must have a "Raw Data" sheet
3. First row of "Raw Data" should contain question text as column headers
4. Click "Refresh Data" in the app sidebar (or it will auto-load on startup)

## File Naming

Name your files however you want. The app will extract the client name from the filename.

**Examples:**
- `Havas__AI_Maturity_Survey_Oct2025.xlsx` → Client: "Havas"
- `ClientName_Survey_2025.xlsx` → Client: "ClientName"
- `Acme Corp.xlsx` → Client: "Acme Corp"

## Current Files

Place your survey files here. The app will automatically detect and load them all.

## Need Help?

If files aren't loading:
1. Check that they're .xlsx or .xls format
2. Verify they have a "Raw Data" sheet
3. Make sure the first row contains column headers
4. Check for error messages in the app sidebar
```

## Your Final Folder Structure Should Look Like:
```
Data App Vibe Code/
├── survey_app.py
├── requirements.txt
├── run_app.sh
├── run_app.bat
├── SETUP_INSTRUCTIONS.md
├── README.md
├── QUICK_START_TAYLOR.md
├── .gitignore
└── data/
    ├── README.md
    └── (your Excel survey files go here)
