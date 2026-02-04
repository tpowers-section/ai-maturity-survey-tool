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

def create_bar_chart(data, title
