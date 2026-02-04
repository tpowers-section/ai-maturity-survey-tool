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
        
        # Normalize each individual option
        normalized_options = []
        for opt in options:
            # Apply the same normalization as normalize_for_display
            normalized = opt.strip()
            
            # Replace apostrophe/quote variations
            apostrophe_chars = ["'", "'", "'", "`", "´", "'"]
            for char in apostrophe_chars:
                normalized = normalized.replace(char, "'")
            
            quote_chars = [""", """, "«", "»", "„", "‟"]
            for char in quote_chars:
                normalized = normalized.replace(char, '"')
            
            # Remove invisible characters
            invisible_chars = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00a0']
            for char in invisible_chars:
                normalized = normalized.replace(char, '')
            
            # Normalize whitespace
            normalized = ' '.join(normalized.split())
            
            # Capitalize
            normalized = normalized.capitalize()
            
            normalized_options.append(normalized)
        
        all_options.extend(normalized_options)
    
    if get_counts:
        option_counts = pd.Series(all_options).value_counts()
        return option_counts
    return all_options

def get_question_type(question_text, column_name):
    """Determine question type based on text and whitelist"""
    text_lower = str(question_text).lower()
    
    # Check whitelist first - if it has valid responses, it's not free-response
    valid_responses_dict = get_valid_responses()
    if question_text in valid_responses_dict:
        # Has a whitelist - check if multi-select
        if 'select all that apply' in text_lower:
            return 'multi-select'
        else:
            return 'single-select'
    
    # Not in whitelist - treat as free response
    return 'free-response'

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
        "What visible actions have you noticed as a result of your organization's AI strategy?",
        "How well are your AI initiatives connected to your organization's business goals?",
        'How clearly has your organization explained how your role will evolve as AI is implemented?',
        'How does your senior leadership team demonstrate their own AI usage?',
        "How is your company's AI strategy being implemented across the organization?",
        "How well has your company translated its AI strategy into specific usage policies for employees?",
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

