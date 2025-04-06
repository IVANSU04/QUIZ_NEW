# Reload timestamp: 2023-09-13 12:00:00  # Updated timestamp to force reload
import streamlit as st
import os
import pandas as pd
from datetime import datetime
import random
import string
import time
import logging
import sys
import requests
import base64
import tempfile
import json
from urllib.parse import urlparse
import sqlite3

# Add debug information
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='/workspaces/QUIZ_NEW/app_debug.log')
logging.debug("Application started")

# Import project modules
from database import Database, get_api_key
from llm import AIService
from utils import (
    generate_class_code,
    generate_student_id,
    format_time,
    validate_input,
)

# Configure page - must be the first Streamlit command
st.set_page_config(
    page_title="Intelligent Education Tool",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import AI feedback components
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))
try:
    # Completely ignore original AI feedback components
    pass
except ImportError:
    pass

# Define alternative rendering function, using a consistent style
def render_ai_feedback(evaluation_result):
    """Render AI feedback with consistent black background and white text style"""
    if not evaluation_result:
        st.info("Evaluation result not available")
        return
    
    score = int(evaluation_result.get('score', 0) * 100)
    feedback = evaluation_result.get('feedback', 'No feedback')
    suggestions = evaluation_result.get('suggestions', [])
    
    # Set color based on score
    if score >= 80:
        score_color = "#4CAF50"  # Green - Excellent
    elif score >= 60:
        score_color = "#FFC107"  # Yellow - Good
    else:
        score_color = "#FF5722"  # Orange-red - Needs Improvement
    
    # Build feedback HTML
    feedback_html = f"""
    <div class="ai-feedback-container">
        <div class="ai-feedback-title">AI Assessment Results</div>
        
        <div class="ai-feedback-score-container">
            <div class="ai-feedback-score" style="color: {score_color};">{score}%</div>
            <div class="ai-feedback-score-label">Overall Score</div>
        </div>
        
        <div class="ai-feedback-section">
            <div class="ai-feedback-header">Detailed Feedback</div>
            <div class="ai-feedback-text">{feedback}</div>
        </div>
        
        <div class="ai-feedback-section">
            <div class="ai-feedback-header">Improvement Suggestions</div>
            <div class="ai-feedback-suggestions-container">
    """
    
    # Add suggestion items - ensure clean suggestion entries
    if suggestions:
        for i, suggestion in enumerate(suggestions):
            # Ensure the suggestion is clean text without unwanted prefixes
            clean_suggestion = suggestion.strip()
            # Remove possible numeric prefixes
            if clean_suggestion.startswith(f"{i+1}") and len(clean_suggestion) > 2:
                if clean_suggestion[1] in ['.', '、', ' ', '：', ':']:
                    clean_suggestion = clean_suggestion[2:].strip()
                
            feedback_html += f'<div class="ai-feedback-suggestion"><span class="suggestion-number">{i+1}</span> {clean_suggestion}</div>'
    else:
        feedback_html += '<div class="ai-feedback-no-suggestions">No specific improvement suggestions</div>'
    
    # Complete HTML
    feedback_html += """
            </div>
        </div>
    </div>
    """
    
    # Render HTML
    st.markdown(feedback_html, unsafe_allow_html=True)

