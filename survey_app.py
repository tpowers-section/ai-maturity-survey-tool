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

def clean_excel_data(df, client_name):
    """Clean and process uploaded Excel data"""
    # First row contains actual column names
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)
    
    # Add client identifier
    df['Client'] = client_name
    
    # Convert participant identifier to numeric if possible
    if 'Participant Identifier' in df.columns:
        df['Participant ID'] = pd.to_numeric(df['Participant Identifier'], errors='coerce')
    
    return df

def load_data_from_folder(data_folder='data'):
    """Load all Excel files from the data folder"""
    data_path = Path(data_folder)
    
    if not data_path.exists():
        return None, f"Data folder '{data_folder}' not found. Please create it and add your Excel files."
    
    excel_files = list(data_path.glob('*.xlsx')) + list(data_path.glob('*.xls'))
    
    if not excel_files:
        return None, f"No Excel files found in '{data_folder}' folder."
    
    all_dfs = []
    loaded_files = {}
    errors = []
    
    for file_path in excel_files:
        file_name = file_path.name
        client_name = file_name.replace('.xlsx', '').replace('.xls', '').split('__')[0]
        
        try:
            df = pd.read_excel(file_path, sheet_name='Raw Data')
            df = clean_excel_data(df, client_name)
            all_dfs.append(df)
            loaded_files[file_name] = len(df)
        except Exception as e:
            errors.append(f"Error loading {file_name}: {str(e)}")
    
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        return (combined_df, loaded_files, errors) if errors else (combined_df, loaded_files, None)
    else:
        return None, "Could not load any files. Check error messages."

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

def get_question_columns(df):
    """Get columns that represent survey questions"""
    # Exclude system columns
    exclude_cols = ['Client', 'Participant ID', 'Participant Identifier', 'Email Address:', 'Email Address']
    
    # Get demographic columns to exclude
    demo_cols = get_demographic_columns(df)
    
    question_cols = [col for col in df.columns 
                    if col not in exclude_cols and col not in demo_cols 
                    and not col.startswith('Unnamed')]
    
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
            result = load_data_from_folder('data')
            
            if result[0] is not None:
                st.session_state.combined_data = result[0]
                st.session_state.loaded_files = result[1]
                st.session_state.data_loaded = True
                
                # Show errors if any
                if len(result) > 2 and result[2]:
                    for error in result[2]:
                        st.warning(error)
                
                st.success("✓ Data loaded successfully!")
            else:
                st.error(result[1])
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
        
        st.divider()
        st.caption("💡 To add new surveys: Add Excel files to the 'data' folder and click 'Refresh Data'")

