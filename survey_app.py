import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import json
import re
import os
from pathlib import Path

# Page config
st.set_page_config(
    page_title="AI Maturity Survey Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'combined_data' not in st.session_state:
    st.session_state.combined_data = None
if 'loaded_files' not in st.session_state:
    st.session_state.loaded_files = {}
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'unmapped_clients' not in st.session_state:
    st.session_state.unmapped_clients = []
if 'load_errors' not in st.session_state:
    st.session_state.load_errors = []

def clean_excel_data(df, client_name):
    """Clean and process Excel data from Raw Data sheet"""
    # Raw Data sheet has headers in row 2 (index 1), data starts in row 3 (index 2)
    df.columns = df.iloc[1]  # Row 2 is index 1
    df = df[2:].reset_index(drop=True)  # Data starts at row 3 (index 2)
    
    # Add client identifier
    df['Client'] = client_name
    
    # Convert participant identifier to numeric if possible
    if 'Participant Identifier' in df.columns:
        df['Participant ID'] = pd.to_numeric(df['Participant Identifier'], errors='coerce')
    
    # Map Rating column to Proficiency
    if 'Rating' in df.columns:
        df['Proficiency'] = df['Rating']
    elif 'Proficiency' not in df.columns:
        df['Proficiency'] = 'Unknown'
    
    return df

def load_client_industry_mapping(data_folder='data'):
    """Load client to industry mapping from Excel file"""
    mapping_file = Path(data_folder) / 'client_industry_mapping.xlsx'
    
    if not mapping_file.exists():
        return None, "Mapping file not found. Please create 'client_industry_mapping.xlsx' in the data folder."
    
    try:
        mapping_df = pd.read_excel(mapping_file)
        
        # Strip whitespace from column names
        mapping_df.columns = mapping_df.columns.str.strip()
        
        # Check if required columns exist
        if 'Client' not in mapping_df.columns or 'Industry' not in mapping_df.columns:
            return None, "Mapping file must have 'Client' and 'Industry' columns."
        
        # Strip whitespace from values
        mapping_df['Client'] = mapping_df['Client'].str.strip()
        mapping_df['Industry'] = mapping_df['Industry'].str.strip()
        
        # Create dictionary mapping
        mapping = dict(zip(mapping_df['Client'], mapping_df['Industry']))
        return mapping, None
    except Exception as e:
        return None, f"Error loading mapping file: {str(e)}"

def add_industry_column(df, mapping):
    """Add industry column to dataframe based on client mapping"""
    if mapping is None:
        df['Industry'] = 'Unknown'
        return df, []
    
    # Create a copy to avoid modifying original
    df = df.copy()
    
    # Map industries - this creates the Industry column
    df['Industry'] = df['Client'].map(mapping)
    
    # Track unmapped clients (clients where Industry is NaN)
    unmapped = df[df['Industry'].isna()]['Client'].unique().tolist()
    
    # Fill unmapped with 'Unknown'
    df['Industry'] = df['Industry'].fillna('Unknown')
    
    return df, unmapped

def load_data_from_folder(data_folder='data'):
    """Load all Excel files from the data folder"""
    data_path = Path(data_folder)
    
    if not data_path.exists():
        return None, f"Data folder '{data_folder}' not found. Please create it and add your Excel files.", []
    
    excel_files = list(data_path.glob('*.xlsx')) + list(data_path.glob('*.xls'))
    
    # Exclude the mapping file
    excel_files = [f for f in excel_files if 'client_industry_mapping' not in f.name.lower()]
    
    if not excel_files:
        return None, f"No Excel files found in '{data_folder}' folder.", []
    
    all_dfs = []
    loaded_files = {}
    errors = []
    
    for file_path in excel_files:
        file_name = file_path.name
        client_name = file_name.replace('.xlsx', '').replace('.xls', '').split('__')[0]
        
        try:
            # Read from Raw Data sheet with no header (we'll extract it manually from row 2)
            df = pd.read_excel(file_path, sheet_name='Raw Data', header=None)
            df = clean_excel_data(df, client_name)
            all_dfs.append(df)
            loaded_files[file_name] = len(df)
        except Exception as e:
            error_msg = f"Error loading {file_name}: {str(e)}"
            errors.append(error_msg)
            print(error_msg)  # Also print to console for debugging
    
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        return combined_df, loaded_files, errors
    else:
        return None, "Could not load any files. Check error messages.", errors

def process_multiselect_column(series, get_counts=True):
    """Process multi-select columns that contain comma-separated values"""
    # Handle NaN values
    series = series.fillna('')
    
    all_options = []
    for value in series:
        if pd.isna(value) or value == '':
            continue
        # Split by semicolon or comma
        options = [opt.strip() for opt in str(value).replace(';', ',').split(',') if opt.strip()]
        all_options.extend(options)
    
    if get_counts:
        option_counts = pd.Series(all_options).value_counts()
        return option_counts
    return all_options

def get_question_type(question_text, column_name):
    """Determine question type based on text"""
    text_lower = str(question_text).lower()
    
    # Multi-select indicators
    if 'select all that apply' in text_lower:
        return 'multi-select'
    
    # Free response indicators
    if '[free response]' in text_lower or 'describe' in text_lower or 'write' in text_lower:
        return 'free-response'
    
    # Check data for multi-select pattern (contains commas/semicolons)
    return 'single-select'

def create_bar_chart(data, title, xaxis_title, yaxis_title):
    """Create a styled bar chart"""
    fig = px.bar(
        x=data.index,
        y=data.values,
        title=title,
        labels={'x': xaxis_title, 'y': yaxis_title}
    )
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
        height=400,
        template='plotly_white'
    )
    return fig

