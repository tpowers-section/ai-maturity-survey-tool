# Quick Start Guide for Taylor

## What You Have

I've built you a web application that lets you:
1. Upload multiple client survey Excel files
2. Filter responses by client and demographics (department, function, country, etc.)
3. Analyze any question with automatic charts
4. View response distributions for single-select, multi-select, and free-response questions
5. Export filtered data as CSV

## Files You'll Download

1. **survey_app.py** - The main application code
2. **requirements.txt** - List of required Python packages
3. **README.md** - Full documentation
4. **run_app.bat** - Windows launcher (double-click to run)
5. **run_app.sh** - Mac/Linux launcher (double-click to run)

## Getting Started (15 minutes)

### Step 1: Install Python (if you don't have it)
- Go to: https://www.python.org/downloads/
- Download Python 3.9 or newer
- **Important**: Check "Add Python to PATH" during installation
- Restart your computer after installing

### Step 2: Run the App
- Put all the files in a folder (like "AI_Survey_Tool" on your desktop)
- Double-click **run_app.bat** (Windows) or **run_app.sh** (Mac)
- First time will take 2-3 minutes to install packages
- Your browser will open automatically with the app

### Step 3: Upload Data
- Click "Browse files" in the left sidebar
- Upload your client Excel files (the ones with "Raw Data" sheet)
- The app will automatically combine them

### Step 4: Start Analyzing!
- Go to "Question Explorer" tab
- Select any question from the dropdown
- Apply filters (client, department, function, etc.)
- See instant charts and tables

## What Each Tab Does

**🔍 Question Explorer**
- Select any question to analyze
- Filter by client and demographics
- See charts and response distributions
- Handles all question types automatically

**📈 Demographics**
- See breakdown of your respondent population
- Charts for each demographic category
- Filter by client

**📋 Raw Data**
- Browse the complete dataset
- Select which columns to view
- Download as CSV

**📥 Export**
- Download full combined dataset
- Get summary statistics by client

## Tips for Your Workflow

1. **Standardizing Demographics**: Since each client uses different terminology (e.g., different department names), the app shows you the raw values. You might want to standardize these in your Excel files before uploading, OR we can add a mapping feature to the app.

2. **Multi-Select Questions**: The app automatically detects questions where respondents could select multiple options (like Question 2). It counts each selection separately.

3. **Free Response**: For questions like "What is the most useful way you're using AI?", you can view sample responses in the app or download all responses as CSV for deeper analysis.

4. **Adding New Clients**: Just upload more Excel files and they'll automatically be added to your analysis.

## Next Steps / Enhancements

Once you're comfortable with the basic app, we can add:

### Easy Additions:
- **Score calculations** from your Scoring Sheet
- **Benchmark comparisons** (compare client to overall average)
- **More filter combinations** (e.g., "Show me marketers in Food & Beverage")
- **Custom question groupings**

### More Advanced:
- **Automated text analysis** for free response questions (categorization, themes)
- **Trend analysis** if you run surveys over time
- **Custom reports** that generate automatically
- **User authentication** so team members can save their filters

### Database Integration:
If Excel uploads become tedious with 20+ clients, we can:
- Set up a database that stores all surveys
- Build a simple upload interface that processes files automatically
- Add version control for survey updates

## Troubleshooting

**"Python not found" error:**
- Make sure you installed Python and checked "Add to PATH"
- Restart your computer
- Try opening Command Prompt and typing: `python --version`

**App won't start:**
- Open Command Prompt / Terminal
- Navigate to your folder: `cd path/to/your/folder`
- Run: `pip install -r requirements.txt`
- Then run: `streamlit run survey_app.py`

**File upload error:**
- Make sure your Excel file has a sheet named "Raw Data" (exact spelling)
- Make sure the first row of Raw Data has the question text
- Try with the Havas file first to test

**Slow performance:**
- This should handle 20 surveys (~50k-100k total rows) fine
- If you get to 50+ surveys, let me know and I'll optimize

## Want to Deploy for Your Team?

If you want everyone at Section to access this without installing Python:

### Option 1: Streamlit Cloud (Free, 5 minutes)
1. Create a GitHub account
2. Create a private repository
3. Upload these files
4. Deploy on share.streamlit.io
5. Share the URL with your team

**Note**: With free tier, data doesn't persist - users upload files each session

### Option 2: More Robust (if needed later)
- Heroku, AWS, or Google Cloud
- Can add database for persistent storage
- User authentication
- I can help set this up when you're ready!

## Questions?

Come back to this chat and let me know:
- What's working well
- What's confusing
- What features would be most useful
- Any errors you're seeing

I'm here to help troubleshoot and add features!

---

**Ready to test?** Download all the files, double-click the run script, and upload your Havas file to see it in action!