# Main content area
if st.session_state.combined_data is not None:
    df = st.session_state.combined_data.copy()
    
    # Get column types
    demo_cols = get_demographic_columns(df)
    question_cols = get_question_columns(df)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Question Explorer", "📈 Demographics", "📋 Raw Data", "📥 Export"])
    
    with tab1:
        st.header("Question Explorer")
        st.markdown("Select a question and apply filters to analyze responses")
        
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
        
        # Demographic filters
        st.subheader("Demographic Filters")
        filter_cols = st.columns(min(len(demo_cols), 4))
        
        active_filters = {}
        for idx, demo_col in enumerate(demo_cols[:4]):  # Show first 4 demographic filters
            with filter_cols[idx % 4]:
                unique_values = df[demo_col].dropna().unique()
                if len(unique_values) > 0:
                    selected_values = st.multiselect(
                        demo_col.replace('What ', '').replace('?', '')[:30] + "...",
                        options=['All'] + sorted([str(v) for v in unique_values]),
                        default=['All'],
                        key=f"filter_{demo_col}"
                    )
                    if 'All' not in selected_values:
                        active_filters[demo_col] = selected_values
        
        # Apply filters
        filtered_df = df.copy()
        
        # Client filter
        if 'All Clients' not in selected_clients and selected_clients:
            filtered_df = filtered_df[filtered_df['Client'].isin(selected_clients)]
        
        # Demographic filters
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
            question_type = get_question_type(selected_question, selected_question)
            
            # Check if data contains commas/semicolons (multi-select indicator)
            sample_values = question_data.astype(str).head(20)
            if any((',' in str(v) or ';' in str(v)) for v in sample_values):
                question_type = 'multi-select'
            
            # Display based on type
            if question_type == 'multi-select':
                st.caption("Multi-select question (respondents could choose multiple options)")
                
                option_counts = process_multiselect_column(question_data, get_counts=True)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    if len(option_counts) > 0:
                        fig = create_bar_chart(
                            option_counts,
                            f"Response Distribution: {selected_question[:60]}...",
                            "Response Option",
                            "Number of Selections"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Response Counts:**")
                    result_df = pd.DataFrame({
                        'Option': option_counts.index,
                        'Count': option_counts.values,
                        'Percentage': (option_counts.values / len(question_data) * 100).round(1)
                    })
                    st.dataframe(result_df, hide_index=True, height=400)
            
            elif question_type == 'free-response':
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
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = create_bar_chart(
                        value_counts,
                        f"Response Distribution: {selected_question[:60]}...",
                        "Response Option",
                        "Count"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Response Breakdown:**")
                    result_df = pd.DataFrame({
                        'Option': value_counts.index,
                        'Count': value_counts.values,
                        'Percentage': (value_counts.values / len(question_data) * 100).round(1)
                    })
                    st.dataframe(result_df, hide_index=True, height=400)
    
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
        
        # Show breakdown for each demographic
        demo_cols_available = [col for col in demo_cols if col in demo_filtered_df.columns]
        
        if demo_cols_available:
            cols_per_row = 2
            for i in range(0, len(demo_cols_available), cols_per_row):
                cols = st.columns(cols_per_row)
                for idx, demo_col in enumerate(demo_cols_available[i:i+cols_per_row]):
                    with cols[idx]:
                        st.subheader(demo_col.replace('What ', '').replace('?', ''))
                        
                        value_counts = demo_filtered_df[demo_col].value_counts()
                        
                        # Chart
                        fig = create_bar_chart(
                            value_counts.head(10),  # Top 10 values
                            "",
                            "",
                            "Count"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Summary stats
                        st.caption(f"Unique values: {len(value_counts)} | Responses: {value_counts.sum()}")
    
    with tab3:
        st.header("Raw Data View")
        st.markdown("Browse and download the complete dataset")
        
        # Column selector
        available_columns = ['Client'] + question_cols
        selected_columns = st.multiselect(
            "Select columns to display",
            options=available_columns,
            default=['Client'] + question_cols[:5]  # Show first 5 questions by default
        )
        
        if selected_columns:
            display_df = df[selected_columns].copy()
            
            # Show data
            st.dataframe(display_df, use_container_width=True, height=500)
            
            # Download option
            csv = display_df.to_csv(index=False)
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
                summary_data.append({
                    'Client': client,
                    'Total Responses': len(client_df),
                    'Response Rate': '—'  # Could calculate if you have invitation data
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, hide_index=True)
            
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
    
    1. **Add Data**: Place your client survey Excel files in the `data` folder
    2. **Load Data**: Click "Refresh Data" in the sidebar
    3. **Explore Questions**: Use the Question Explorer tab to analyze individual questions with filters
    4. **View Demographics**: Analyze the demographic breakdown of respondents
    5. **Access Raw Data**: View and download the complete dataset
    6. **Export**: Download filtered data and summary statistics
    
    ### Features:
    - ✅ Automatically loads all client surveys from one location
    - ✅ Filter by client, demographics, and custom criteria
    - ✅ Visualize response distributions with charts
    - ✅ Handle single-select, multi-select, and free-response questions
    - ✅ Export filtered data and summaries
    
    ### Setup Instructions:
    
    **For the person managing the data (Taylor):**
    1. Create a folder called `data` in the same location as this app
    2. Add all your client Excel files to that folder
    3. Each file should have a "Raw Data" sheet with questions as column headers
    4. Click "Refresh Data" to load everything
    
    **For everyone else:**
    - Just use the app! All data is already loaded
    - Filter and analyze without worrying about uploading files
    
    ### Adding New Surveys:
    1. Add new Excel file to the `data` folder
    2. Click "Refresh Data" in the sidebar
    3. New data appears instantly for everyone
    """)
    
    # Show helpful info about data folder
    data_path = Path('data')
    if data_path.exists():
        excel_count = len(list(data_path.glob('*.xlsx')) + list(data_path.glob('*.xls')))
        if excel_count > 0:
            st.success(f"✓ Found {excel_count} Excel file(s) in the data folder. Click 'Refresh Data' to load them.")
        else:
            st.warning("⚠️ The 'data' folder exists but contains no Excel files. Add your survey files there.")
    else:
        st.warning("⚠️ No 'data' folder found. Create one and add your Excel survey files.")