def get_valid_responses():
    """Returns a dictionary of valid responses for each question"""
    return {
        # Scored Questions
        'How often do you use AI tools for work-related tasks?': [
            'Never or rarely',
            'A few times a month',
            'Weekly',
            'Several times a week',
            'Daily'
        ],
        
        'Which of the following best describes how you typically use AI at work? Select all that apply.': [
            'Getting quick answers to specific questions or looking up information',
            "Editing or improving text I've already written (emails, documents, presentations)",
            'Writing or debugging code, scripts, or formulas',
            'Creating first drafts of content from scratch (reports, proposals, marketing copy)',
            'Analyzing data or documents to extract insights or summaries',
            'Brainstorming ideas, testing concepts, or getting feedback on my thinking',
            'Building custom prompts, templates, or workflows that I reuse regularly',
            'Using AI for vibe coding to prototype solutions, apps, or products',
            "I don't use AI for work"
        ],
        
        'Which best describes your AI usage patterns at work?': [
            "I don't use AI for work",
            'I create fresh prompts each time I use AI',
            'I maintain a library of prompts that I reuse frequently',
            "I've built custom AI tools (CustomGPTs, Copilot Agents, Google Gems, Claude Projects) for repetitive tasks",
            "I've created workflows that connect AI with other systems (Slack, Salesforce, email) using integrations or code"
        ],
        
        'You need to create a monthly performance summary. How would you use AI for this task?': [
            "Ask AI to write the summary after you've analyzed all the data",
            'Use AI to help analyze each data source, then compile results manually',
            'Create a systematic process where AI handles data analysis and summary generation consistently',
            "I wouldn't use AI for this task"
        ],
        
        'Which task would current AI tools (like ChatGPT, Copilot, or Gemini) handle most effectively?': [
            "Predicting next week's stock market performance for investment decisions",
            'Analyzing presentation slides to evaluate both the visual design and written content for consistency',
            'Providing real-time updates on breaking news events happening right now',
            'Creating a complete slide deck with visual design for an important client presentation'
        ],
        
        'Which of the following are the main risks of using current LLMs? Select all that apply.': [
            'Hallucinations (generating false or misleading information)',
            'Biases in answers',
            'Data privacy concerns when information is shared with an LLM',
            'Vulnerability to manipulation by bad actors'
        ],
        
        'How can you best protect sensitive information when using AI tools? Select all that apply.': [
            'Avoid using AI tools for anything work-related',
            'Verify that the AI tool has SSL/HTTPS encryption before using it',
            'Only share information that you would be comfortable sharing internally with a colleague',
            'Anonymize information by removing identifying details',
            'Use secure company instances or enterprise plans when available'
        ],
        
        'How often do you verify or fact-check AI-generated content before finalizing or sharing it?': [
            'Never: I typically trust the output as is',
            "Rarely: I only verify if something doesn't sound right",
            'Sometimes: I do a quick check against known data or references',
            'Always: I routinely cross-check AI outputs with reliable sources'
        ],
        
        'When fact-checking AI-generated content, which approaches would be helpful? Select all that apply.': [
            'Check if the response uses confident language and specific details',
            'Use a different AI tool to review and verify the content',
            'Look for professional formatting and proper grammar',
            'Cross-reference key claims with reliable external sources',
            'Verify any calculations or data analysis independently',
            'Ask the same AI tool to double-check its work for accuracy'
        ],
        
        'When you use AI, how often do you refine or iterate on your prompts to improve the output?': [
            'Never: I usually just ask once and accept the first response',
            'Rarely: I only tweak the prompt if something feels obviously off',
            'Sometimes: I iterate 2-3 times to reach a good result',
            "Frequently: I systematically refine prompts until I'm satisfied"
        ],
        
        # Organizational Readiness Questions
        'Does your company have an AI strategy?': [
            'Yes, we have a formal AI strategy',
            "We're currently developing an AI strategy",
            "No, we don't have an AI strategy",
            "I'm not sure"
        ],
        
        "What visible actions have you noticed as a result of your organization's AI strategy?": [
            'No visible actions or changes yet',
            'Leadership talks about AI, but no action taken',
            'Small AI pilots in a few areas',
            'AI rollout across multiple departments',
            'AI fully integrated with clear business results'
        ],
        
        "How well are your AI initiatives connected to your organization's business goals?": [
            "No connection - AI projects aren't linked to business goals",
            "Loose connection - We know AI should help but haven't defined how",
            'Clear connection - AI projects are tied to specific business goals with KPIs',
            'Not sure'
        ],
        
        'How clearly has your organization explained how your role will evolve as AI is implemented?': [
            'No explanation of how AI will impact my role',
            "There's clarity that my role is expected to change, but the specifics aren't clear yet",
            'Very clear explanation of how my role will evolve with AI'
        ],
        
        'How does your senior leadership team demonstrate their own AI usage?': [
            'Leaders regularly share how they use AI in their work',
            'Some leaders occasionally mention using AI',
            "Leaders talk about AI but don't show personal usage",
            'Leaders do not talk about AI or show personal usage'
        ],
        
        "How is your company's AI strategy being implemented across the organization?": [
            "We don't have an approach",
            'Multiple uncoordinated AI pilots',
            'We have a central roadmap at the company, team, or functional level',
            'Not sure'
        ],
        
        "How well has your company translated its AI strategy into specific usage policies for employees?": [
            'Clear, enforced policies that directly implement our AI strategy',
            "Some policies exist, but don't clearly connect to our strategy",
            'We have AI strategy but no specific usage policies',
            'No clear strategy or policies'
        ],
        
        'How well does your organization manage AI risks and ethical considerations?': [
            'No policies or guidelines for AI risks or ethics',
            "Basic usage policies exist but don't address risks or ethical considerations",
            'Comprehensive policies covering risks and ethics with active monitoring',
            'Not sure'
        ],
        
        'Who is primarily responsible for driving AI adoption and change management at your company?': [
            'Centralized AI team or Center of Excellence',
            'Individual departments and teams',
            'No clear ownership',
            "I don't know"
        ],
        
        'How effective has this approach been at driving AI adoption?': [
            'Very effective - seeing strong adoption and results',
            'Somewhat effective - making progress but slowly',
            'Not effective - limited adoption despite efforts',
            'Too early to tell'
        ],
        
        'Have you received any training or support from your company on how to use AI?': [
            'Yes',
            'No',
            'True',
            'False'
        ],
        
        'How does your company approach AI usage expectations?': [
            'No clear expectations about AI usage',
            'AI usage is encouraged but not incentivized',
            'AI usage is expected with recognition and rewards',
            'AI usage is required and tied to performance evaluations'
        ],
        
        'How well do teams in your organization collaborate to discover and share AI use cases?': [
            'Strong collaboration - regular cross-team sessions and sharing AI use cases',
            'Some collaboration - occasional sharing of AI use cases between teams',
            'Limited collaboration - teams work mostly in isolation',
            "No collaboration that I'm aware of"
        ],
        
        'Which of the following best describes how you feel about AI?': [
            'Anxious about its implications for me',
            'Overwhelmed about its implications for me',
            'Excited about its implications for me'
        ],
        
        'Do you trust AI to support you in your work?': [
            'Yes',
            'No',
            'True',
            'False'
        ],
        
        'Which of the following are reasons that limit your AI usage or make you hesitate using AI? Select all that apply.': [
            "I'm worried about hallucinations",
            "I'm worried about data security or privacy",
            "I don't know the right use cases or what to use it for",
            "I'm worried I'll get in trouble with my company",
            "I'm worried it will be seen as cheating by my company or manager",
            "I'm worried it will replace me / about the impact on my job",
            "I don't know how to use it",
            'Other'
        ],
        
        'Which LLMs are you currently using? Select all that apply.': [
            'ChatGPT',
            'Perplexity.ai',
            'Microsoft Copilot',
            'Google Gemini',
            'Claude',
            'DeepSeek',
            "xAI's Grok",
            "Meta's Llama",
            'Mistral',
            'Other',
            "I'm not using any LLMs"
        ],
        
        'Do you know what AI tools are available at your company and how to access them?': [
            'No sanctioned tools available',
            "Tools exist but I don't know how to access them",
            'Tools exist with clear access process',
            'Not sure'
        ],
        
        'How satisfied are you with the AI tools available to you at work?': [
            'Very satisfied - they meet all my needs',
            "Somewhat satisfied - they're helpful but have limitations",
            "Dissatisfied - they don't meet my needs",
            "I don't have access to AI tools at work"
        ],
        
        'How well do you understand the potential benefits of AI for your specific role?': [
            'Very clear - I know exactly how AI can help me',
            'Somewhat clear - I see some opportunities',
            'Unclear - I struggle to see how AI applies to my work',
            "No understanding - AI doesn't seem relevant to my role"
        ]
    }