def get_demographic_columns(df):
    """Identify demographic columns"""
    demographic_keywords = ['department', 'function', 'office', 'level', 'country', 
                           'region', 'agency', 'network', 'tenure', 'role']
    
    demo_cols = []
    for col in df.columns:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in demographic_keywords):
            demo_cols.append(col)
    
    return demo_cols

def get_question_columns(df, question_type='scored'):
    """Get columns that represent survey questions - whitelist approach"""
    
    # Scored questions whitelist
    scored_questions = [
        'How often do you use AI tools for work-related tasks?',
        'Which of the following best describes how you typically use AI at work? Select all that apply.',
        'Which best describes your AI usage patterns at work?',
        'You need to create a monthly performance summary. How would you use AI for this task?',
        'Which task would current AI tools (like ChatGPT, Copilot, or Gemini) handle most effectively?',
        'Which of the following are the main risks of using current LLMs? Select all that apply.',
        'How can you best protect sensitive information when using AI tools? Select all that apply.',
        'How often do you verify or fact-check AI-generated content before finalizing or sharing it?',
        'When fact-checking AI-generated content, which approaches would be helpful? Select all that apply.',
        'When you use AI, how often do you refine or iterate on your prompts to improve the output?'
    ]
    
    # Organizational readiness questions whitelist
    org_readiness_questions = [
        'Does your company have an AI strategy?',
        'What visible actions have you noticed as a result of your organization\'s AI strategy?',
        'How well are your AI initiatives connected to your organization\'s business goals?',
        'How clearly has your organization explained how your role will evolve as AI is implemented?',
        'How does your senior leadership team demonstrate their own AI usage?',
        'How is your company\'s AI strategy being implemented across the organization?',
        'How well has your company translated its AI strategy into specific usage policies for employees?',
        'How well does your organization manage AI risks and ethical considerations?',
        'Who is primarily responsible for driving AI adoption and change management at your company?',
        'How effective has this approach been at driving AI adoption?',
        'Have you received any training or support from your company on how to use AI?',
        'How does your company approach AI usage expectations?',
        'How well do teams in your organization collaborate to discover and share AI use cases?',
        'Which of the following best describes how you feel about AI?',
        'Do you trust AI to support you in your work?',
        'Which of the following are reasons that limit your AI usage or make you hesitate using AI? Select all that apply.',
        'Which LLMs are you currently using? Select all that apply.',
        'Do you know what AI tools are available at your company and how to access them?',
        'How satisfied are you with the AI tools available to you at work?',
        'How well do you understand the potential benefits of AI for your specific role?'
    ]
    
    # Choose which whitelist to use
    whitelist = scored_questions if question_type == 'scored' else org_readiness_questions
    
    # Find columns that match the whitelist
    question_cols = []
    for col in df.columns:
        col_str = str(col).strip()
        if col_str in whitelist:
            question_cols.append(col)
    
    return question_cols

