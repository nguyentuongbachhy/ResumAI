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
    /* Import Professional Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* CSS Variables for Consistent Color Scheme */
    :root {
        /* Primary Colors */
        --primary-blue: #2563eb;
        --primary-blue-dark: #1d4ed8;
        --primary-blue-light: #3b82f6;
        
        /* Secondary Colors */
        --secondary-indigo: #4f46e5;
        --secondary-purple: #7c3aed;
        --secondary-teal: #0d9488;
        
        /* Neutral Colors */
        --gray-50: #f9fafb;
        --gray-100: #f3f4f6;
        --gray-200: #e5e7eb;
        --gray-300: #d1d5db;
        --gray-400: #9ca3af;
        --gray-500: #6b7280;
        --gray-600: #4b5563;
        --gray-700: #374151;
        --gray-800: #1f2937;
        --gray-900: #111827;
        
        /* Status Colors */
        --success: #10b981;
        --success-light: #34d399;
        --warning: #f59e0b;
        --warning-light: #fbbf24;
        --error: #ef4444;
        --error-light: #f87171;
        --info: #06b6d4;
        --info-light: #22d3ee;
        
        /* Background Colors */
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --bg-tertiary: #f1f5f9;
        --bg-dark: #0f172a;
        --bg-dark-secondary: #1e293b;
        --bg-dark-tertiary: #334155;
        
        /* Text Colors */
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --text-tertiary: #64748b;
        --text-light: #94a3b8;
        --text-white: #ffffff;
        
        /* Shadows */
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        
        /* Border Radius */
        --radius-sm: 6px;
        --radius-md: 8px;
        --radius-lg: 12px;
        --radius-xl: 16px;
        --radius-2xl: 24px;
    }
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: var(--text-primary);
        line-height: 1.6;
    }
    
    /* Remove default Streamlit styles */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Header - Modern & Professional */
    .app-header {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        color: var(--text-white);
        padding: 3rem 2rem;
        text-align: center;
        margin: -1rem -1rem 2rem -1rem;
        box-shadow: var(--shadow-xl);
        position: relative;
        overflow: hidden;
    }
    
    .app-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
        opacity: 0.1;
    }
    
    .app-header h1 {
        font-size: 3rem;
        font-weight: 800;
        margin: 0 0 1rem 0;
        color: var(--text-white);
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        position: relative;
        z-index: 1;
    }
    
    .app-header p {
        font-size: 1.2rem;
        margin: 0;
        opacity: 0.95;
        font-weight: 400;
        color: rgba(255, 255, 255, 0.9);
        position: relative;
        z-index: 1;
    }
    
    /* Content Area */
    .content-area {
        padding: 2rem;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    /* Cards - Premium Design */
    .card {
        background: var(--bg-primary);
        border-radius: var(--radius-xl);
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--gray-200);
        padding: 2rem;
        margin-bottom: 2rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .card:hover {
        box-shadow: var(--shadow-xl);
        border-color: var(--primary-blue-light);
        transform: translateY(-4px);
    }
    
    .card:hover::before {
        opacity: 1;
    }
    
    .card-header {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid var(--gray-100);
    }
    
    .card-header h3 {
        margin: 0;
        color: var(--text-primary);
        font-weight: 700;
        font-size: 1.4rem;
        letter-spacing: -0.025em;
    }
    
    .card-icon {
        font-size: 1.5rem;
        margin-right: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: var(--radius-lg);
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        color: var(--text-white);
        box-shadow: var(--shadow-md);
        position: relative;
    }
    
    .card-icon::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: inherit;
        padding: 2px;
        background: linear-gradient(135deg, var(--primary-blue-light), var(--secondary-purple));
        mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        mask-composite: exclude;
    }
    
    /* Chat Interface - Enhanced Readability */
    .chat-container {
        background: var(--bg-secondary);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        max-height: 600px;
        overflow-y: auto;
        border: 1px solid var(--gray-200);
        margin: 1rem 0;
        scrollbar-width: thin;
        scrollbar-color: var(--primary-blue-light) var(--gray-200);
    }
    
    .chat-container::-webkit-scrollbar {
        width: 8px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: var(--gray-100);
        border-radius: var(--radius-md);
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        border-radius: var(--radius-md);
    }
    
    .chat-message {
        margin: 1.5rem 0;
        padding: 1.25rem 1.5rem;
        border-radius: var(--radius-lg);
        max-width: 85%;
        animation: slideInUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 0.95rem;
        line-height: 1.6;
        font-weight: 500;
        box-shadow: var(--shadow-md);
        position: relative;
    }
    
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .system-message {
        background: linear-gradient(135deg, var(--success) 0%, var(--secondary-teal) 100%);
        color: var(--text-white);
        margin-right: auto;
        border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) 6px;
    }
    
    .user-message {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        color: var(--text-white);
        margin-left: auto;
        text-align: right;
        border-radius: var(--radius-lg) var(--radius-lg) 6px var(--radius-lg);
    }
    
    .result-message {
        background: linear-gradient(135deg, var(--info) 0%, var(--primary-blue-light) 100%);
        color: var(--text-white);
        margin-right: auto;
        border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) 6px;
    }
    
    .error-message {
        background: linear-gradient(135deg, var(--error) 0%, #dc2626 100%);
        color: var(--text-white);
        margin-right: auto;
        border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) 6px;
    }
    
    .summary-message {
        background: linear-gradient(135deg, var(--warning) 0%, var(--warning-light) 100%);
        color: var(--text-white);
        margin-right: auto;
        font-weight: 600;
        border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) 6px;
    }
    
    /* Upload Area - Professional Design */
    .upload-area {
        border: 3px dashed var(--primary-blue-light);
        border-radius: var(--radius-xl);
        padding: 3rem 2rem;
        text-align: center;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(79, 70, 229, 0.05) 100%);
        margin: 2rem 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .upload-area::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 50%);
        transform: translate(-50%, -50%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .upload-area:hover {
        border-color: var(--primary-blue);
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(79, 70, 229, 0.08) 100%);
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }
    
    .upload-area:hover::before {
        opacity: 1;
    }
    
    .upload-area h4 {
        color: var(--primary-blue);
        font-weight: 700;
        margin-bottom: 0.75rem;
        font-size: 1.5rem;
        position: relative;
        z-index: 1;
    }
    
    .upload-area p {
        color: var(--text-secondary);
        margin: 0;
        font-weight: 500;
        font-size: 1.1rem;
        position: relative;
        z-index: 1;
    }
    
    /* Buttons - Enhanced Design */
    .stButton button {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%) !important;
        color: var(--text-white) !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: var(--shadow-md) !important;
        position: relative !important;
        overflow: hidden !important;
        text-transform: uppercase !important;
        letter-spacing: 0.025em !important;
    }
    
    .stButton button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s ease;
    }
    
    .stButton button:hover {
        background: linear-gradient(135deg, var(--primary-blue-dark) 0%, var(--secondary-purple) 100%) !important;
        box-shadow: var(--shadow-xl) !important;
        transform: translateY(-2px) !important;
    }
    
    .stButton button:hover::before {
        left: 100%;
    }
    
    /* Metrics - Professional Design */
    .metric-card {
        background: var(--bg-primary);
        border-radius: var(--radius-lg);
        padding: 2rem;
        text-align: center;
        border: 1px solid var(--gray-200);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow-md);
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
    }
    
    .metric-card:hover {
        box-shadow: var(--shadow-xl);
        border-color: var(--primary-blue-light);
        transform: translateY(-4px);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--primary-blue);
        margin-bottom: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-label {
        color: var(--text-secondary);
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.1em;
    }
    
    /* Feature Cards - Enhanced Design */
    .feature-card {
        background: var(--bg-primary);
        border-radius: var(--radius-xl);
        padding: 2.5rem;
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--gray-200);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .feature-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: conic-gradient(from 0deg, transparent, rgba(59, 130, 246, 0.1), transparent);
        opacity: 0;
        transition: opacity 0.3s ease;
        animation: rotate 10s linear infinite;
    }
    
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: var(--shadow-xl);
        border-color: var(--primary-blue-light);
    }
    
    .feature-card:hover::before {
        opacity: 1;
    }
    
    .feature-card .feature-icon {
        font-size: 3rem;
        margin-bottom: 1.5rem;
        display: block;
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        position: relative;
        z-index: 1;
    }
    
    .feature-card h4 {
        color: var(--text-primary);
        font-weight: 700;
        margin-bottom: 1rem;
        font-size: 1.3rem;
        position: relative;
        z-index: 1;
    }
    
    .feature-card p {
        color: var(--text-secondary);
        line-height: 1.7;
        margin: 0;
        font-size: 1rem;
        font-weight: 500;
        position: relative;
        z-index: 1;
    }
    
    /* Status Indicators - Modern Design */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.75rem 1.25rem;
        border-radius: var(--radius-2xl);
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0.25rem;
        gap: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.025em;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }
    
    .status-ready {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%);
        color: var(--success);
        border: 2px solid rgba(16, 185, 129, 0.2);
    }
    
    .status-processing {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(251, 191, 36, 0.1) 100%);
        color: var(--warning);
        border: 2px solid rgba(245, 158, 11, 0.2);
    }
    
    .status-completed {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(99, 102, 241, 0.1) 100%);
        color: var(--primary-blue);
        border: 2px solid rgba(59, 130, 246, 0.2);
    }
    
    .status-error {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%);
        color: var(--error);
        border: 2px solid rgba(239, 68, 68, 0.2);
    }
    
    /* File Grid - Professional Layout */
    .file-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .file-card {
        background: var(--bg-primary);
        padding: 2rem;
        border-radius: var(--radius-lg);
        border: 1px solid var(--gray-200);
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow-md);
        position: relative;
        overflow: hidden;
    }
    
    .file-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--info) 0%, var(--primary-blue) 100%);
        transform: scaleX(0);
        transition: transform 0.3s ease;
        transform-origin: left;
    }
    
    .file-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-xl);
        border-color: var(--primary-blue-light);
    }
    
    .file-card:hover::before {
        transform: scaleX(1);
    }
    
    .file-card .file-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        display: block;
        background: linear-gradient(135deg, var(--info) 0%, var(--primary-blue) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .file-card .file-name {
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.75rem;
        word-break: break-word;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    
    .file-card .file-size {
        color: var(--text-tertiary);
        font-size: 0.85rem;
        font-weight: 500;
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Welcome Container - Premium Design */
    .welcome-container {
        text-align: center;
        padding: 4rem 3rem;
        max-width: 1000px;
        margin: 0 auto;
        background: var(--bg-primary);
        border-radius: var(--radius-2xl);
        box-shadow: var(--shadow-xl);
        border: 1px solid var(--gray-200);
        position: relative;
        overflow: hidden;
    }
    
    .welcome-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 6px;
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--secondary-indigo) 50%, var(--secondary-purple) 100%);
    }
    
    .welcome-container h2 {
        color: var(--text-primary);
        font-weight: 800;
        margin-bottom: 2rem;
        font-size: 2.5rem;
        background: linear-gradient(135deg, var(--text-primary) 0%, var(--primary-blue) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .welcome-container p {
        color: var(--text-secondary);
        font-size: 1.2rem;
        line-height: 1.7;
        font-weight: 500;
    }
    
    /* Feature Grid */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        margin: 3rem 0;
    }
    
    /* Sidebar Styling - Professional Dark Theme */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-dark) 0%, var(--bg-dark-secondary) 100%) !important;
        border-right: 3px solid var(--primary-blue) !important;
    }
    
    .sidebar-header {
        text-align: center;
        padding: 1.5rem 0;
        border-bottom: 2px solid var(--bg-dark-tertiary);
        margin-bottom: 2rem;
        position: relative;
    }
    
    .sidebar-header::before {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        border-radius: var(--radius-sm);
    }
    
    .sidebar-header h2 {
        color: var(--text-white) !important;
        font-size: 1.6rem !important;
        margin: 0 !important;
        font-weight: 800 !important;
    }
    
    .sidebar-header p {
        color: #cbd5e1 !important;
        font-size: 0.95rem !important;
        margin: 0.75rem 0 0 0 !important;
        font-weight: 500 !important;
    }
    
    .sidebar-section {
        margin-bottom: 2.5rem;
    }
    
    .sidebar-section h4 {
        color: var(--text-white) !important;
        font-weight: 700 !important;
        margin-bottom: 1.25rem !important;
        font-size: 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        position: relative !important;
        padding-left: 1rem !important;
    }
    
    .sidebar-section h4::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%);
        border-radius: var(--radius-sm);
    }
    
    /* Sidebar Text Overrides */
    section[data-testid="stSidebar"] .element-container {
        color: #cbd5e1 !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown p {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown strong {
        color: var(--text-white) !important;
        font-weight: 700 !important;
    }
    
    /* Sidebar Metrics Enhancement */
    section[data-testid="stSidebar"] [data-testid="metric-container"] {
        background: rgba(59, 130, 246, 0.1) !important;
        border: 2px solid rgba(59, 130, 246, 0.2) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="metric-container"] label {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.1em !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="metric-container"] .metric-value {
        color: var(--info-light) !important;
        font-weight: 800 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Sidebar Button Styling */
    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-indigo) 100%) !important;
        color: var(--text-white) !important;
        border: 2px solid transparent !important;
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.025em !important;
        transition: all 0.3s ease !important;
    }
    
    section[data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(135deg, var(--primary-blue-dark) 0%, var(--secondary-purple) 100%) !important;
        border-color: var(--primary-blue-light) !important;
        transform: translateY(-1px) !important;
        box-shadow: var(--shadow-lg) !important;
    }
    
    /* Sidebar Input Styling */
    section[data-testid="stSidebar"] .stNumberInput input,
    section[data-testid="stSidebar"] .stTextInput input {
        background: var(--bg-dark-tertiary) !important;
        color: var(--text-white) !important;
        border: 2px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: var(--radius-md) !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] .stNumberInput input:focus,
    section[data-testid="stSidebar"] .stTextInput input:focus {
        border-color: var(--primary-blue-light) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* Sidebar Success/Info Messages */
    section[data-testid="stSidebar"] .stSuccess {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 182, 212, 0.15) 100%) !important;
        color: var(--success-light) !important;
        border: 2px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
    }
    
    section[data-testid="stSidebar"] .stInfo {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%) !important;
        color: var(--info-light) !important;
        border: 2px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
    }
    
    /* Custom Alert Styling */
    .stAlert {
        border-radius: var(--radius-lg) !important;
        border: none !important;
        box-shadow: var(--shadow-lg) !important;
        font-weight: 600 !important;
        padding: 1.25rem !important;
    }
    
    .stAlert[data-baseweb="notification"] {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%) !important;
        color: var(--success) !important;
        border-left: 4px solid var(--success) !important;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .app-header {
            padding: 2rem 1rem;
        }
        
        .app-header h1 {
            font-size: 2.5rem;
        }
        
        .chat-message {
            max-width: 95%;
        }
        
        .file-grid {
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        }
        
        .feature-grid {
            grid-template-columns: 1fr;
        }
        
        .welcome-container {
            padding: 2.5rem 1.5rem;
        }
        
        .content-area {
            padding: 1rem;
        }
        
        .card {
            padding: 1.5rem;
        }
    }
    
    @media (max-width: 480px) {
        .app-header h1 {
            font-size: 2rem;
        }
        
        .app-header p {
            font-size: 1rem;
        }
        
        .card-header h3 {
            font-size: 1.2rem;
        }
        
        .metric-value {
            font-size: 2rem;
        }
        
        .upload-area {
            padding: 2rem 1rem;
        }
    }
    
    /* Loading Animations */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    @keyframes shimmer {
        0% { background-position: -468px 0; }
        100% { background-position: 468px 0; }
    }
    
    .loading {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    .shimmer {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 400% 100%;
        animation: shimmer 1.5s ease-in-out infinite;
    }
    
    /* Focus Styles for Accessibility */
    button:focus,
    input:focus,
    select:focus,
    textarea:focus {
        outline: 3px solid rgba(59, 130, 246, 0.5) !important;
        outline-offset: 2px !important;
    }
    
    /* High Contrast Mode Support */
    @media (prefers-contrast: high) {
        :root {
            --primary-blue: #0000ff;
            --text-primary: #000000;
            --bg-primary: #ffffff;
        }
    }
    
    /* Reduced Motion Support */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* Print Styles */
    @media print {
        .sidebar, .app-header {
            display: none !important;
        }
        
        .card {
            box-shadow: none !important;
            border: 1px solid #000 !important;
        }
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