def filter_valid_responses(series, question_text):
    """Minimal filtering - only remove obvious garbage"""
    
    def is_obviously_invalid(value):
        """Check if response is obviously invalid"""
        if pd.isna(value) or value == '':
            return True
        
        value_str = str(value).strip()
        
        # Filter very long responses (likely contamination or free text)
        if len(value_str) > 200:
            return True
        
        # Filter responses with multiple sentences (3+ periods)
        if value_str.count('.') >= 3:
            return True
        
        # Otherwise keep it
        return False
    
    # Apply minimal filter
    filtered = series[~series.apply(is_obviously_invalid)]
    
    return filtered
    
    # Build a blacklist of key phrases from OTHER questions
    def extract_key_phrases(text):
        """Extract distinctive phrases (2-4 words) from text"""
        text = text.lower()
        words = text.split()
        phrases = []
        
        # 2-word phrases
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
        
        # 3-word phrases
        for i in range(len(words) - 2):
            phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        return phrases
    
    # Build blacklist from all OTHER questions
    blacklist_phrases = set()
    for other_question, other_options in valid_responses_dict.items():
        if other_question == question_text:
            continue  # Skip current question
        
        for option in other_options:
            phrases = extract_key_phrases(option)
            blacklist_phrases.update(phrases)
    
    # Remove phrases that also appear in THIS question's valid responses
    # (to avoid false positives)
    current_phrases = set()
    for option in valid_options:
        phrases = extract_key_phrases(option)
        current_phrases.update(phrases)
    
    # Final blacklist = phrases in other questions but NOT in current question
    blacklist_phrases = blacklist_phrases - current_phrases
    
    # Filter function
    def is_valid(value):
        if pd.isna(value) or value == '':
            return False
        
        value_str = str(value).strip()
        
        # Filter obviously invalid
        if len(value_str) > 200 or value_str.count('.') >= 3:
            return False
        
        # Normalize the value
        value_lower = value_str.lower()
        
        # For multi-select, check each part
        if ',' in value_str or ';' in value_str:
            parts = [p.strip() for p in value_str.replace(';', ',').split(',')]
            for part in parts:
                if not part:
                    continue
                
                part_lower = part.lower()
                
                # Check if this part contains blacklisted phrases
                for phrase in blacklist_phrases:
                    if phrase in part_lower:
                        # This part likely belongs to another question
                        return False
            
            return True
        else:
            # Single select - check if it contains blacklisted phrases
            for phrase in blacklist_phrases:
                if phrase in value_lower:
                    # This response likely belongs to another question
                    return False
            
            return True
    
    # Apply filter
    filtered = series[series.apply(is_valid)]
    
    return filtered
    
    # Normalize function for comparison
    def normalize_for_matching(text):
        """Normalize text for fuzzy matching"""
        text = str(text).strip().lower()
        # Replace apostrophes and quotes
        for char in ["'", "'", "'", "`", "´", "'"]:
            text = text.replace(char, "'")
        for char in [""", """, "«", "»", "„", "‟"]:
            text = text.replace(char, '"')
        # Remove invisible chars
        for char in ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00a0']:
            text = text.replace(char, '')
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    # Create normalized valid options
    normalized_valid = [normalize_for_matching(opt) for opt in valid_options]
    
    # Check if key words from valid option appear in response
    def has_key_words(response, valid_option):
        """Check if response contains key words from valid option"""
        # Extract meaningful words (>3 chars, not common words)
        common_words = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are', 'but', 'not', 'you', 'all', 'can', 'have', 'has', 'had', 'our', 'their'}
        
        valid_words = [w for w in valid_option.split() if len(w) > 3 and w not in common_words]
        response_words = set(response.split())
        
        if not valid_words:
            return False
        
        # Count how many key words match
        matches = sum(1 for word in valid_words if word in response_words)
        
        # Need at least 40% of key words to match
        return (matches / len(valid_words)) >= 0.4
    
    # Simple similarity score based on word overlap
    def similarity_score(text1, text2):
        """Calculate similarity between two texts based on word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0
    
    # Filter function
    def is_valid(value):
        if pd.isna(value) or value == '':
            return False
        
        value_str = str(value).strip()
        
        # Filter obviously invalid
        if len(value_str) > 200 or value_str.count('.') >= 3:
            return False
        
        # For multi-select, check if ALL parts are valid
        if ',' in value_str or ';' in value_str:
            parts = [p.strip() for p in value_str.replace(';', ',').split(',')]
            for part in parts:
                if not part:
                    continue
                normalized_part = normalize_for_matching(part)
                
                # Check similarity OR key word match
                is_similar = False
                for valid_opt in normalized_valid:
                    sim = similarity_score(normalized_part, valid_opt)
                    key_match = has_key_words(normalized_part, valid_opt)
                    
                    # Accept if either 30% similarity OR key words match
                    if sim >= 0.3 or key_match:
                        is_similar = True
                        break
                
                if not is_similar:
                    return False
            return True
        else:
            # Single select - check similarity to valid options
            normalized_value = normalize_for_matching(value_str)
            
            # Check similarity to each valid option
            for valid_opt in normalized_valid:
                sim = similarity_score(normalized_value, valid_opt)
                key_match = has_key_words(normalized_value, valid_opt)
                
                # Accept if either 30% similarity OR key words match
                if sim >= 0.3 or key_match:
                    return True
            
            return False
    
    # Apply filter
    filtered = series[series.apply(is_valid)]
    
    return filtered
    
    # Normalize function for comparison
    def normalize_for_matching(text):
        """Normalize text for fuzzy matching"""
        text = str(text).strip().lower()
        # Replace apostrophes and quotes
        for char in ["'", "'", "'", "`", "´", "'"]:
            text = text.replace(char, "'")
        for char in [""", """, "«", "»", "„", "‟"]:
            text = text.replace(char, '"')
        # Remove invisible chars
        for char in ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00a0']:
            text = text.replace(char, '')
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    # Create normalized valid options
    normalized_valid = [normalize_for_matching(opt) for opt in valid_options]
    
    # Simple similarity score based on word overlap
    def similarity_score(text1, text2):
        """Calculate similarity between two texts based on word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0
    
    # Filter function
    def is_valid(value):
        if pd.isna(value) or value == '':
            return False
        
        value_str = str(value).strip()
        
        # Filter obviously invalid
        if len(value_str) > 200 or value_str.count('.') >= 3:
            return False
        
        # For multi-select, check if ALL parts are valid
        if ',' in value_str or ';' in value_str:
            parts = [p.strip() for p in value_str.replace(';', ',').split(',')]
            for part in parts:
                if not part:
                    continue
                normalized_part = normalize_for_matching(part)
                
                # Check if this part is similar to any valid option
                max_similarity = max([similarity_score(normalized_part, valid_opt) 
                                     for valid_opt in normalized_valid])
                
                # Require at least 50% word overlap
                if max_similarity < 0.5:
                    return False
            return True
        else:
            # Single select - check similarity to valid options
            normalized_value = normalize_for_matching(value_str)
            
            # Check similarity to each valid option
            max_similarity = max([similarity_score(normalized_value, valid_opt) 
                                 for valid_opt in normalized_valid])
            
            # Require at least 50% word overlap
            return max_similarity >= 0.5
    
    # Apply filter
    filtered = series[series.apply(is_valid)]
    
    return filtered