# Main app
st.title("📊 AI Maturity Survey Analysis Tool")
st.markdown("Upload client survey files and analyze results across multiple surveys")

# Sidebar for data management
with st.sidebar:
    st.header("📁 Data Management")
    
    # Load data on first run or when refresh button is clicked
    if not st.session_state.data_loaded or st.button("🔄 Refresh Data", help="Reload data from the data folder"):
        with st.spinner("Loading survey data..."):
            # Load industry mapping
            industry_mapping, mapping_error = load_client_industry_mapping('data')
            
            if mapping_error:
                st.warning(f"⚠️ {mapping_error}")
                st.info("Create a file called 'client_industry_mapping.xlsx' with columns 'Client' and 'Industry'")
            
            # Load survey data
            result = load_data_from_folder('data')
            
            if result[0] is not None:
                combined_df = result[0]
                loaded_files = result[1]
                load_errors = result[2] if len(result) > 2 else []
                
                # Add industry column
                combined_df, unmapped = add_industry_column(combined_df, industry_mapping)
                
                st.session_state.combined_data = combined_df
                st.session_state.loaded_files = loaded_files
                st.session_state.unmapped_clients = unmapped
                st.session_state.load_errors = load_errors
                st.session_state.data_loaded = True
                
                # Show errors if any
                if load_errors:
                    st.error(f"⚠️ Failed to load {len(load_errors)} file(s)")
                    with st.expander("Show Errors", expanded=True):
                        for error in load_errors:
                            st.text(error)
                
                # Show unmapped clients
                if unmapped:
                    st.warning(f"⚠️ Unmapped clients: {', '.join(unmapped)}")
                    st.info("Add these clients to 'client_industry_mapping.xlsx'")
                
                st.success("✓ Data loaded successfully!")
            else:
                st.error(result[1])
                if len(result) > 2 and result[2]:
                    with st.expander("Show Errors", expanded=True):
                        for error in result[2]:
                            st.text(error)
                st.info("👉 To add data: Create a 'data' folder in the same directory as this app and add your Excel files there.")
    
    # Show data summary
    if st.session_state.combined_data is not None:
        st.divider()
        st.metric("Loaded Clients", len(st.session_state.loaded_files))
        st.metric("Total Responses", len(st.session_state.combined_data))
        
        # Show loaded files
        with st.expander("📄 Loaded Files", expanded=False):
            for file_name, row_count in st.session_state.loaded_files.items():
                st.text(f"• {file_name}: {row_count} responses")
        
        # Show load errors if any
        if st.session_state.load_errors:
            with st.expander("⚠️ Load Errors", expanded=False):
                for error in st.session_state.load_errors:
                    st.text(error)
        
        # Show unmapped clients if any
        if st.session_state.unmapped_clients:
            with st.expander("⚠️ Unmapped Clients", expanded=False):
                for client in st.session_state.unmapped_clients:
                    st.text(f"• {client}")
                st.caption("Add these to client_industry_mapping.xlsx")
        
        st.divider()
        st.caption("💡 To add new surveys: Add Excel files to the 'data' folder and click 'Refresh Data'")

