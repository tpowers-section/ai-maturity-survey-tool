# AI Maturity Survey Analysis Tool

## Quick Start Guide

### Option 1: Run Locally (Easiest to start)

1. **Install Python** (if you don't have it)
   - Go to https://www.python.org/downloads/
   - Download and install Python 3.9 or newer
   - Make sure to check "Add Python to PATH" during installation

2. **Install Required Packages**
   - Open your terminal/command prompt
   - Navigate to the folder containing these files
   - Run: `pip install -r requirements.txt`

3. **Run the App**
   - In the same folder, run: `streamlit run survey_app.py`
   - Your browser will automatically open with the app
   - If not, go to: http://localhost:8501

4. **Use the App**
   - Upload your Excel files using the sidebar
   - Start analyzing!

### Option 2: Deploy Online (For Team Access)

**Using Streamlit Community Cloud (FREE):**

1. **Create a GitHub Account**
   - Go to https://github.com and sign up (if you don't have an account)

2. **Create a New Repository**
   - Click the "+" in the top right → "New repository"
   - Name it something like "ai-maturity-survey-tool"
   - Make it **Private** (important for your data)
   - Click "Create repository"

3. **Upload Your Files**
   - Click "uploading an existing file"
   - Upload: `survey_app.py`, `requirements.txt`, and this `README.md`
   - Click "Commit changes"

4. **Deploy to Streamlit**
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"
   - Select your repository and branch (main)
   - Set main file path: `survey_app.py`
   - Click "Deploy"
   - Your app will be live in a few minutes!

5. **Share with Team**
   - Copy the URL (will be something like: `your-app-name.streamlit.app`)
   - Share with your team - anyone with the link can access it
   - Note: Since you're using the free tier, data is NOT saved between sessions
     (users need to upload files each time they use it)

### Option 3: More Robust Deployment (if needed later)

If you need:
- Persistent data storage (data saved between sessions)
- More control over hosting
- Higher performance

Consider these options:
- **Heroku** (has free tier, more storage options)
- **AWS/Google Cloud** (more technical, but very scalable)
- **Replit** (easiest for persistent storage)

I can help you set up any of these if needed!

### Features

✅ **Multi-Client Analysis**: Upload multiple client surveys and analyze them together
✅ **Smart Filtering**: Filter by client, demographics (department, function, region, etc.)
✅ **Question Explorer**: Analyze any question with automatic chart generation
✅ **Multiple Question Types**: Handles single-select, multi-select, and free-response questions
✅ **Demographics Dashboard**: See breakdown of your respondent population
✅ **Raw Data Access**: View and download complete datasets
✅ **Export Options**: Download filtered data and summaries as CSV

### File Format

The app expects Excel files with a "Raw Data" sheet where:
- First row contains the question text (column headers)
- Each subsequent row is a survey response
- Works with your current Section survey format

### Tips for Use

1. **Naming Convention**: Name your files like "ClientName__Survey_Date.xlsx" - the app will extract the client name automatically

2. **Demographic Filters**: The app automatically detects demographic columns (department, function, office, level, country, region, etc.)

3. **Multi-Select Questions**: Questions with comma or semicolon-separated values are automatically detected and handled properly

4. **Free Response**: Long text responses can be viewed individually or downloaded as CSV for deeper analysis

5. **Client Comparison**: Upload multiple clients and use the client filter to compare results

### Troubleshooting

**App won't start:**
- Make sure Python 3.9+ is installed
- Run `pip install -r requirements.txt` again
- Check for error messages in the terminal

**File upload error:**
- Make sure your file has a "Raw Data" sheet
- Check that the first row contains column headers
- Try with the sample file first to test

**Slow performance:**
- With 20+ surveys (100k+ rows), the app may slow down
- Consider filtering to specific clients/questions
- For very large datasets, let me know and I can optimize further

### Need Help?

If you run into issues or want to add features:
1. Check the error message in the app or terminal
2. Come back to this chat and describe what's happening
3. I can help troubleshoot or add new features!

### Future Enhancements (we can add these)

Ideas for what we could add next:
- Score calculation automation (from your Scoring Sheet)
- Trend analysis across survey waves
- Benchmark comparisons
- Advanced text analysis for free responses
- Custom report generation
- User authentication
- Persistent database storage
- Email report scheduling

Just let me know what would be most useful!