# Add custom CSS - ensure higher style priority
def load_css():
    st.markdown("""
    <style>
    /* Global font settings */
    * {
        font-family: 'Noto Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Source Han Sans CN', 'Noto Sans CJK SC', sans-serif;
        font-weight: bold;
    }
    
    /* Button styles */
    .stButton>button {
        min-height: 40px;
        min-width: 40px;
    }
    
    /* Input box styles */
    .stTextInput>div>div>input {
        min-height: 40px;
    }
    
    /* Error box styles */
    .error-box {
        border: 2px solid red;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        background-color: #ffeeee;
        color: #333333;
    }
    
    /* Word counter styles */
    .word-counter {
        text-align: right;
        font-size: 0.8em;
        color: #888;
    }
    
    /* Score display styles */
    .score-display {
        font-size: 1.2em;
        font-weight: bold;
        color: #333333;
    }
    
    /* Redefine AI feedback styles - enforce black background and white text */
    .ai-feedback-container {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        padding: 25px !important;
        margin: 20px 0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        font-family: 'Noto Sans', sans-serif !important;
        border: none !important;
    }
    
    .ai-feedback-title {
        font-size: 1.5em !important;
        font-weight: bold !important;
        text-align: center !important;
        margin-bottom: 20px !important;
        color: #FFFFFF !important;
        border-bottom: 1px solid #444 !important;
        padding-bottom: 15px !important;
    }
    
    .ai-feedback-score-container {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        margin: 15px 0 25px 0 !important;
        padding: 15px !important;
        border-radius: 8px !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    
    .ai-feedback-score {
        font-size: 3em !important;
        font-weight: bold !important;
        margin: 5px 0 !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
    }
    
    .ai-feedback-score-label {
        font-size: 0.9em !important;
        color: #BBBBBB !important;
    }
    
    .ai-feedback-header {
        font-size: 1.2em !important;
        font-weight: bold !important;
        margin: 20px 0 15px 0 !important;
        padding-bottom: 8px !important;
        border-bottom: 1px solid #444 !important;
        color: #FFFFFF !important;
    }
    
    .ai-feedback-text {
        margin: 15px 0 !important;
        line-height: 1.6 !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 15px !important;
        border-radius: 6px !important;
        color: #EEEEEE !important;
    }
    
    .ai-feedback-section {
        margin-top: 20px !important;
    }
    
    .ai-feedback-suggestions-container {
        padding: 10px 0 !important;
    }
    
    .ai-feedback-suggestion {
        margin: 10px 0 !important;
        padding: 12px 15px 12px 15px !important;
        border-radius: 6px !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        position: relative !important;
        color: #FFFFFF !important;
    }
    
    .suggestion-number {
        display: inline-block !important;
        width: 24px !important;
        height: 24px !important;
        background-color: #4CAF50 !important;
        color: white !important;
        border-radius: 50% !important;
        text-align: center !important;
        line-height: 24px !important;
        font-size: 0.85em !important;
        margin-right: 10px !important;
    }
    
    .ai-feedback-no-suggestions {
        text-align: center !important;
        padding: 15px !important;
        color: #BBBBBB !important;
        font-style: italic !important;
    }
    
    /* Auto-refresh indicator styles */
    .refresh-indicator {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 8px !important;
        background-color: #f0f2f6 !important;
        border-radius: 4px !important;
        margin: 10px 0 !important;
        font-size: 0.9em !important;
        color: #4a4a4a !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        animation: pulse 2s infinite !important;
    }
    
    .refresh-icon {
        margin-right: 8px !important;
        font-size: 1.2em !important;
        display: inline-block !important;
        animation: spin 4s linear infinite !important;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @keyframes pulse {
        0% { background-color: #f0f2f6; }
        50% { background-color: #e1e5ea; }
        100% { background-color: #f0f2f6; }
    }
    </style>
    """, unsafe_allow_html=True)

# Now load CSS, ensuring it's after set_page_config
load_css()

# Initialize database
db = Database()

# Initialize session states
if 'user_type' not in st.session_state:
    # Check if user_type is in query params first
    if "user_type" in st.query_params:
        st.session_state.user_type = st.query_params["user_type"]
    else:
        st.session_state.user_type = None
        
if 'class_code' not in st.session_state:
    # Check if class_code is in query params first
    if "class_code" in st.query_params:
        st.session_state.class_code = st.query_params["class_code"]
    else:
        st.session_state.class_code = None
        
if 'student_id' not in st.session_state:
    # Check if student_id is in query params first
    if "student_id" in st.query_params:
        st.session_state.student_id = st.query_params["student_id"]
    else:
        st.session_state.student_id = None
        
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = -1
if 'timer_active' not in st.session_state:
    st.session_state.timer_active = False
if 'time_remaining' not in st.session_state:
    st.session_state.time_remaining = 0
if 'answer_submitted' not in st.session_state:
    st.session_state.answer_submitted = False
if 'evaluation_result' not in st.session_state:
    st.session_state.evaluation_result = None
if 'connected_students' not in st.session_state:
    st.session_state.connected_students = []
if 'editing_question_index' not in st.session_state:
    st.session_state.editing_question_index = -1
if 'delete_confirm' not in st.session_state:
    st.session_state.delete_confirm = None
if 'video_request_id' not in st.session_state:
    st.session_state.video_request_id = None
if 'video_status' not in st.session_state:
    st.session_state.video_status = None
if 'video_url' not in st.session_state:
    st.session_state.video_url = None
if 'generating_video' not in st.session_state:
    st.session_state.generating_video = False
if 'show_video_form' not in st.session_state:
    st.session_state.show_video_form = False

# D-ID API related functions
def get_basic_auth_header(api_key):
    """Convert API key to Basic Auth format"""
    auth_bytes = api_key.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
    return f"Basic {auth_base64}"

def create_video(image_url, text, voice_id="zh-CN-YunxiNeural"):
    """Create D-ID video task"""
    # D-ID API configuration
    API_KEY = "c3RhcnRiaW5neGlhQGdtYWlsLmNvbQ:z5JIEY1nAbBtjFjSLew34"
    API_URL = "https://api.d-id.com/talks"
    
    # Set authorization header
    headers = {
        "Authorization": get_basic_auth_header(API_KEY),
        "Content-Type": "application/json"
    }

    # Build video task request parameters
    payload = {
        "source_url": image_url,
        "script": {
            "type": "text",
            "input": text,
            "provider": {
                "type": "microsoft",
                "voice_id": voice_id
            }
        }
    }

    try:
        # Send request to create video task
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code != 201:
            logging.error(f"Failed to create video task: {response.text}")
            return None, f"Error ({response.status_code}): {response.text}"
        
        # Return video task ID
        result = response.json()
        return result.get("id"), None
    except Exception as e:
        logging.error(f"Exception while creating video task: {str(e)}")
        return None, str(e)