# Main content area
if st.session_state.combined_data is not None:
    df = st.session_state.combined_data.copy()
    
    # Get column types
    demo_cols = get_demographic_columns(df)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Question Explorer", "📈 Demographics", "📋 Raw Data", "📥 Export"])
    
    with tab1:
        st.header("Question Explorer")
        st.markdown("Select a question and apply filters to analyze responses")
        
        # Radio button to select question type
        question_category = st.radio(
            "Question Category",
            options=["📊 Scored Questions", "🏢 Organizational Readiness"],
            horizontal=True,
            key='question_category'
        )
        
        st.divider()
        
        # Determine which questions to show based on selection
        question_type = 'scored' if '📊' in question_category else 'org'
        question_cols = get_question_columns(df, question_type=question_type)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Question selection
            selected_question = st.selectbox(
                "Select Question",
                options=question_cols,
                help="Choose which question to analyze"
            )
        
        with col2:
            # Client filter
            clients = ['All Clients'] + sorted(df['Client'].unique().tolist())
            selected_clients = st.multiselect(
                "Filter by Client",
                options=clients,
                default=['All Clients']
            )
        
        # Filters section
        st.subheader("Filters")
        
        filter_col1, filter_col2 = st.columns(2)
        
        active_filters = {}
        
        with filter_col1:
            # Industry filter
            if 'Industry' in df.columns:
                unique_industries = df['Industry'].dropna().unique()
                industry_options = ['All'] + sorted([str(v) for v in unique_industries if str(v) != 'Unknown'])
                if 'Unknown' in unique_industries:
                    industry_options.append('Unknown')
                
                selected_industries = st.multiselect(
                    "Industry",
                    options=industry_options,
                    default=['All'],
                    key="filter_industry"
                )
                if 'All' not in selected_industries:
                    active_filters['Industry'] = selected_industries
        
        with filter_col2:
            # Proficiency filter
            if 'Proficiency' in df.columns:
                unique_proficiencies = df['Proficiency'].dropna().unique()
                # Order proficiency levels
                proficiency_order = ['AI Expert', 'AI Practitioner', 'AI Experimenter', 'AI Novice']
                ordered_proficiencies = [p for p in proficiency_order if p in unique_proficiencies]
                # Add any unexpected values
                other_proficiencies = [p for p in unique_proficiencies if p not in proficiency_order and str(p) != 'Unknown']
                proficiency_options = ['All'] + ordered_proficiencies + other_proficiencies
                if 'Unknown' in unique_proficiencies:
                    proficiency_options.append('Unknown')
                
                selected_proficiencies = st.multiselect(
                    "AI Proficiency Level",
                    options=proficiency_options,
                    default=['All'],
                    key="filter_proficiency"
                )
                if 'All' not in selected_proficiencies:
                    active_filters['Proficiency'] = selected_proficiencies
        
        # Apply filters
        filtered_df = df.copy()
        
        # Client filter
        if 'All Clients' not in selected_clients and selected_clients:
            filtered_df = filtered_df[filtered_df['Client'].isin(selected_clients)]
        
        # Industry and Proficiency filters
        for col, values in active_filters.items():
            filtered_df = filtered_df[filtered_df[col].isin(values)]
        
        # Show filter summary
        st.info(f"📊 Showing {len(filtered_df)} responses (filtered from {len(df)} total)")
        
        if len(filtered_df) > 0 and selected_question:
            # Analyze the selected question
            st.divider()
            st.subheader(f"Analysis: {selected_question}")
            
            question_data = filtered_df[selected_question].dropna()
            
            # Determine question type
            question_type_check = get_question_type(selected_question, selected_question)
            
            # Check if data contains commas/semicolons (multi-select indicator)
            sample_values = question_data.astype(str).head(20)
            if any((',' in str(v) or ';' in str(v)) for v in sample_values):
                question_type_check = 'multi-select'
            
            # Display based on type
            if question_type_check == 'multi-select':
                st.caption("Multi-select question (respondents could choose multiple options)")
                
                option_counts = process_multiselect_column(question_data, get_counts=True)
                
                # Chart on top
                if len(option_counts) > 0:
                    fig = create_bar_chart(
                        option_counts,
                        f"Response Distribution: {selected_question[:60]}...",
                        "Response Option",
                        "Number of Selections"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Table below - full width
                st.markdown("**Response Counts:**")
                result_df = pd.DataFrame({
                    'Option': option_counts.index,
                    'Count': option_counts.values,
                    'Percentage': (option_counts.values / len(question_data) * 100).round(1)
                })
                st.dataframe(result_df, hide_index=True, use_container_width=True)
            
            elif question_type_check == 'free-response':
                st.caption("Free response question")
                
                # Show sample responses
                st.markdown("**Sample Responses:**")
                sample_responses = question_data.head(10)
                for idx, response in enumerate(sample_responses, 1):
                    with st.expander(f"Response {idx}"):
                        st.write(response)
                
                # Show total count
                st.metric("Total Responses", len(question_data))
                
                # Download option for all responses
                if st.button("📥 Download All Responses (CSV)"):
                    csv = question_data.to_csv(index=False)
                    st.download_button(
                        "Click to Download",
                        csv,
                        f"{selected_question[:30]}_responses.csv",
                        "text/csv"
                    )
            
            else:  # single-select
                st.caption("Single-select question")
                
                value_counts = question_data.value_counts()
                
                # Chart on top
                fig = create_bar_chart(
                    value_counts,
                    f"Response Distribution: {selected_question[:60]}...",
                    "Response Option",
                    "Count"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Table below - full width
                st.markdown("**Response Breakdown:**")
                result_df = pd.DataFrame({
                    'Option': value_counts.index,
                    'Count': value_counts.values,
                    'Percentage': (value_counts.values / len(question_data) * 100).round(1)
                })
                st.dataframe(result_df, hide_index=True, use_container_width=True)
    
    with tab2:
        st.header("Demographic Analysis")
        st.markdown("Analyze the demographic breakdown of your survey respondents")
        
        # Client filter for demographics
        demo_clients = st.multiselect(
            "Filter by Client",
            options=['All Clients'] + sorted(df['Client'].unique().tolist()),
            default=['All Clients'],
            key='demo_client_filter'
        )
        
        demo_filtered_df = df.copy()
        if 'All Clients' not in demo_clients and demo_clients:
            demo_filtered_df = demo_filtered_df[demo_filtered_df['Client'].isin(demo_clients)]
        
        st.info(f"Showing demographics for {len(demo_filtered_df)} responses")
        
        # Show breakdown for Industry and Proficiency
        col1, col2 = st.columns(2)
        
        with col1:
            # Industry breakdown
            if 'Industry' in demo_filtered_df.columns:
                st.subheader("Industry Distribution")
                
                industry_counts = demo_filtered_df['Industry'].value_counts()
                
                fig = create_bar_chart(
                    industry_counts,
                    "Responses by Industry",
                    "Industry",
                    "Count"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                industry_df = pd.DataFrame({
                    'Industry': industry_counts.index,
                    'Count': industry_counts.values,
                    'Percentage': (industry_counts.values / len(demo_filtered_df) * 100).round(1)
                })
                st.dataframe(industry_df, hide_index=True, use_container_width=True)
        
        with col2:
            # Proficiency breakdown
            if 'Proficiency' in demo_filtered_df.columns:
                st.subheader("AI Proficiency Distribution")
                
                proficiency_counts = demo_filtered_df['Proficiency'].value_counts()
                
                fig = create_bar_chart(
                    proficiency_counts,
                    "Responses by Proficiency Level",
                    "Proficiency",
                    "Count"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                proficiency_df = pd.DataFrame({
                    'Proficiency': proficiency_counts.index,
                    'Count': proficiency_counts.values,
                    'Percentage': (proficiency_counts.values / len(demo_filtered_df) * 100).round(1)
                })
                st.dataframe(proficiency_df, hide_index=True, use_container_width=True)
    
    with tab3:
        st.header("Raw Data View")
        st.markdown("Browse and download the complete dataset")
        
        # Get all question columns (both scored and org)
        all_question_cols = get_question_columns(df, question_type='scored') + get_question_columns(df, question_type='org')
        
        # Column selector
        available_columns = ['Client', 'Industry', 'Proficiency'] + all_question_cols
        selected_columns = st.multiselect(
            "Select columns to display",
            options=available_columns,
            default=['Client', 'Industry', 'Proficiency'] + all_question_cols[:5]  # Show first 5 questions by default
        )
        
        if selected_columns:
            display_df = df[selected_columns].copy()
            
            # Show data
            st.dataframe(display_df, use_container_width=True, height=500)
            
            # Download option
            csv = df[selected_columns].to_csv(index=False)
            st.download_button(
                "📥 Download Current View (CSV)",
                csv,
                "survey_data.csv",
                "text/csv"
            )
    
    with tab4:
        st.header("Export Data")
        st.markdown("Download your filtered and analyzed data")
        
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            st.subheader("Full Dataset")
            st.markdown("Export the complete combined dataset")
            
            csv_full = df.to_csv(index=False)
            st.download_button(
                "📥 Download Full Dataset (CSV)",
                csv_full,
                "ai_maturity_full_data.csv",
                "text/csv",
                use_container_width=True
            )
        
        with export_col2:
            st.subheader("Summary Statistics")
            st.markdown("Export summary statistics by client")
            
            # Create summary
            summary_data = []
            for client in df['Client'].unique():
                client_df = df[df['Client'] == client]
                industry = client_df['Industry'].iloc[0] if len(client_df) > 0 else 'Unknown'
                
                # Proficiency breakdown
                proficiency_counts = client_df['Proficiency'].value_counts()
                
                summary_data.append({
                    'Client': client,
                    'Industry': industry,
                    'Total Responses': len(client_df),
                    'AI Experts': proficiency_counts.get('AI Expert', 0),
                    'AI Practitioners': proficiency_counts.get('AI Practitioner', 0),
                    'AI Experimenters': proficiency_counts.get('AI Experimenter', 0),
                    'AI Novices': proficiency_counts.get('AI Novice', 0)
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, hide_index=True, use_container_width=True)
            
            csv_summary = summary_df.to_csv(index=False)
            st.download_button(
                "📥 Download Summary (CSV)",
                csv_summary,
                "ai_maturity_summary.csv",
                "text/csv",
                use_container_width=True
            )

else:
    # Welcome screen
    st.info("👈 Click 'Refresh Data' in the sidebar to load survey data")
    
    st.markdown("""
    ### How to use this tool:
    
    1. **Add Data**: Place your client survey Excel files in the `data` folder (using the **Raw Data** sheet)
    2. **Add Proficiency Column**: Make sure your Raw Data sheet has a "Proficiency" column (in row 2) with values like "AI Expert", "AI Practitioner", etc.
    3. **Create Industry Mapping**: Create `client_industry_mapping.xlsx` with columns 'Client' and 'Industry'
    4. **Load Data**: Click "Refresh Data" in the sidebar
    5. **Explore Questions**: Use the Question Explorer tab to analyze individual questions with filters
    6. **View Demographics**: Analyze the demographic breakdown of respondents
    7. **Access Raw Data**: View and download the complete dataset
    8. **Export**: Download filtered data and summary statistics
    
    ### Raw Data Sheet Structure:
    - **Row 1**: (ignored)
    - **Row 2**: Column headers/questions
    - **Row 3+**: Response data
    
    ### Features:
    - ✅ Automatically loads all client surveys from one location
    - ✅ Filter by client, industry, and AI proficiency level
    - ✅ Visualize response distributions with charts
    - ✅ Handle single-select, multi-select, and free-response questions
    - ✅ Export filtered data and summaries
    - ✅ Toggle between Scored Questions and Organizational Readiness questions
    
    ### Setup Instructions:
    
    **For the person managing the data (Taylor):**
    1. Create a folder called `data` in the same location as this app
    2. Add all your client Excel files to that folder (must have "Raw Data" sheet)
    3. Make sure each file has a "Proficiency" column in row 2 of the Raw Data sheet
    4. Create `client_industry_mapping.xlsx` with two columns: 'Client' and 'Industry'
    5. Click "Refresh Data" to load everything
    
    **For everyone else:**
    - Just use the app! All data is already loaded
    - Filter and analyze without worrying about uploading files
    
    ### Adding New Surveys:
    1. Add new Excel file to the `data` folder (must have "Raw Data" sheet with "Proficiency" column in row 2)
    2. Add client name and industry to `client_industry_mapping.xlsx`
    3. Click "Refresh Data" in the sidebar
    4. New data appears instantly for everyone
    """)
    
    # Show helpful info about data folder
    data_path = Path('data')
    if data_path.exists():
        excel_count = len([f for f in list(data_path.glob('*.xlsx')) + list(data_path.glob('*.xls')) 
                          if 'client_industry_mapping' not in f.name.lower()])
        if excel_count > 0:
            st.success(f"✓ Found {excel_count} Excel file(s) in the data folder. Click 'Refresh Data' to load them.")
        else:
            st.warning("⚠️ The 'data' folder exists but contains no Excel files. Add your survey files there.")
    else:
        st.warning("⚠️ No 'data' folder found. Create one and add your Excel survey files.")