def normalize_for_display(series):
    """Normalize responses to group similar variations together"""
    
    def normalize_text(text):
        """Convert text to standardized form"""
        if pd.isna(text) or text == '':
            return ''
        
        text = str(text).strip()
        
        # Replace all apostrophe/quote variations with standard ones
        apostrophe_chars = ["'", "'", "'", "`", "´", "'"]
        for char in apostrophe_chars:
            text = text.replace(char, "'")
        
        quote_chars = [""", """, "«", "»", "„", "‟"]
        for char in quote_chars:
            text = text.replace(char, '"')
        
        # Remove zero-width and invisible characters
        invisible_chars = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00a0']
        for char in invisible_chars:
            text = text.replace(char, '')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Standardize capitalization - capitalize first letter of each sentence
        sentences = text.split('. ')
        sentences = [s.capitalize() for s in sentences]
        text = '. '.join(sentences)
        
        return text
    
    return series.apply(normalize_text)

def normalize_yes_no_responses(series, question_text):
    """Normalize True/False responses to Yes/No for display"""
    yes_no_questions = [
        'Have you received any training or support from your company on how to use AI?',
        'Do you trust AI to support you in your work?'
    ]
    
    if question_text not in yes_no_questions:
        return series
    
    # Map True/False to Yes/No
    mapping = {
        'True': 'Yes',
        'False': 'No',
        'true': 'Yes',
        'false': 'No',
        'Yes': 'Yes',
        'No': 'No',
        'yes': 'Yes',
        'no': 'No'
    }
    
    return series.map(lambda x: mapping.get(str(x).strip(), x))

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
    tab0, tab1, tab2, tab3, tab4 = st.tabs(["📊 Proficiency Overview", "🔍 Question Explorer", "📈 Demographics", "📋 Raw Data", "📥 Export"])
    
    with tab0:
        st.header("Proficiency Overview")
        st.markdown("View AI proficiency distribution across your organization")
        
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            # Client filter
            overview_clients = st.multiselect(
                "Filter by Client",
                options=['All Clients'] + sorted(df['Client'].unique().tolist()),
                default=['All Clients'],
                key='overview_client_filter'
            )
        
        with col2:
            # Industry filter
            if 'Industry' in df.columns:
                unique_industries = df['Industry'].dropna().unique()
                industry_options_overview = ['All'] + sorted([str(v) for v in unique_industries if str(v) != 'Unknown'])
                if 'Unknown' in unique_industries:
                    industry_options_overview.append('Unknown')
                
                overview_industries = st.multiselect(
                    "Filter by Industry",
                    options=industry_options_overview,
                    default=['All'],
                    key='overview_industry_filter'
                )
        
        # Apply filters
        overview_df = df.copy()
        
        if 'All Clients' not in overview_clients and overview_clients:
            overview_df = overview_df[overview_df['Client'].isin(overview_clients)]
        
        if 'All' not in overview_industries and overview_industries:
            overview_df = overview_df[overview_df['Industry'].isin(overview_industries)]
        
        # Show summary
        st.divider()
        st.info(f"📊 Showing {len(overview_df)} responses (filtered from {len(df)} total)")
        
        if len(overview_df) > 0 and 'Proficiency' in overview_df.columns:
            # Calculate proficiency breakdown
            proficiency_counts = overview_df['Proficiency'].value_counts()
            total_responses = len(overview_df)
            
            # Order proficiency levels
            proficiency_order = ['AI Expert', 'AI Practitioner', 'AI Experimenter', 'AI Novice']
            
            # Create metrics row
            st.subheader("Proficiency Distribution")
            
            metric_cols = st.columns(4)
            
            for idx, level in enumerate(proficiency_order):
                count = proficiency_counts.get(level, 0)
                percentage = (count / total_responses * 100) if total_responses > 0 else 0
                
                with metric_cols[idx]:
                    st.metric(
                        label=level,
                        value=f"{percentage:.1f}%",
                        delta=f"{count} responses"
                    )
            
            # Visualization
            st.divider()
            
            # Prepare data for visualization
            viz_data = []
            for level in proficiency_order:
                if level in proficiency_counts.index:
                    viz_data.append({
                        'Proficiency Level': level,
                        'Count': proficiency_counts[level],
                        'Percentage': (proficiency_counts[level] / total_responses * 100)
                    })
            
            viz_df = pd.DataFrame(viz_data)
            
            if len(viz_df) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Count by Proficiency Level")
                    fig_count = px.bar(
                        viz_df,
                        x='Proficiency Level',
                        y='Count',
                        text='Count',
                        color='Proficiency Level',
                        color_discrete_map={
                            'AI Expert': '#1f77b4',
                            'AI Practitioner': '#2ca02c',
                            'AI Experimenter': '#ff7f0e',
                            'AI Novice': '#d62728'
                        }
                    )
                    fig_count.update_traces(textposition='outside')
                    fig_count.update_layout(
                        showlegend=False,
                        xaxis_title="",
                        yaxis_title="Number of Responses",
                        height=400
                    )
                    st.plotly_chart(fig_count, use_container_width=True)
                
                with col2:
                    st.subheader("Percentage Distribution")
                    fig_pie = px.pie(
                        viz_df,
                        values='Percentage',
                        names='Proficiency Level',
                        color='Proficiency Level',
                        color_discrete_map={
                            'AI Expert': '#1f77b4',
                            'AI Practitioner': '#2ca02c',
                            'AI Experimenter': '#ff7f0e',
                            'AI Novice': '#d62728'
                        }
                    )
                    fig_pie.update_traces(
                        textposition='inside',
                        textinfo='percent+label',
                        hovertemplate='<b>%{label}</b><br>%{value:.1f}%<br>%{customdata[0]} responses<extra></extra>',
                        customdata=viz_df[['Count']].values
                    )
                    fig_pie.update_layout(height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                # Detailed table
                st.divider()
                st.subheader("Detailed Breakdown")
                
                detail_df = pd.DataFrame({
                    'Proficiency Level': viz_df['Proficiency Level'],
                    'Count': viz_df['Count'],
                    'Percentage': viz_df['Percentage'].apply(lambda x: f"{x:.1f}%")
                })
                
                st.dataframe(detail_df, hide_index=True, use_container_width=True)
        else:
            st.warning("No proficiency data available for the selected filters.")
    
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
            
            # Apply response filtering
            question_data = filtered_df[selected_question].dropna()
            question_data_filtered = filter_valid_responses(question_data, selected_question)
            
            # Show how many responses were filtered out
            filtered_count = len(question_data) - len(question_data_filtered)
            if filtered_count > 0:
                st.warning(f"⚠️ Filtered out {filtered_count} invalid/contaminated responses")
                
                # DEBUG: Show what was filtered out
                with st.expander("🔍 Debug: View filtered responses", expanded=False):
                    filtered_out = question_data[~question_data.index.isin(question_data_filtered.index)]
                    unique_filtered = filtered_out.unique()
                    
                    st.write("**Responses that were filtered out:**")
                    for resp in unique_filtered[:20]:  # Show first 20
                        st.code(f"'{resp}'")
                    
                    st.write("**Valid responses in whitelist:**")
                    valid_options = get_valid_responses().get(selected_question, [])
                    for opt in valid_options:
                        st.code(f"'{opt}'")
            
            question_data = question_data_filtered
            
            # Determine question type BEFORE normalization (trust the whitelist, not the data)
            question_type_check = get_question_type(selected_question, selected_question)
            
            # Only normalize for single-select (multi-select is normalized during processing)
            if question_type_check != 'multi-select':
                question_data = normalize_for_display(question_data)
            
            # Normalize True/False to Yes/No for display
            question_data = normalize_yes_no_responses(question_data, selected_question)
            
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
    2. **Add Rating Column**: Make sure your Raw Data sheet has a "Rating" column (in row 2) with values like "AI Expert", "AI Practitioner", etc.
    3. **Create Industry Mapping**: Create `client_industry_mapping.xlsx` with columns 'Client' and 'Industry'
    4. **Load Data**: Click "Refresh Data" in the sidebar
    5. **View Proficiency**: Check the Proficiency Overview tab for distribution analysis
    6. **Explore Questions**: Use the Question Explorer tab to analyze individual questions with filters
    7. **View Demographics**: Analyze the demographic breakdown of respondents
    8. **Access Raw Data**: View and download the complete dataset
    9. **Export**: Download filtered data and summary statistics
    
    ### Raw Data Sheet Structure:
    - **Row 1**: (ignored)
    - **Row 2**: Column headers/questions (must include "Rating" column)
    - **Row 3+**: Response data
    
    ### Features:
    - ✅ Proficiency Overview dashboard with metrics and visualizations
    - ✅ Automatically loads all client surveys from one location
    - ✅ Filter by client, industry, and AI proficiency level
    - ✅ Visualize response distributions with charts
    - ✅ Handle single-select, multi-select, and free-response questions
    - ✅ Smart response normalization to group similar variations
    - ✅ Multi-select questions properly split and normalized
    - ✅ Minimal filtering (only removes obvious garbage)
    - ✅ Automatic True/False to Yes/No conversion for display
    - ✅ Export filtered data and summaries
    - ✅ Toggle between Scored Questions and Organizational Readiness questions
    
    ### Setup Instructions:
    
    **For the person managing the data (Taylor):**
    1. Create a folder called `data` in the same location as this app
    2. Add all your client Excel files to that folder (must have "Raw Data" sheet)
    3. Make sure each file has a "Rating" column in row 2 of the Raw Data sheet
    4. Create `client_industry_mapping.xlsx` with two columns: 'Client' and 'Industry'
    5. Click "Refresh Data" to load everything
    
    **For everyone else:**
    - Just use the app! All data is already loaded
    - Filter and analyze without worrying about uploading files
    
    ### Adding New Surveys:
    1. Add new Excel file to the `data` folder (must have "Raw Data" sheet with "Rating" column in row 2)
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
