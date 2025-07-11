import streamlit as st
import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI

# Import local modules
from database import db_manager
from workflow import get_cv_workflow, cv_workflow
from gpt_evaluator import get_gpt_evaluator
from email_service import email_service
from gemini_ocr import gemini_ocr
from utils import (
    setup_directories, save_uploaded_file, get_file_info,
    validate_file_type, format_file_size, generate_session_id,
    format_score, get_pass_status_emoji, format_datetime, get_file_icon
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Streamlit Caching for Services
@st.cache_resource
def get_cached_workflow():
    """Get cached workflow instance"""
    return get_cv_workflow()

@st.cache_resource  
def get_cached_gpt_evaluator():
    """Get cached GPT evaluator instance"""
    return get_gpt_evaluator()

@st.cache_resource
def get_cached_email_service():
    """Get cached email service instance"""
    return email_service

# Page configuration
st.set_page_config(
    page_title="CV Evaluator AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        min-height: 100vh;
    }
    
    /* Header - Simple and Clean */
    .app-header {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        padding: 2.5rem 2rem;
        text-align: center;
        margin: -1rem -1rem 2rem -1rem;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.2);
    }
    
    .app-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        color: white;
    }
    
    .app-header p {
        font-size: 1.1rem;
        margin: 0;
        opacity: 0.95;
        font-weight: 400;
        color: rgba(255, 255, 255, 0.95);
    }
    
    /* Content Area */
    .content-area {
        padding: 2rem;
        background: transparent;
    }
    
    /* Cards - Clean and Modern with better contrast on dark background */
    .card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.2s ease;
        backdrop-filter: blur(10px);
    }
    
    .card:hover {
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        border-color: #3b82f6;
        transform: translateY(-2px);
    }
    
    .card-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #f3f4f6;
    }
    
    .card-header h3 {
        margin: 0;
        color: #1f2937;
        font-weight: 600;
        font-size: 1.2rem;
    }
    
    .card-icon {
        font-size: 1.25rem;
        margin-right: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 8px;
        background: #3b82f6;
        color: white;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(15px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Chat Interface - Improved Readability */
    .chat-container {
        background: rgba(249, 250, 251, 0.95);
        border-radius: 12px;
        padding: 1.5rem;
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }
    
    .chat-message {
        margin: 1rem 0;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        max-width: 85%;
        animation: fadeInUp 0.3s ease;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    .system-message {
        background: #10b981;
        color: white;
        margin-right: auto;
        border-radius: 12px 12px 12px 4px;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
    }
    
    .user-message {
        background: #3b82f6;
        color: white;
        margin-left: auto;
        text-align: right;
        border-radius: 12px 12px 4px 12px;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
    }
    
    .result-message {
        background: #0ea5e9;
        color: white;
        margin-right: auto;
        border-radius: 12px 12px 12px 4px;
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.2);
    }
    
    .error-message {
        background: #ef4444;
        color: white;
        margin-right: auto;
        border-radius: 12px 12px 12px 4px;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);
    }
    
    .summary-message {
        background: #f59e0b;
        color: white;
        margin-right: auto;
        font-weight: 600;
        border-radius: 12px 12px 12px 4px;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
    }
    
    /* Upload Area - Clean Design for dark background */
    .upload-area {
        border: 2px dashed #3b82f6;
        border-radius: 12px;
        padding: 2.5rem 2rem;
        text-align: center;
        background: rgba(240, 249, 255, 0.95);
        margin: 1.5rem 0;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    
    .upload-area:hover {
        border-color: #1d4ed8;
        background: rgba(219, 234, 254, 0.95);
        transform: translateY(-2px);
    }
    
    .upload-area h4 {
        color: #1e40af;
        font-weight: 600;
        margin-bottom: 0.5rem;
        font-size: 1.3rem;
    }
    
    .upload-area p {
        color: #64748b;
        margin: 0;
        font-weight: 400;
    }
    
    /* Buttons - Clean and Professional */
    .stButton button {
        background: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2) !important;
    }
    
    .stButton button:hover {
        background: #1d4ed8 !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Metrics - Clean Design for dark background */
    .metric-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    
    .metric-card:hover {
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
        border-color: #3b82f6;
        transform: translateY(-1px);
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #3b82f6;
        margin-bottom: 0.25rem;
    }
    
    .metric-label {
        color: #6b7280;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.5px;
    }
    
    /* Feature Cards - Better Contrast on Dark Background */
    .feature-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.2s ease;
        height: 100%;
        backdrop-filter: blur(10px);
    }
    
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
        border-color: #3b82f6;
    }
    
    .feature-card .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        display: block;
    }
    
    .feature-card h4 {
        color: #1f2937;
        font-weight: 600;
        margin-bottom: 0.75rem;
        font-size: 1.1rem;
    }
    
    .feature-card p {
        color: #6b7280;
        line-height: 1.6;
        margin: 0;
        font-size: 0.95rem;
    }
    
    
    /* Status Indicators - Clean Design */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 0.25rem;
        gap: 0.5rem;
    }
    
    .status-ready {
        background: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
    }
    
    .status-processing {
        background: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    
    .status-completed {
        background: #dbeafe;
        color: #1e40af;
        border: 1px solid #93c5fd;
    }
    
    .status-error {
        background: #fee2e2;
        color: #dc2626;
        border: 1px solid #fca5a5;
    }
    
    /* File Grid - Improved for dark background */
    .file-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .file-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    
    .file-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
        border-color: #3b82f6;
    }
    
    .file-card .file-icon {
        font-size: 2rem;
        margin-bottom: 0.75rem;
        display: block;
    }
    
    .file-card .file-name {
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
        word-break: break-word;
        font-size: 0.9rem;
    }
    
    .file-card .file-size {
        color: #6b7280;
        font-size: 0.8rem;
    }
    
    /* Welcome Container - Better Typography for Dark Background */
    .welcome-container {
        text-align: center;
        padding: 3rem 2rem;
        max-width: 900px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    .welcome-container h2 {
        color: #1f2937;
        font-weight: 600;
        margin-bottom: 1.5rem;
        font-size: 2rem;
    }
    
    .welcome-container p {
        color: #1f2937;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    
    /* Feature Grid for Welcome Screen */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    /* Sidebar Styling - Dark Theme */
    .sidebar-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid #475569;
        margin-bottom: 1.5rem;
    }
    
    .sidebar-header h2 {
        color: #f1f5f9 !important;
        font-size: 1.5rem !important;
        margin: 0 !important;
    }
    
    .sidebar-header p {
        color: #cbd5e1 !important;
        font-size: 0.9rem !important;
        margin: 0.5rem 0 0 0 !important;
    }
    
    .sidebar-section {
        margin-bottom: 2rem;
    }
    
    .sidebar-section h4 {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
        font-size: 0.95rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Sidebar Text Override */
    .element-container .stMarkdown p {
        color: #cbd5e1 !important;
    }
    
    .element-container .stMarkdown strong {
        color: #f1f5f9 !important;
    }
    
    /* Sidebar Metrics */
    .element-container .metric-value {
        color: #60a5fa !important;
    }
    
    .element-container .metric-label {
        color: #94a3b8 !important;
    }
    
    /* Sidebar Success/Info Messages */
    .sidebar .stSuccess {
        background: rgba(34, 197, 94, 0.1) !important;
        color: #4ade80 !important;
        border: 1px solid rgba(34, 197, 94, 0.2) !important;
    }
    
    .sidebar .stInfo {
        background: rgba(59, 130, 246, 0.1) !important;
        color: #60a5fa !important;
        border: 1px solid rgba(59, 130, 246, 0.2) !important;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main-container {
            margin: 1rem;
        }
        
        .app-header {
            padding: 2rem 1rem;
        }
        
        .app-header h1 {
            font-size: 2rem;
        }
        
        .chat-message {
            max-width: 95%;
        }
        
        .file-grid {
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        }
    }
    
    /* Scrollbar Styling */
    .chat-container::-webkit-scrollbar {
        width: 6px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #5a67d8, #6b4c93);
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stDeployButton {visibility: hidden;}
    
    /* Custom success/error/info messages */
    .stAlert {
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    /* Streamlit Sidebar Dark Theme Override */
    .css-1d391kg, .css-1lcbmhc, .css-1rs6os, .css-17eq0hr {
        background-color: #1e293b !important;
    }
    
    .sidebar .element-container {
        color: #cbd5e1 !important;
    }
    
    .sidebar .stMarkdown h1, .sidebar .stMarkdown h2, .sidebar .stMarkdown h3, .sidebar .stMarkdown h4 {
        color: #f1f5f9 !important;
    }
    
    .sidebar .stMarkdown p {
        color: #cbd5e1 !important;
    }
    
    .sidebar .stButton button {
        background: #3b82f6 !important;
        color: white !important;
        border: 1px solid #3b82f6 !important;
    }
    
    .sidebar .stButton button:hover {
        background: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
    }
    
    /* Sidebar Input Styling */
    .sidebar .stNumberInput input {
        background: #334155 !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
    }
    
    .sidebar .stCheckbox label {
        color: #cbd5e1 !important;
    }
    
    /* Sidebar Expandar */
    .sidebar .stExpander {
        background: #334155 !important;
        border: 1px solid #475569 !important;
    }
    
    /* More specific Streamlit sidebar overrides */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%) !important;
    }
    
    section[data-testid="stSidebar"] .element-container {
        color: #cbd5e1 !important;
    }
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] h4 {
        color: #f1f5f9 !important;
    }
    
    section[data-testid="stSidebar"] p {
        color: #cbd5e1 !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #cbd5e1 !important;
    }
    
    section[data-testid="stSidebar"] .metric-value {
        color: #60a5fa !important;
    }
    
    section[data-testid="stSidebar"] .metric-label {
        color: #94a3b8 !important;
    }
    
    section[data-testid="stSidebar"] .stAlert[data-baseweb="notification"] {
        background: rgba(34, 197, 94, 0.1) !important;
        color: #4ade80 !important;
        border: 1px solid rgba(34, 197, 94, 0.2) !important;
    }
    
    /* Streamlit metric styling in sidebar */
    section[data-testid="stSidebar"] [data-testid="metric-container"] {
        background: rgba(59, 130, 246, 0.1) !important;
        border: 1px solid rgba(59, 130, 246, 0.2) !important;
        color: #f1f5f9 !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="metric-container"] label {
        color: #94a3b8 !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="metric-container"] .metric-value {
        color: #60a5fa !important;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize enhanced session state variables"""
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'session_state' not in st.session_state:
        st.session_state.session_state = None
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'job_description' not in st.session_state:
        st.session_state.job_description = ""
    if 'position_title' not in st.session_state:
        st.session_state.position_title = ""
    if 'required_candidates' not in st.session_state:
        st.session_state.required_candidates = 3

def render_sidebar():
    """Clean and professional sidebar"""
    with st.sidebar:
        # Header
        st.markdown("""
        <div class="sidebar-header">
            <h2 style="margin: 0; color: #2c3e50; font-weight: 700;">🎯 CV Evaluator</h2>
            <p style="margin: 0.5rem 0 0 0; color: #6c757d; font-size: 0.9rem;">AI-Powered Recruitment</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Session Management
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h4>🗂️ Session Management</h4>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ New", help="Create new session", use_container_width=True):
                st.session_state.current_session_id = generate_session_id()
                st.session_state.chat_history = []
                st.session_state.session_state = None
                st.session_state.job_description = ""
                st.session_state.position_title = ""
                st.rerun()
        
        with col2:
            if st.button("🔄 Refresh", help="Refresh session", use_container_width=True):
                if st.session_state.current_session_id:
                    session_state = cv_workflow.get_session_state(st.session_state.current_session_id)
                    if session_state:
                        st.session_state.session_state = session_state
                        st.session_state.chat_history = session_state.get('chat_history', [])
                st.rerun()
        
        # Current session info
        if st.session_state.current_session_id:
            st.success(f"**Active Session:** {st.session_state.current_session_id[:8]}...")
            
            # Session settings
            with st.expander("⚙️ Settings"):
                st.session_state.required_candidates = st.number_input(
                    "Required Candidates", 
                    min_value=1, max_value=20, 
                    value=st.session_state.required_candidates,
                    key="sidebar_required_candidates"
                )
                
                st.session_state.auto_refresh = st.checkbox(
                    "Auto-refresh", 
                    value=st.session_state.auto_refresh,
                    help="Automatically refresh results"
                )
        else:
            st.info("No active session")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Recent Sessions
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h4>📋 Recent Sessions</h4>', unsafe_allow_html=True)
        
        sessions = db_manager.get_all_sessions()
        
        if sessions:
            for session in sessions[:3]:
                with st.expander(f"📅 {format_datetime(session['created_at'])}"):
                    st.write(f"**CVs:** {session['total_cvs']}")
                    st.write(f"**Evaluations:** {session['total_evaluations']}")
                    
                    if st.button(f"Load", key=f"load_{session['session_id']}", use_container_width=True):
                        st.session_state.current_session_id = session['session_id']
                        session_state = cv_workflow.get_session_state(session['session_id'])
                        if session_state:
                            st.session_state.session_state = session_state
                            st.session_state.chat_history = session_state.get('chat_history', [])
                            st.session_state.job_description = session_state.get('job_description', '')
                            st.session_state.position_title = session_state.get('position_title', '')
                        st.rerun()
        else:
            st.info("No recent sessions")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Session Stats
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h4>📊 Current Session</h4>', unsafe_allow_html=True)
        
        if st.session_state.session_state and st.session_state.session_state.get('final_results'):
            results = st.session_state.session_state['final_results']
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("CVs", results.get('total_cvs', 0))
                st.metric("Qualified", results.get('qualified_count', 0))
                
            with col2:
                st.metric("Avg Score", f"{results.get('average_score', 0):.1f}")
                pass_rate = results.get('summary', {}).get('qualification_rate', 0)
                st.metric("Pass Rate", f"{pass_rate:.1f}%")
        else:
            st.info("No evaluation data yet")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_header():
    """Render application header"""
    st.markdown("""
    <div class="app-header">
        <h1>🎯 CV Evaluator AI</h1>
        <p>Interactive AI recruitment assistant • Chat with your evaluations • Real-time insights</p>
    </div>
    """, unsafe_allow_html=True)

def render_chat_interface():
    """Render main chat interface"""
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    
    if not st.session_state.current_session_id:
        render_welcome_screen()
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_chat_messages()
        render_file_upload_area()
    
    with col2:
        render_session_info()
        render_quick_actions()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_welcome_screen():
    """Professional welcome screen"""
    st.markdown("""
    <div class="welcome-container">
        <h2>Welcome to CV Evaluator AI</h2>
        <p style="font-size: 1.1rem; margin-bottom: 3rem; line-height: 1.6;">
            Transform your recruitment process with AI-powered CV evaluation, 
            automated scoring, and intelligent candidate matching.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature cards
    st.markdown('<div class="feature-grid">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">🤖</span>
            <h4>AI-Powered Analysis</h4>
            <p>Advanced OCR with Gemini and real-time evaluation using GPT-3.5-turbo with streaming responses.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">💬</span>
            <h4>Interactive AI Chat</h4>
            <p>Ask questions about specific candidates, get detailed insights, and interact with your evaluation data naturally.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📊</span>
            <h4>Real-time Insights</h4>
            <p>Get instant feedback during evaluation, streaming responses, and comprehensive candidate analysis on demand.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Getting started
    st.markdown("""
    <div class="card" style="margin-top: 2rem; text-align: center;">
        <h3 style="color: #2c3e50; margin-bottom: 1rem;">🚀 Getting Started</h3>
        <p style="color: #6c757d; margin-bottom: 1.5rem;">Ready to revolutionize your recruitment? Follow these simple steps:</p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">1️⃣</div>
                <strong>Create Session</strong><br>
                <small style="color: #6c757d;">Click "➕ New" in the sidebar</small>
            </div>
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">2️⃣</div>
                <strong>Set Requirements</strong><br>
                <small style="color: #6c757d;">Define job description & criteria</small>
            </div>
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">3️⃣</div>
                <strong>Upload CVs</strong><br>
                <small style="color: #6c757d;">Drag & drop candidate files</small>
            </div>
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">4️⃣</div>
                <strong>Chat & Explore</strong><br>
                <small style="color: #6c757d;">Ask questions about candidates</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_chat_messages():
    """Enhanced chat message display with interactive chat"""
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon">💬</div>
            <h3>AI Assistant Conversation</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        
        for message in st.session_state.chat_history:
            msg_type = message.get('type', 'system')
            msg_text = message.get('message', '')
            timestamp = datetime.fromtimestamp(message.get('timestamp', time.time())).strftime("%H:%M:%S")
            
            css_class = f"{msg_type}-message"
            chat_html += f'''
            <div class="chat-message {css_class}">
                <div style="font-size: 0.8rem; opacity: 0.7; margin-bottom: 0.25rem;">{timestamp}</div>
                <div>{msg_text}</div>
            </div>
            '''
        
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #6c757d;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">💭</div>
            <p>No messages yet. Start by uploading some CVs or ask me questions!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Chat input area
    if st.session_state.current_session_id:
        st.markdown("### 💬 Ask AI Assistant")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            user_question = st.text_input(
                "Ask about candidates or CVs...",
                placeholder="e.g., Tell me about candidate John Doe's experience with Python",
                key="chat_input"
            )
        with col2:
            if st.button("Send", type="primary", use_container_width=True):
                if user_question.strip():
                    handle_chat_query(user_question.strip())
                    st.rerun()
        
        # Quick question buttons
        if st.session_state.session_state and st.session_state.session_state.get('final_results'):
            st.markdown("**Quick Questions:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("👥 Top candidates?", use_container_width=True):
                    handle_chat_query("Who are the top 3 candidates and why?")
                    st.rerun()
            
            with col2:
                if st.button("📊 Summary stats?", use_container_width=True):
                    handle_chat_query("Give me a summary of all evaluation results")
                    st.rerun()
            
            with col3:
                if st.button("🔍 Skills analysis?", use_container_width=True):
                    handle_chat_query("Analyze the skills distribution among candidates")
                    st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_file_upload_area():
    """Enhanced file upload interface"""
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon">📁</div>
            <h3>Upload & Process CVs</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Job description input (if not set)
    if not st.session_state.job_description:
        st.markdown("### 📋 Job Requirements")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            job_description = st.text_area(
                "Job Description",
                height=120,
                placeholder="Enter detailed job requirements, skills, experience needed...",
                key="job_desc_input"
            )
            
        with col2:
            position_title = st.text_input(
                "Position Title",
                placeholder="e.g., Python Developer",
                key="position_input"
            )
            
            required_candidates = st.number_input(
                "Required Candidates",
                min_value=1, max_value=20,
                value=3,
                key="candidates_input"
            )
        
        if st.button("💾 Save Job Information", type="primary", use_container_width=True):
            if job_description.strip():
                st.session_state.job_description = job_description
                st.session_state.position_title = position_title or "Position"
                st.session_state.required_candidates = required_candidates
                st.success("✅ Job information saved successfully!")
                st.rerun()
            else:
                st.error("❌ Please enter job description")
    
    # File upload area
    st.markdown('''
    <div class="upload-area">
        <h4>🎯 Drag & Drop CV Files Here</h4>
        <p>Supported formats: PDF, JPG, PNG, GIF, BMP, TIFF • Max size: 200MB per file</p>
    </div>
    ''', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Choose CV files",
        accept_multiple_files=True,
        type=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'],
        key="file_uploader",
        label_visibility="collapsed"
    )
    
    if uploaded_files and st.session_state.job_description:
        # Display uploaded files
        st.markdown("### 📋 Selected Files")
        
        valid_files = []
        total_size = 0
        
        # File grid
        st.markdown('<div class="file-grid">', unsafe_allow_html=True)
        
        cols = st.columns(min(len(uploaded_files), 4))
        
        for i, file in enumerate(uploaded_files):
            col_idx = i % len(cols)
            
            with cols[col_idx]:
                if validate_file_type(file.type):
                    valid_files.append(file)
                    total_size += file.size
                    
                    st.markdown(f'''
                    <div class="file-card">
                        <span class="file-icon">{get_file_icon(file.type)}</span>
                        <div class="file-name">{file.name}</div>
                        <div class="file-size">{format_file_size(file.size)}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.error(f"❌ {file.name} - Unsupported file type")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if valid_files:
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Valid Files", len(valid_files))
            with col2:
                st.metric("Total Size", format_file_size(total_size))
            with col3:
                estimated_time = len(valid_files) * 15
                st.metric("Est. Time", f"{estimated_time}s")
            
            # Process button
            if st.button("🚀 Start AI Evaluation", type="primary", use_container_width=True):
                start_chat_evaluation_with_streaming(valid_files)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_session_info():
    """Enhanced session information panel"""
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon">📊</div>
            <h3>Session Overview</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.session_state:
        session = st.session_state.session_state
        
        # Status badge
        status = session.get('processing_status', 'unknown')
        status_labels = {
            'initialized': '🔄 Initialized',
            'ready': '✅ Ready',
            'processing_files': '⏳ Processing Files',
            'extracting_text': '🔍 Extracting Text',
            'evaluating_cvs': '🤖 AI Evaluation',
            'finalizing_results': '📊 Finalizing',
            'sending_emails': '📧 Sending Emails',
            'completed': '✅ Completed',
            'error': '❌ Error'
        }
        
        status_colors = {
            'initialized': 'status-ready',
            'ready': 'status-ready',
            'processing_files': 'status-processing',
            'extracting_text': 'status-processing',
            'evaluating_cvs': 'status-processing',
            'finalizing_results': 'status-processing',
            'sending_emails': 'status-processing',
            'completed': 'status-completed',
            'error': 'status-error'
        }
        
        status_class = status_colors.get(status, 'status-ready')
        status_label = status_labels.get(status, status.title())
        
        st.markdown(f'''
        <div class="status-badge {status_class}">
            {status_label}
        </div>
        ''', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Session details
        st.markdown(f"**Position:** {session.get('position_title', 'N/A')}")
        st.markdown(f"**Required:** {session.get('required_candidates', 'N/A')} candidates")
        
        # Results metrics
        if 'final_results' in session and session['final_results']:
            results = session['final_results']
            
            st.markdown("### 📈 Results")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{results.get('total_cvs', 0)}</div>
                    <div class="metric-label">Total CVs</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{results.get('qualified_count', 0)}</div>
                    <div class="metric-label">Qualified</div>
                </div>
                """, unsafe_allow_html=True)
            
            avg_score = results.get('average_score', 0)
            qualification_rate = results.get('summary', {}).get('qualification_rate', 0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_score:.1f}</div>
                    <div class="metric-label">Avg Score</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{qualification_rate:.1f}%</div>
                    <div class="metric-label">Pass Rate</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Email status
        email_status = session.get('email_status', {})
        if email_status.get('sent'):
            st.markdown("### 📧 Email Status")
            st.success(f"✅ Rejection emails: {email_status.get('rejection_count', 0)} sent")
            st.info(f"⏰ Interview invites: {email_status.get('interview_count', 0)} scheduled")
    
    else:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #6c757d;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔄</div>
            <p>No active session</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_quick_actions():
    """Enhanced quick actions panel"""
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon">⚡</div>
            <h3>Quick Actions</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.session_state and st.session_state.session_state.get('final_results'):
        results = st.session_state.session_state['final_results']
        
        # Main action buttons
        if st.button("📊 View Detailed Results", use_container_width=True):
            render_detailed_results(results)
        
        if st.button("📋 Ask AI Analysis", use_container_width=True):
            render_ai_report()
        
        st.markdown("### 📧 Email Actions")
        
        qualified_count = results.get('qualified_count', 0)
        rejected_count = results.get('total_cvs', 0) - qualified_count
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"❌ Rejections\n({rejected_count})", use_container_width=True):
                send_rejection_emails_manual()
        
        with col2:
            if st.button(f"✅ Interviews\n({qualified_count})", use_container_width=True):
                schedule_interview_emails_manual()
        
        st.markdown("### 📤 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 JSON", use_container_width=True):
                export_results_json()
        
        with col2:
            if st.button("📊 CSV", use_container_width=True):
                export_summary_csv()
    
    else:
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem; color: #6c757d;">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🎯</div>
            <p style="margin: 0;">Complete evaluation to unlock actions</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def handle_chat_query(question: str):
    """Handle user chat queries about CVs and evaluations"""
    try:
        # Add user message to chat
        st.session_state.chat_history.append({
            "type": "user",
            "message": question,
            "timestamp": time.time()
        })
        
        # Check if we have evaluation data
        if not st.session_state.session_state or not st.session_state.session_state.get('final_results'):
            st.session_state.chat_history.append({
                "type": "system",
                "message": "🤖 I don't have any evaluation data yet. Please upload and evaluate some CVs first!",
                "timestamp": time.time()
            })
            return
        
        # Get current session data
        session_data = st.session_state.session_state
        results = session_data.get('final_results', {})
        job_description = session_data.get('job_description', '')
        
        # Create context for AI
        context = create_chat_context(results, job_description, question)
        
        # Generate AI response
        with st.spinner("🤖 AI is thinking..."):
            response = generate_chat_response(context, question)
        
        # Add AI response to chat
        st.session_state.chat_history.append({
            "type": "result",
            "message": f"🤖 {response}",
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error handling chat query: {e}")
        st.session_state.chat_history.append({
            "type": "error",
            "message": f"❌ Error processing your question: {str(e)}",
            "timestamp": time.time()
        })

def create_chat_context(results: Dict, job_description: str, question: str) -> str:
    """Create context for chat AI response"""
    try:
        all_evaluations = results.get('all_evaluations', [])
        
        # Create summary context
        context = f"""
        JOB DESCRIPTION:
        {job_description}
        
        EVALUATION RESULTS SUMMARY:
        - Total CVs: {results.get('total_cvs', 0)}
        - Qualified candidates: {results.get('qualified_count', 0)}
        - Average score: {results.get('average_score', 0):.1f}/10
        - Pass rate: {results.get('summary', {}).get('qualification_rate', 0):.1f}%
        
        CANDIDATE DETAILS:
        """
        
        # Add candidate information
        for i, candidate in enumerate(all_evaluations[:10], 1):  # Limit to top 10
            filename = candidate.get('filename', f'Candidate {i}')
            score = candidate.get('score', 0)
            qualified = "✅ Qualified" if candidate.get('is_qualified', False) else "❌ Not Qualified"
            
            context += f"\n{i}. {filename} - Score: {score:.1f}/10 - {qualified}"
            
            # Add evaluation details if available
            eval_text = candidate.get('evaluation_text', '')
            if eval_text:
                try:
                    eval_data = json.loads(eval_text)
                    if isinstance(eval_data, dict):
                        summary = eval_data.get('Tổng kết', '')
                        strengths = eval_data.get('Điểm mạnh', [])
                        if summary:
                            context += f"\n   Summary: {summary}"
                        if strengths:
                            context += f"\n   Strengths: {', '.join(strengths[:3])}"
                except:
                    pass
            
            # Add extracted CV text for detailed queries
            extracted_text = candidate.get('extracted_text', '')
            if extracted_text and len(question) > 50:  # For detailed questions
                context += f"\n   CV Content: {extracted_text[:500]}..."
        
        return context
        
    except Exception as e:
        logger.error(f"Error creating chat context: {e}")
        return f"Job Description: {job_description}\nEvaluation data available but error processing details."

def generate_chat_response(context: str, question: str) -> str:
    """Generate AI response for chat queries"""
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return "OpenAI API key not configured. Please check your environment settings."
        
        client = OpenAI(api_key=openai_api_key)
        
        prompt = f"""
        You are an expert recruitment consultant AI assistant. You have access to CV evaluation data and should provide helpful, professional insights about candidates.
        
        CONTEXT:
        {context}
        
        USER QUESTION: {question}
        
        Please provide a helpful, professional response based on the evaluation data. If the question is about specific candidates, use their actual data. Be concise but informative.
        
        Guidelines:
        - Be professional and helpful
        - Use specific data from the evaluations when available
        - If asked about candidates by name, search through the CV content
        - Provide actionable insights for recruitment decisions
        - Keep responses concise but complete
        - Use Vietnamese for candidate names and details if they are in Vietnamese
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional recruitment AI assistant. Provide helpful insights based on CV evaluation data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error generating chat response: {e}")
        return f"I apologize, but I encountered an error while processing your question: {str(e)}"

def start_chat_evaluation_with_streaming(uploaded_files: List):
    """Start evaluation with streaming responses"""
    try:
        setup_directories()
        
        # Save files
        saved_files = []
        for file in uploaded_files:
            file_path = save_uploaded_file(file)
            file_info = get_file_info(file, file_path)
            saved_files.append(file_info)
        
        # Add user message
        st.session_state.chat_history.append({
            "type": "user",
            "message": f"📁 Uploaded {len(saved_files)} CV files for evaluation",
            "timestamp": time.time()
        })
        
        # Process files step by step with streaming
        st.session_state.chat_history.append({
            "type": "system",
            "message": "🚀 Starting AI-powered CV evaluation...",
            "timestamp": time.time()
        })
        
        # Initialize results storage
        evaluation_results = []
        
        for i, file_info in enumerate(saved_files, 1):
            # OCR Step
            st.session_state.chat_history.append({
                "type": "system",
                "message": f"🔍 [{i}/{len(saved_files)}] Extracting text from {file_info['filename']}...",
                "timestamp": time.time()
            })
            
            # Extract text with Gemini
            extracted_text = gemini_ocr.extract_text(file_info["path"])
            
            if extracted_text and not extracted_text.startswith('Error'):
                # GPT Evaluation with streaming
                st.session_state.chat_history.append({
                    "type": "system",
                    "message": f"🤖 [{i}/{len(saved_files)}] AI evaluating {file_info['filename']}...",
                    "timestamp": time.time()
                })
                
                # Stream evaluation
                evaluation_text = stream_cv_evaluation(file_info['filename'], extracted_text)
                
                # Parse evaluation
                try:
                    eval_data = json.loads(evaluation_text)
                    score = eval_data.get("Điểm tổng", 0)
                    is_qualified = eval_data.get("Phù hợp", "không phù hợp") == "phù hợp"
                    
                    result = {
                        "filename": file_info['filename'],
                        "score": score,
                        "is_qualified": is_qualified,
                        "evaluation_text": evaluation_text,
                        "extracted_text": extracted_text
                    }
                    
                    evaluation_results.append(result)
                    
                    # Show individual result
                    status = "✅ Qualified" if is_qualified else "❌ Not Qualified"
                    st.session_state.chat_history.append({
                        "type": "result",
                        "message": f"📊 {file_info['filename']}: {score:.1f}/10 - {status}",
                        "timestamp": time.time()
                    })
                    
                except Exception as e:
                    logger.error(f"Error parsing evaluation: {e}")
                    evaluation_results.append({
                        "filename": file_info['filename'],
                        "score": 0,
                        "is_qualified": False,
                        "evaluation_text": evaluation_text,
                        "extracted_text": extracted_text
                    })
            else:
                st.session_state.chat_history.append({
                    "type": "error",
                    "message": f"❌ Failed to extract text from {file_info['filename']}",
                    "timestamp": time.time()
                })
        
        # Finalize results
        if evaluation_results:
            # Sort by score
            evaluation_results.sort(key=lambda x: x["score"], reverse=True)
            
            # Calculate summary
            total_cvs = len(evaluation_results)
            qualified_count = sum(1 for r in evaluation_results if r["is_qualified"])
            avg_score = sum(r["score"] for r in evaluation_results) / total_cvs
            
            final_results = {
                "total_cvs": total_cvs,
                "qualified_count": qualified_count,
                "average_score": round(avg_score, 2),
                "all_evaluations": evaluation_results,
                "top_candidates": evaluation_results[:st.session_state.required_candidates],
                "summary": {
                    "best_score": evaluation_results[0]["score"] if evaluation_results else 0,
                    "worst_score": evaluation_results[-1]["score"] if evaluation_results else 0,
                    "qualification_rate": round(qualified_count / total_cvs * 100, 1)
                },
                "qualified_candidates": [r for r in evaluation_results if r["is_qualified"]],
                "rejected_candidates": [r for r in evaluation_results if not r["is_qualified"]]
            }
            
            # Update session state
            st.session_state.session_state = {
                "session_id": st.session_state.current_session_id,
                "final_results": final_results,
                "job_description": st.session_state.job_description,
                "position_title": st.session_state.position_title,
                "required_candidates": st.session_state.required_candidates,
                "processing_status": "completed"
            }
            
            # Final summary
            st.session_state.chat_history.append({
                "type": "summary",
                "message": f"✅ Evaluation completed! {qualified_count}/{total_cvs} candidates qualified (Avg: {avg_score:.1f}/10)",
                "timestamp": time.time()
            })
            
            st.success("🎉 AI evaluation completed successfully!")
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error during evaluation: {str(e)}")
        logger.error(f"Error in streaming evaluation: {e}")

def stream_cv_evaluation(filename: str, cv_text: str) -> str:
    """Stream CV evaluation with GPT"""
    try:
        gpt_evaluator = get_cached_gpt_evaluator()
        
        # Use existing evaluation method
        evaluation_result = gpt_evaluator.evaluate_cv(
            st.session_state.job_description,
            cv_text
        )
        
        return evaluation_result
        
    except Exception as e:
        logger.error(f"Error in CV evaluation streaming: {e}")
        return gpt_evaluator._create_fallback_evaluation(str(e))
    """Start evaluation process with chat updates"""
    try:
        setup_directories()
        
        saved_files = []
        for file in uploaded_files:
            file_path = save_uploaded_file(file)
            file_info = get_file_info(file, file_path)
            saved_files.append(file_info)
        
        st.session_state.chat_history.append({
            "type": "user",
            "message": f"📁 Uploaded {len(saved_files)} CV files for evaluation",
            "timestamp": time.time()
        })
        
        cv_workflow_instance = get_cached_workflow()
        
        with st.spinner("🚀 Starting AI evaluation workflow..."):
            result = cv_workflow_instance.run_evaluation(
                st.session_state.current_session_id,
                st.session_state.job_description,
                st.session_state.required_candidates,
                saved_files,
                st.session_state.position_title
            )
        
        if result["success"]:
            st.session_state.session_state = {
                "session_id": result["session_id"],
                "chat_history": result.get("chat_history", []),
                "final_results": result.get("results", {}),
                "processing_status": result.get("status", "completed"),
                "email_status": result.get("email_status", {}),
                "job_description": st.session_state.job_description,
                "position_title": st.session_state.position_title,
                "required_candidates": st.session_state.required_candidates
            }
            
            st.session_state.chat_history.extend(result.get("chat_history", []))
            st.success("✅ Evaluation completed successfully!")
            
        else:
            st.error(f"❌ Evaluation failed: {result.get('error', 'Unknown error')}")
            
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error starting evaluation: {str(e)}")
        logger.error(f"Error starting chat evaluation: {e}")

def render_detailed_results(results: Dict):
    """Render detailed evaluation results"""
    st.subheader("📊 Detailed Evaluation Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total CVs", results.get("total_cvs", 0))
    with col2:
        st.metric("✅ Qualified", results.get("qualified_count", 0))
    with col3:
        st.metric("📊 Average Score", f"{results.get('average_score', 0):.1f}/10")
    with col4:
        qualification_rate = results.get("summary", {}).get("qualification_rate", 0)
        st.metric("📈 Pass Rate", f"{qualification_rate}%")
    
    # Top candidates
    st.subheader("🏆 Top Candidates")
    top_candidates = results.get("top_candidates", [])
    
    for i, candidate in enumerate(top_candidates, 1):
        with st.expander(f"#{i} - {candidate.get('filename', 'Unknown')} {format_score(candidate.get('score', 0))}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write(f"**Score:** {candidate.get('score', 0):.1f}/10")
                status = "✅ Qualified" if candidate.get('is_qualified', False) else "❌ Not Qualified"
                st.write(f"**Status:** {status}")
            
            with col2:
                evaluation_text = candidate.get('evaluation_text', '')
                if evaluation_text:
                    try:
                        eval_data = json.loads(evaluation_text)
                        if isinstance(eval_data, dict):
                            st.write("**Summary:**", eval_data.get('Tổng kết', 'N/A'))
                            
                            strengths = eval_data.get('Điểm mạnh', [])
                            if strengths:
                                st.write("**Strengths:**")
                                for strength in strengths[:3]:
                                    st.write(f"• {strength}")
                        else:
                            st.write(evaluation_text[:200] + "..." if len(evaluation_text) > 200 else evaluation_text)
                    except:
                        st.write(evaluation_text[:200] + "..." if len(evaluation_text) > 200 else evaluation_text)

def render_ai_report():
    """Simple AI chat about results instead of formal report"""
    if not st.session_state.session_state or not st.session_state.session_state.get('final_results'):
        st.error("No evaluation results available")
        return
    
    # Trigger a chat query for comprehensive analysis
    comprehensive_query = "Please provide a comprehensive analysis of all evaluation results including top candidates, overall assessment, and recruitment recommendations."
    handle_chat_query(comprehensive_query)
    st.rerun()

def send_rejection_emails_manual():
    """Manual trigger for rejection emails"""
    if not st.session_state.session_state:
        st.error("No session data available")
        return
    
    results = st.session_state.session_state.get('final_results', {})
    rejected_candidates = results.get('rejected_candidates', [])
    position_title = st.session_state.session_state.get('position_title', 'Position')
    
    if not rejected_candidates:
        st.info("No rejected candidates to send emails to")
        return
    
    try:
        email_svc = get_cached_email_service()
        email_svc.send_rejection_emails(rejected_candidates, position_title)
        st.success(f"📧 Sending rejection emails to {len(rejected_candidates)} candidates")
        
        st.session_state.chat_history.append({
            "type": "system",
            "message": f"📧 Manually triggered rejection emails for {len(rejected_candidates)} candidates",
            "timestamp": time.time()
        })
        
    except Exception as e:
        st.error(f"Error sending rejection emails: {str(e)}")

def schedule_interview_emails_manual():
    """Manual trigger for interview email scheduling"""
    if not st.session_state.session_state:
        st.error("No session data available")
        return
    
    results = st.session_state.session_state.get('final_results', {})
    qualified_candidates = results.get('qualified_candidates', [])
    position_title = st.session_state.session_state.get('position_title', 'Position')
    
    if not qualified_candidates:
        st.info("No qualified candidates to schedule interviews for")
        return
    
    try:
        email_svc = get_cached_email_service()
        email_svc.schedule_interview_emails(qualified_candidates, position_title)
        st.success(f"⏰ Scheduled interview emails for {len(qualified_candidates)} candidates")
        
        st.session_state.chat_history.append({
            "type": "system",
            "message": f"⏰ Manually scheduled interview emails for {len(qualified_candidates)} candidates",
            "timestamp": time.time()
        })
        
    except Exception as e:
        st.error(f"Error scheduling interview emails: {str(e)}")

def export_results_json():
    """Export results as JSON"""
    if not st.session_state.session_state:
        st.error("No data to export")
        return
    
    try:
        data = {
            "session_id": st.session_state.current_session_id,
            "export_timestamp": datetime.now().isoformat(),
            "job_description": st.session_state.session_state.get('job_description', ''),
            "position_title": st.session_state.session_state.get('position_title', ''),
            "results": st.session_state.session_state.get('final_results', {}),
            "chat_history": st.session_state.chat_history
        }
        
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label="💾 Download JSON",
            data=json_str,
            file_name=f"cv_evaluation_{st.session_state.current_session_id[:8]}.json",
            mime="application/json"
        )
        
    except Exception as e:
        st.error(f"Error exporting JSON: {str(e)}")

def export_summary_csv():
    """Export summary as CSV"""
    if not st.session_state.session_state:
        st.error("No data to export")
        return
    
    try:
        results = st.session_state.session_state.get('final_results', {})
        all_evaluations = results.get('all_evaluations', [])
        
        if not all_evaluations:
            st.error("No evaluation data to export")
            return
        
        csv_lines = ["Filename,Score,Qualified,Summary"]
        
        for eval in all_evaluations:
            filename = eval.get('filename', '').replace(',', ';')
            score = eval.get('score', 0)
            qualified = "Yes" if eval.get('is_qualified', False) else "No"
            
            eval_text = eval.get('evaluation_text', '')
            summary = "N/A"
            
            try:
                eval_data = json.loads(eval_text)
                if isinstance(eval_data, dict):
                    summary = eval_data.get('Tổng kết', 'N/A').replace(',', ';')[:100]
            except:
                summary = eval_text[:100].replace(',', ';') if eval_text else "N/A"
            
            csv_lines.append(f"{filename},{score},{qualified},{summary}")
        
        csv_content = "\n".join(csv_lines)
        
        st.download_button(
            label="📊 Download CSV",
            data=csv_content,
            file_name=f"cv_summary_{st.session_state.current_session_id[:8]}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error exporting CSV: {str(e)}")

def main():
    """Enhanced main application function"""
    initialize_session_state()
    setup_directories()
    
    # Auto-refresh logic
    if st.session_state.auto_refresh and st.session_state.current_session_id:
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()
        
        if time.time() - st.session_state.last_refresh > 30:
            cv_workflow_instance = get_cached_workflow()
            session_state = cv_workflow_instance.get_session_state(st.session_state.current_session_id)
            if session_state:
                st.session_state.session_state = session_state
                st.session_state.chat_history = session_state.get('chat_history', [])
            st.session_state.last_refresh = time.time()
            st.rerun()
    
    # Layout
    render_sidebar()
    render_header()
    render_chat_interface()

if __name__ == "__main__":
    main()