def get_video_status(video_id):
    """Get D-ID video task status"""
    API_KEY = "c3RhcnRiaW5neGlhQGdtYWlsLmNvbQ:z5JIEY1nAbBtjFjSLew34"
    API_URL = "https://api.d-id.com/talks"
    
    headers = {
        "Authorization": get_basic_auth_header(API_KEY)
    }
    
    try:
        response = requests.get(f"{API_URL}/{video_id}", headers=headers)
        if response.status_code != 200:
            return None, f"Error ({response.status_code}): {response.text}"
        
        return response.json(), None
    except Exception as e:
        return None, str(e)

def is_valid_url(url):
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def find_database_files():
    """Find all database files in the workspace"""
    import glob
    
    # Get all .db files in the current working directory
    db_files = glob.glob("*.db")
    # Get all .db files in the workspace directory
    workspace_db_files = glob.glob("/workspaces/QUIZ_NEW/*.db")
    
    all_db_files = list(set(db_files + workspace_db_files))
    return all_db_files

def teacher_view():
    """Teacher console view"""
    st.title("Teacher Console 👨‍🏫")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Question Creation", "Classroom Management", "Data Export"])
    
    # Question creation tab
    with tab1:
        st.header("Create Discussion Questions")
        # Display number of questions created
        if st.session_state.questions:
            st.success(f"Created {len(st.session_state.questions)} questions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Manual Input")
            question_text = st.text_area("Enter question:", height=150)
            if st.button("Add This Question", key="manual_question"):
                if validate_input(question_text):  # Removed minimum length restriction
                    # Add question to list
                    st.session_state.questions.append(question_text)
                    # If first question, set as current
                    if len(st.session_state.questions) == 1 or st.session_state.current_question is None:
                        st.session_state.current_question = question_text
                        st.session_state.current_question_index = 0
                    st.success("Question added!")
                else:
                    st.error("Question cannot be empty. Please enter content.")
        
        with col2:
            st.subheader("AI-Generated Questions")
            subject = st.selectbox("Subject:", ["Science", "Math", "Literature", "History", "Geography", "Art", "General"])
            difficulty = st.select_slider("Difficulty:", options=["Easy", "Medium", "Hard"])
            keywords = st.text_input("Keywords (separated by commas):")
            
            generate_clicked = st.button("Generate Question", key="generate_question_btn", use_container_width=True)
            
            if generate_clicked:
                with st.spinner("AI is generating a question..."):
                    subject_mapping = {
                        "Science": "science", "Math": "math", "Literature": "literature", 
                        "History": "history", "Geography": "geography", "Art": "art", "General": "general"
                    }
                    difficulty_mapping = {
                        "Easy": "easy", "Medium": "medium", "Hard": "hard"
                    }
                    
                    params = {
                        "subject": subject_mapping.get(subject, "general"),
                        "difficulty": difficulty_mapping.get(difficulty, "medium"),
                        "keywords": [k.strip() for k in keywords.split(",") if k.strip()]
                    }
                    
                    try:
                        generated_question = AIService.generate_question(params)
                        st.session_state.last_generated_question = generated_question
                        st.info(generated_question)
                        
                        # Create a unique key for the add button using a random string
                        add_button_key = f"add_ai_question_{random.randint(10000, 99999)}"
                        
                        if st.button("Add to Question List", key=add_button_key):
                            # Append the question to the list
                            st.session_state.questions.append(generated_question)
                            
                            # If this is the first question or there's no current question, set this as current
                            if len(st.session_state.questions) == 1 or st.session_state.current_question is None:
                                st.session_state.current_question = generated_question
                                st.session_state.current_question_index = len(st.session_state.questions) - 1
                            
                            st.success("Question added to list!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to generate question: {e}")
        
        if st.session_state.questions:
            st.markdown("---")
            st.subheader("Question Management")
            st.info("Manage all your created questions here. You can edit, delete, or reorder these questions. During class, you can browse these questions in the 'Classroom Management' tab.")
            
            question_manager = st.container()
            
            with question_manager:
                for i, question in enumerate(st.session_state.questions):
                    with st.expander(f"Question {i+1}", expanded=(i == st.session_state.current_question_index)):
                        if i == st.session_state.current_question_index:
                            st.markdown("📌 **Current Active Question**")
                        
                        if st.session_state.editing_question_index == i:
                            edited_question = st.text_area(
                                "Edit question:", 
                                value=question, 
                                height=150, 
                                key=f"edit_question_{i}"
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Save Changes", key=f"save_edit_{i}"):
                                    if validate_input(edited_question):
                                        st.session_state.questions[i] = edited_question
                                        if i == st.session_state.current_question_index:
                                            st.session_state.current_question = edited_question
                                            if st.session_state.class_code:
                                                db.update_classroom_question(st.session_state.class_code, edited_question)
                                        st.session_state.editing_question_index = -1
                                        st.success("Question updated!")
                                        st.rerun()
                                    else:
                                        st.error("Question cannot be empty. Please enter content.")
                            with col2:
                                if st.button("Cancel Editing", key=f"cancel_edit_{i}"):
                                    st.session_state.editing_question_index = -1
                                    st.rerun()
                        else:
                            st.markdown(f"**Question Content:**")
                            st.info(question)
                            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                            
                            with col1:
                                if st.button("Edit", key=f"edit_{i}"):
                                    st.session_state.editing_question_index = i
                                    st.rerun()
                            
                            with col2:
                                if st.button("Delete", key=f"delete_{i}"):
                                    if "delete_confirm" not in st.session_state:
                                        st.session_state.delete_confirm = None
                                    st.session_state.delete_confirm = i
                                    st.rerun()
                            
                            with col3:
                                if i > 0:
                                    if st.button("Move Up", key=f"move_up_{i}"):
                                        st.session_state.questions[i], st.session_state.questions[i-1] = st.session_state.questions[i-1], st.session_state.questions[i]
                                        if i == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i-1
                                        elif i-1 == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i
                                        st.rerun()
                            
                            with col4:
                                if i < len(st.session_state.questions) - 1:
                                    if st.button("Move Down", key=f"move_down_{i}"):
                                        st.session_state.questions[i], st.session_state.questions[i+1] = st.session_state.questions[i+1], st.session_state.questions[i]
                                        if i == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i+1
                                        elif i+1 == st.session_state.current_question_index:
                                            st.session_state.current_question_index = i
                                        st.rerun()
                
                if hasattr(st.session_state, 'delete_confirm') and st.session_state.delete_confirm is not None:
                    i = st.session_state.delete_confirm
                    st.warning(f"Are you sure you want to delete Question {i+1}? This action cannot be undone.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Confirm Delete", key=f"confirm_delete_{i}"):
                            deleted_question = st.session_state.questions.pop(i)
                            if i == st.session_state.current_question_index:
                                if st.session_state.questions:
                                    new_index = min(i, len(st.session_state.questions) - 1)
                                    st.session_state.current_question_index = new_index
                                    st.session_state.current_question = st.session_state.questions[new_index]
                                    if st.session_state.class_code:
                                        db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                                else:
                                    st.session_state.current_question_index = -1
                                    st.session_state.current_question = None
                            elif i < st.session_state.current_question_index:
                                st.session_state.current_question_index -= 1
                            st.session_state.delete_confirm = None
                            st.success(f"Question {i+1} deleted")
                            st.rerun()
                    with col2:
                        if st.button("Cancel Delete", key=f"cancel_delete_{i}"):
                            st.session_state.delete_confirm = None
                            st.rerun()
    
    # Classroom Management tab
    with tab2:
        st.header("Classroom Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.class_code:
                st.subheader(f"Current Class Code: {st.session_state.class_code}")
                
                # Question navigation area
                if st.session_state.questions:
                    st.write("### Question Navigation")
                    question_count = len(st.session_state.questions)
                    current_index = st.session_state.current_question_index
                    
                    # Display current question number
                    st.write(f"Current Question: {current_index + 1}/{question_count}")
                    
                    # Fix: Move dropdown to separate line
                    question_options = [f"Question {i+1}" for i in range(question_count)]
                    selected_question = st.selectbox(
                        "Select Question:", 
                        options=question_options, 
                        index=current_index
                    )
                    selected_index = question_options.index(selected_question)
                    if selected_index != current_index:
                        st.session_state.current_question_index = selected_index
                        st.session_state.current_question = st.session_state.questions[selected_index]
                        db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                        st.rerun()
                    
                    # Add previous/next buttons in separate row
                    col_nav1, col_nav2 = st.columns(2)
                    
                    with col_nav1:
                        if current_index > 0:
                            if st.button("← Previous Question", key="prev_question", use_container_width=True):
                                st.session_state.current_question_index -= 1
                                st.session_state.current_question = st.session_state.questions[st.session_state.current_question_index]
                                db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                                st.rerun()
                        else:
                            st.button("← Previous Question", disabled=True, key="prev_question_disabled", use_container_width=True)
                    
                    with col_nav2:
                        if current_index < question_count - 1:
                            if st.button("Next Question →", key="next_question", use_container_width=True):
                                st.session_state.current_question_index += 1
                                st.session_state.current_question = st.session_state.questions[st.session_state.current_question_index]
                                db.update_classroom_question(st.session_state.class_code, st.session_state.current_question)
                                st.rerun()
                        else:
                            st.button("Next Question →", disabled=True, key="next_question_disabled", use_container_width=True)
                
                # Display current question
                if st.session_state.current_question:
                    st.write("**Current Question:**")
                    st.info(st.session_state.current_question)
                    
                    # Add student answers list button
                    if st.button("View Student Answers", key="view_student_answers", type="primary"):
                        # Get all student answers for current question
                        student_answers = db.get_answers_for_question(
                            st.session_state.class_code, 
                            st.session_state.current_question
                        )
                        
                        if student_answers:
                            st.session_state.student_answers = student_answers
                        else:
                            st.session_state.student_answers = []
                        
                        # Set display state
                        if 'show_answers' not in st.session_state:
                            st.session_state.show_answers = True
                        else:
                            st.session_state.show_answers = True
                        
                        st.rerun()
                    
                    # Display student answers list
                    if 'show_answers' in st.session_state and st.session_state.show_answers and 'student_answers' in st.session_state:
                        if st.button("Hide Student Answers", key="hide_student_answers"):
                            st.session_state.show_answers = False
                            st.rerun()
                        
                        st.subheader(f"Student Answers ({len(st.session_state.student_answers)} responses)")
                        
                        if not st.session_state.student_answers:
                            st.info("No students have submitted answers yet")
                        else:
                            # Create a table displaying all answers
                            answer_data = []
                            for idx, answer in enumerate(st.session_state.student_answers):
                                # Format score as percentage
                                score_pct = int(answer['score'] * 100)
                                # Format time
                                submitted_time = answer['submitted_at']
                                if isinstance(submitted_time, str):
                                    try:
                                        submitted_time = datetime.strptime(submitted_time, "%Y-%m-%d %H:%M:%S.%f")
                                    except:
                                        pass
                                # Format time string
                                if isinstance(submitted_time, datetime):
                                    time_str = submitted_time.strftime("%H:%M:%S")
                                else:
                                    time_str = str(submitted_time)
                                
                                # Add to table data
                                answer_data.append({
                                    "No.": idx + 1,
                                    "Student ID": answer['student_id'],
                                    "Time": time_str,
                                    "Score": f"{score_pct}%",
                                    "Preview": answer['answer'][:30] + "..." if len(answer['answer']) > 30 else answer['answer']
                                })
                            
                            # Convert to DataFrame and display
                            answer_df = pd.DataFrame(answer_data)
                            st.dataframe(answer_df, use_container_width=True)
                            
                            # View detailed answer
                            st.subheader("View Detailed Answer")
                            answer_idx = st.selectbox(
                                "Select an answer to view:", 
                                range(len(st.session_state.student_answers)),
                                format_func=lambda i: f"{i+1}. {st.session_state.student_answers[i]['student_id']}"
                            )
                            
                            if answer_idx is not None:
                                selected_answer = st.session_state.student_answers[answer_idx]
                                
                                st.markdown("#### Student Information")
                                st.write(f"**Student ID:** {selected_answer['student_id']}")
                                st.write(f"**Submission Time:** {selected_answer['submitted_at']}")
                                
                                st.markdown("#### Answer Content")
                                st.info(selected_answer['answer'])
                                
                                # Display AI assessment results
                                st.markdown("#### AI Assessment Results")
                                
                                # Build evaluation result object for rendering
                                evaluation_result = {
                                    'score': selected_answer['score'],
                                    'feedback': selected_answer['feedback'],
                                    'suggestions': selected_answer['suggestions']
                                }
                                
                                # Use the same rendering function
                                render_ai_feedback(evaluation_result)
                
                else:
                    st.warning("No discussion question set. Please create questions in the 'Question Creation' tab.")
                
                if st.button("End Class", type="primary"):
                    st.session_state.class_code = None
                    st.session_state.current_question = None
                    st.session_state.timer_active = False  # Keep this line to avoid state errors
                    st.session_state.connected_students = []
                    st.query_params.class_code = ""
            else:
                st.subheader("Create New Class")
                
                if not st.session_state.questions:
                    st.warning("Please create at least one question in the 'Question Creation' tab first.")
                    st.stop()
                
                if st.button("Generate Class Code", type="primary"):
                    new_code = generate_class_code()
                    if db.create_classroom(new_code, "teacher-1", st.session_state.current_question):
                        st.session_state.class_code = new_code
                        st.success(f"Class created successfully! Class code: {new_code}")
                        st.query_params.class_code = new_code
                    else:
                        st.error("Failed to create class, please try again.")
        
        with col2:
            st.subheader("Connected Students")
            if st.session_state.class_code:
                if st.button("Refresh Student List", type="primary", use_container_width=True):
                    st.session_state.connected_students = db.get_classroom_students(st.session_state.class_code)
                    st.success("Student list updated")
                
                student_container = st.empty()
                
                with student_container.container():
                    st.session_state.connected_students = db.get_classroom_students(st.session_state.class_code)
                    st.write(f"Connected students: {len(st.session_state.connected_students)}")
                    if st.session_state.connected_students:
                        st.markdown('<div class="student-list">', unsafe_allow_html=True)
                        for i, student in enumerate(st.session_state.connected_students):
                            st.write(f"{i+1}. {student['id']} (Joined at: {student['joined_at']})")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("No students connected")
            else:
                st.info("Connected students will be displayed here after class creation")
    
    with tab3:
        st.header("Data Export")
        
        if st.session_state.class_code:
            st.write(f"Current Class: {st.session_state.class_code}")
            try:
                df = db.get_classroom_data(st.session_state.class_code)
                if not df.empty:
                    st.write("Class data preview:")
                    st.dataframe(df.head())
                    
                    export_format = st.selectbox("Export Format:", ["CSV", "Excel"])
                    if st.button("Export Data", type="primary"):
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = f"classroom_{st.session_state.class_code}_{timestamp}"
                        
                        if export_format == "CSV":
                            file_path = f"{filename}.csv"
                            df.to_csv(file_path, index=False)
                        else:
                            file_path = f"{filename}.xlsx"
                            df.to_excel(file_path, index=False)
                        
                        with open(file_path, "rb") as file:
                            st.download_button(
                                label="Download File",
                                data=file,
                                file_name=os.path.basename(file_path),
                                mime="application/octet-stream"
                            )
                else:
                    st.info("No data available for export")
            except Exception as e:
                st.error(f"Failed to retrieve data: {e}")
        else:
            st.info("Please create or join a class first")
        
        # Add new section for database download
        st.markdown("---")
        st.subheader("Database File Download")
        
        db_col1, db_col2 = st.columns([1, 2])
        
        with db_col1:
            if os.path.exists(db.db_path):
                with open(db.db_path, "rb") as file:
                    st.download_button(
                        label="Download Database File",
                        data=file,
                        file_name="education_tool.db",
                        mime="application/octet-stream",
                        help="Download the complete database file to your local computer"
                    )
            else:
                st.error("Database file does not exist")
        
        with db_col2:
            st.info("""
            **Note**: This function allows you to download the complete database file.
            
            The database contains all classroom, student, and answer data. You can use SQLite tools (such as DB Browser for SQLite) to open this file for advanced data analysis.
            
            **Important**: The downloaded database file only contains data from the current session. A new database is created each time the application restarts.
            """)
        
        # Existing database files viewer
        with st.expander("View System Database Files"):
            db_files = find_database_files()
            if db_files:
                st.write("Database files in the system:")
                for db_file in db_files:
                    st.code(db_file)
                    
                    try:
                        import sqlite3
                        conn = sqlite3.connect(db_file)
                        cursor = conn.cursor()
                        
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        st.write(f"Tables in database: {', '.join([t[0] for t in tables])}")
                        
                        conn.close()
                    except Exception as e:
                        st.error(f"Unable to read database information: {e}")
            else:
                st.info("No database files found")

def student_view():
    """Student terminal view"""
    st.title("Student Terminal 👨‍🎓")
    if not st.session_state.class_code:
        st.header("Join Class")
        
        col1, col2 = st.columns(2)
        
        with col1:
            class_code = st.text_input("Enter class code:", max_chars=4).upper()
            
            if st.button("Join", type="primary"):
                if len(class_code) == 4:
                    # Show database connection status for debugging
                    st.info(f"Connecting to database at: {db.db_path}")
                    
                    # Validate class code exists
                    conn = sqlite3.connect(db.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM classrooms WHERE class_code = ?", (class_code,))
                    count = cursor.fetchone()[0]
                    conn.close()
                    
                    if count == 0:
                        st.error(f"Class code '{class_code}' does not exist in the database. Please check the code.")
                        return
                    
                    # Create student ID and add to class    
                    student_id = generate_student_id()
                    if db.add_student(student_id, class_code):
                        st.session_state.class_code = class_code
                        st.session_state.student_id = student_id
                        st.query_params.class_code = class_code
                        st.query_params.student_id = student_id
                        st.success(f"Successfully joined class: {class_code}")
                        st.rerun()
                    else:
                        st.error(f"Failed to join: Class code '{class_code}' does not exist or is closed. Please check the class code.")
                else:
                    st.error("Class code must be 4 characters")
        
        with col2:
            st.info("Tip: Ask your teacher for the class code")
    else:
        st.header(f"Joined Class: {st.session_state.class_code}")
        st.subheader(f"Your ID: {st.session_state.student_id}")
        
        if st.button("Refresh Question", type="primary", help="Click to get the latest question from the teacher"):
            classroom_info = db.get_classroom_info(st.session_state.class_code)
            if classroom_info and classroom_info.get('question'):
                current_question = classroom_info.get('question')
                if current_question != st.session_state.current_question:
                    st.session_state.current_question = current_question
                    st.success("Got a new question!")
                else:
                    st.info("Question hasn't changed")
            elif not st.session_state.current_question:
                st.session_state.current_question = "Teacher hasn't posted a discussion question yet. Please wait."
            st.rerun()
        
        classroom_info = db.get_classroom_info(st.session_state.class_code)
        if classroom_info and classroom_info.get('question'):
            current_question = classroom_info.get('question')
            if current_question != st.session_state.current_question:
                st.session_state.current_question = current_question
                logging.debug(f"Retrieved new question from database: {st.session_state.current_question}")
        elif not st.session_state.current_question:
            st.session_state.current_question = "Teacher hasn't posted a discussion question yet. Please wait."
        
        st.markdown("### 📝 Discussion Question:")
        st.info(st.session_state.current_question)
        
        if not st.session_state.answer_submitted:
            st.subheader("Your Answer:")
            answer_text = st.text_area("Enter your answer (Markdown supported):", height=200, key="answer_input")
            
            st.markdown(f'<div class="word-counter">{len(answer_text)} characters</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Submit Answer", type="primary"):
                    if answer_text.strip() == "":
                        st.error("Answer cannot be empty. Please provide a valid response.")
                    else:
                        with st.spinner("Evaluating your answer..."):
                            try:
                                eval_result = AIService.evaluate_answer(
                                    st.session_state.current_question, 
                                    answer_text
                                )
                                db.save_answer(
                                    st.session_state.student_id,
                                    st.session_state.class_code,
                                    st.session_state.current_question,
                                    answer_text,
                                    eval_result
                                )
                                st.session_state.answer_submitted = True
                                st.session_state.evaluation_result = eval_result
                                st.rerun()
                            except Exception as e:
                                st.error(f"Evaluation failed: {e}")
            with col2:
                st.info("Tip: You'll receive AI feedback after submission and won't be able to modify your answer.")
        
        else:
            st.subheader("Your answer has been submitted")
            
            # Add AI video button
            video_col1, video_col2 = st.columns([1, 3])
            with video_col1:
                if not st.session_state.generating_video and not st.session_state.video_url:
                    if st.button("Generate AI Video Explanation", type="primary"):
                        st.session_state.show_video_form = True
                        st.rerun()
            
            with video_col2:
                if not st.session_state.generating_video and not st.session_state.video_url:
                    st.info("Click the button to generate a video explanation based on AI feedback")
            
            # Display video generation form
            if st.session_state.show_video_form and not st.session_state.video_url:
                # Add a back button at the top of the form
                if st.button("← Back to Answer Page", key="back_to_answer"):
                    st.session_state.show_video_form = False
                    st.rerun()
                
                with st.form("video_generation_form"):
                    st.subheader("Set AI Video Parameters")
                    
                    # Default image URL
                    default_image_url = "https://i.imgur.com/JcMQ8Gh.jpeg"
                    
                    # Simplify image selection
                    st.write("### Select Character Image")
                    
                    # Option 1: Direct URL input
                    image_url = st.text_input(
                        "Image URL (enter web image link):", 
                        value=default_image_url,
                        help="Enter a valid image URL, e.g., https://example.com/image.jpg"
                    )
                    
                    # URL validity tip
                    if image_url and image_url != default_image_url:
                        if is_valid_url(image_url):
                            st.success("URL format is valid")
                        else:
                            st.error("Please enter a valid image URL format")
                    
                    # Option 2: Or upload local image
                    st.write("---")
                    st.write("**Or** upload a local image:")
                    uploaded_file = st.file_uploader(
                        "Select a JPG or PNG image", 
                        type=["jpg", "jpeg", "png"]
                    )
                    
                    # Show image preview
                    st.write("### Image Preview")
                    preview_col1, preview_col2 = st.columns([1, 2])
                    
                    with preview_col1:
                        if uploaded_file is not None:
                            # Display uploaded image preview
                            st.image(uploaded_file, width=150)
                            st.info("You've uploaded a local image, it will be used after submission")
                        elif image_url:
                            # Display URL image preview
                            try:
                                st.image(image_url, width=150)
                                if image_url == default_image_url:
                                    st.info("Using default image")
                                else:
                                    st.info("Using custom URL image")
                            except Exception:
                                st.error("Unable to load image, please check if the URL is valid")
                    
                    # Upload limitations explanation
                    with preview_col2:
                        if uploaded_file is not None:
                            # Validate file type
                            if uploaded_file.type not in ["image/jpeg", "image/jpg", "image/png"]:
                                st.error("Please upload a valid JPG or PNG image")
                            
                            # Inform user about conversion requirement
                            st.warning("""
                            ### Important Note
                            Due to technical limitations, uploaded local images are only for preview.
                            The video will still use the URL entered above or default image.
                            
                            To use your own image:
                            1. First upload your image to an image hosting site (like imgur.com)
                            2. Copy the image link and paste it in the URL input box above
                            """)
                    
                    st.write("---")
                    
                    # Voice options
                    voice_option = st.radio(
                        "Select Voice:",
                        ["Male", "Female"],
                        horizontal=True
                    )
                    
                    voice_id = "zh-CN-YunxiNeural" if voice_option == "Male" else "zh-CN-XiaoxiaoNeural"
                    
                    # Text content
                    feedback_text = st.session_state.evaluation_result.get('feedback', '')
                    suggestions = st.session_state.evaluation_result.get('suggestions', [])
                    suggestions_text = "\n".join([f"{i+1}. {suggestion}" for i, suggestion in enumerate(suggestions)])
                    
                    default_script = f"Here's an evaluation of your answer:\n{feedback_text}\n\nImprovement suggestions:\n{suggestions_text}"
                    
                    video_script = st.text_area(
                        "Video Explanation Content:",
                        value=default_script,
                        height=150
                    )
                    
                    submitted = st.form_submit_button("Start Generating Video")
                    cancelled = st.form_submit_button("Cancel", type="secondary")
                    
                    if submitted:
                        # Confirm URL is valid
                        if not is_valid_url(image_url):
                            st.error("Please provide a valid image URL format")
                            st.stop()
                        
                        with st.spinner("Creating video task..."):
                            # Start generating video
                            video_id, error = create_video(image_url, video_script, voice_id)
                            
                            if video_id:
                                st.session_state.video_request_id = video_id
                                st.session_state.generating_video = True
                                st.session_state.video_status = "processing"
                                st.success(f"Video task created, ID: {video_id}")
                                st.rerun()
                            else:
                                st.error(f"Failed to create video task: {error}")
                    
                    if cancelled:
                        st.session_state.show_video_form = False
                        st.rerun()
            
            # ...existing code for checking video generation status and displaying the video...
            
            if st.session_state.evaluation_result:
                render_ai_feedback(st.session_state.evaluation_result)
            else:
                st.info("Evaluation result not available")
            
            if st.button("Leave Class"):
                st.session_state.class_code = None
                st.session_state.student_id = None
                st.session_state.current_question = None
                st.session_state.answer_submitted = False
                st.session_state.evaluation_result = None
                st.query_params.clear()
                st.rerun()

def main():
    """Main application function"""
    logging.debug("Entering main() function")
    
    with st.sidebar:
        st.title("Intelligent Education Tool")
        st.write("AI-powered classroom discussion assistant")
        
        if not st.session_state.user_type:
            st.header("Select User Type")
            
            st.write("### Please select your role:")
            
            if st.button("👨‍🏫 Teacher", key="teacher_btn", use_container_width=True):
                st.session_state.user_type = "teacher"
                st.query_params.user_type = "teacher"
            
            st.write("") 
            
            if st.button("👨‍🎓 Student", key="student_btn", use_container_width=True):
                st.session_state.user_type = "student"
                st.query_params.user_type = "student"
                
            st.write("---")
            st.info("If you don't see the buttons, please refresh the page or clear your browser cache")
        
        if st.session_state.user_type:
            # Only show when student ID exists
            if st.session_state.student_id:
                st.write(f"Student ID: {st.session_state.student_id}")
            
            if st.button("Switch User Type"):
                st.session_state.user_type = None
                st.session_state.class_code = None
                st.session_state.student_id = None
                st.session_state.current_question = None
                st.session_state.answer_submitted = False
                st.session_state.evaluation_result = None
                st.query_params.clear()
        
        st.markdown("---")
        st.write("📚 Intelligent Education Tool v1.0")
        st.write("⚙️ Powered by Python + Streamlit + AI")
        st.write("© 2025 Education Tech")
    
    logging.debug("Checking if AI API is available...")
    api_available = AIService.is_api_available()
    logging.debug(f"AI API availability check result: {api_available}")
    if not api_available:
        st.error("⚠️ AI service unavailable. Please check:\n"
                 "1. Ensure your network connection is working.\n"
                 "2. Check if your API key is correct.\n"
                 "3. Ensure the AI service endpoint is accessible.")
    else:
        st.success("✅ AI service connected successfully")
        if st.session_state.user_type == "teacher":
            teacher_view()
        elif st.session_state.user_type == "student":
            student_view()
        else:
            st.title("Welcome to Intelligent Education Tool")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Teacher Features")
                st.write("✅ Question creation and management")
                st.write("✅ Real-time classroom monitoring")
                st.write("✅ Student response data analysis")
                st.write("✅ AI-assisted teaching assessment")
            
            with col2:
                st.subheader("Student Features")
                st.write("✅ Simple classroom connection")
                st.write("✅ Markdown-formatted answers")
                st.write("✅ Real-time AI feedback")
                st.write("✅ Personalized learning suggestions")
        
        st.info("Please select your user type in the sidebar")

if __name__ == "__main__":
    main()