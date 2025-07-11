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
    """Lấy cached workflow instance"""
    return get_cv_workflow()

@st.cache_resource  
def get_cached_gpt_evaluator():
    """Lấy cached GPT evaluator instance"""
    return get_gpt_evaluator()

@st.cache_resource
def get_cached_email_service():
    """Lấy cached email service instance"""
    return email_service

# Page configuration
st.set_page_config(
    page_title="Hệ thống Đánh giá CV bằng AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling with Vietnamese support
st.markdown("""
<style>
    /* Import Professional Fonts with Vietnamese support */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=Roboto:wght@300;400;500;700&display=swap');
    
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
        --bg-secondary: #eceff4;
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
    
    /* Global Styles with Vietnamese font support */
    .stApp {
        font-family: 'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(to bottom, #141E30, #243B55);
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
    
    /* Buttons - Enhanced Design for Vietnamese text */
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
        letter-spacing: 0.025em !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
        max-width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        line-height: 1.2 !important;
        min-height: 44px !important;
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
        color: black;
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
        letter-spacing: 0.025em !important;
        transition: all 0.3s ease !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
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
    """Khởi tạo trạng thái phiên nâng cao với tích hợp cơ sở dữ liệu và session_title"""
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
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
    if 'session_title_suggestions' not in st.session_state:
        st.session_state.session_title_suggestions = []
    
    # Tải lịch sử chat từ cơ sở dữ liệu nếu phiên tồn tại
    if st.session_state.current_session_id:
        load_chat_history_from_db()

def load_chat_history_from_db():
    """Tải lịch sử chat từ cơ sở dữ liệu"""
    try:
        if st.session_state.current_session_id:
            chat_history = db_manager.get_chat_history(st.session_state.current_session_id)
            # Lưu trữ trong session state để tương thích
            st.session_state.chat_history = chat_history
    except Exception as e:
        logger.error(f"Lỗi tải lịch sử chat: {e}")
        st.session_state.chat_history = []

def render_sidebar():
    """Thanh bên nâng cao với hiển thị session_title"""
    with st.sidebar:
        # Header
        st.markdown("""
        <div class="sidebar-header">
            <h2 style="margin: 0; color: white; font-weight: 700;">🎯 Đánh giá CV</h2>
            <p style="margin: 0.5rem 0 0 0; color: #cbd5e1; font-size: 0.9rem;">Hệ thống AI Tuyển dụng</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quản lý phiên
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h4>🗂️ Quản lý phiên</h4>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Tạo mới", help="Tạo phiên mới", use_container_width=True):
                st.session_state.current_session_id = generate_session_id()
                st.session_state.session_state = None
                st.session_state.job_description = ""
                st.session_state.position_title = ""
                st.rerun()
        
        with col2:
            if st.button("🔄 Làm mới", help="Làm mới phiên", use_container_width=True):
                if st.session_state.current_session_id:
                    session_state = cv_workflow.get_session_state(st.session_state.current_session_id)
                    if session_state:
                        st.session_state.session_state = session_state
                        st.session_state.job_description = session_state.get('job_description', '')
                        st.session_state.position_title = session_state.get('position_title', '')
                st.rerun()
        
        # Thông tin phiên hiện tại với session_title
        if st.session_state.current_session_id:
            # Lấy thông tin hiển thị session
            display_info = cv_workflow.get_session_display_info(st.session_state.current_session_id)
            session_title = display_info.get('display_name', f'Phiên {st.session_state.current_session_id[:8]}...')
            
            # Hiển thị tên phiên thay vì session_id
            st.success(f"**Phiên đang hoạt động:**\n{session_title}")
            
            # Tính năng đổi tên phiên
            with st.expander("✏️ Đổi tên phiên"):
                current_title = st.session_state.session_state.get('session_title', '') if st.session_state.session_state else ''
                
                new_title = st.text_input(
                    "Tên phiên mới:",
                    value=current_title,
                    placeholder="VD: Tuyển Frontend Developer - React",
                    key="new_session_title"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Lưu", use_container_width=True):
                        if new_title.strip() and new_title != current_title:
                            if cv_workflow.update_session_title(st.session_state.current_session_id, new_title.strip()):
                                st.success("✅ Đã đổi tên!")
                                # Cập nhật session state
                                if st.session_state.session_state:
                                    st.session_state.session_state['session_title'] = new_title.strip()
                                st.rerun()
                            else:
                                st.error("❌ Lỗi đổi tên!")
                
                with col2:
                    if st.button("🎯 Gợi ý", use_container_width=True):
                        if st.session_state.job_description:
                            suggestions = cv_workflow.generate_session_title_suggestions(
                                st.session_state.job_description, 
                                st.session_state.position_title
                            )
                            st.write("**Gợi ý:**")
                            for i, suggestion in enumerate(suggestions, 1):
                                if st.button(f"{i}. {suggestion}", key=f"suggest_{i}", use_container_width=True):
                                    st.session_state.new_session_title = suggestion
                                    st.rerun()
            
            # Cài đặt phiên
            with st.expander("⚙️ Cài đặt"):
                st.session_state.required_candidates = st.number_input(
                    "Số ứng viên cần tuyển", 
                    min_value=1, max_value=20, 
                    value=st.session_state.required_candidates,
                    key="sidebar_required_candidates"
                )
                
                st.session_state.auto_refresh = st.checkbox(
                    "Tự động làm mới", 
                    value=st.session_state.auto_refresh,
                    help="Tự động làm mới kết quả"
                )
        else:
            st.info("Chưa có phiên hoạt động")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Phiên gần đây với session_title
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h4>📋 Phiên gần đây</h4>', unsafe_allow_html=True)
        
        # Thêm tìm kiếm phiên
        search_term = st.text_input(
            "🔍 Tìm kiếm phiên:",
            placeholder="Nhập tên phiên hoặc vị trí...",
            key="session_search"
        )
        
        if search_term:
            sessions = cv_workflow.search_sessions(search_term)
        else:
            sessions = db_manager.get_all_sessions()
        
        if sessions:
            for session in sessions[:5]:  # Hiển thị 5 phiên gần nhất
                # Sử dụng session_title thay vì created_at
                session_display_name = session.get('session_title', f"Phiên {session['session_id'][:8]}...")
                
                with st.expander(f"📅 {session_display_name}"):
                    st.write(f"**Vị trí:** {session.get('position_title', 'N/A')}")
                    st.write(f"**CV:** {session['total_cvs']}")
                    st.write(f"**Đánh giá:** {session['total_evaluations']}")
                    st.write(f"**Tạo lúc:** {format_datetime(session['created_at'])}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"📂 Tải", key=f"load_{session['session_id']}", use_container_width=True):
                            st.session_state.current_session_id = session['session_id']
                            session_state = cv_workflow.get_session_state(session['session_id'])
                            if session_state:
                                st.session_state.session_state = session_state
                                st.session_state.job_description = session_state.get('job_description', '')
                                st.session_state.position_title = session_state.get('position_title', '')
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🗑️ Xóa", key=f"del_{session['session_id']}", use_container_width=True):
                            if db_manager.delete_session(session['session_id']):
                                st.success("Đã xóa phiên!")
                                st.rerun()
        else:
            if search_term:
                st.info(f"Không tìm thấy phiên nào với '{search_term}'")
            else:
                st.info("Chưa có phiên gần đây")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Thống kê phiên hiện tại (giữ nguyên như trước)
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h4>📊 Thống kê phiên hiện tại</h4>', unsafe_allow_html=True)
        
        if st.session_state.current_session_id and st.session_state.session_state:
            session_state = st.session_state.session_state
            
            # Lấy phân tích từ cơ sở dữ liệu
            analytics = db_manager.get_session_analytics(st.session_state.current_session_id)
            
            if analytics:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("📁 Tệp tin", analytics.get('total_files_uploaded', 0))
                    st.metric("📊 Đánh giá", analytics.get('total_evaluations', 0))
                    
                with col2:
                    st.metric("📈 Điểm TB", f"{analytics.get('average_score', 0):.1f}")
                    st.metric("💬 Tin nhắn", analytics.get('total_chat_messages', 0))
                
                # Hiển thị tỷ lệ đạt yêu cầu nếu có
                if session_state.get('final_results'):
                    results = session_state['final_results']
                    qualified_count = results.get('qualified_count', 0)
                    total_cvs = results.get('total_cvs', 0)
                    
                    if total_cvs > 0:
                        pass_rate = (qualified_count / total_cvs) * 100
                        st.metric("✅ Tỷ lệ đạt", f"{pass_rate:.1f}%")
                        
                    # Hiển thị thông tin phiên chi tiết
                    st.markdown("---")
                    st.markdown("**📋 Chi tiết phiên:**")
                    st.write(f"• Vị trí: {session_state.get('position_title', 'N/A')}")
                    st.write(f"• Cần tuyển: {session_state.get('required_candidates', 0)} người")
                    st.write(f"• Trạng thái: {session_state.get('processing_status', 'N/A')}")
                    
                    # Hiển thị kết quả nhanh
                    if results:
                        best_score = results.get('summary', {}).get('best_score', 0)
                        worst_score = results.get('summary', {}).get('worst_score', 0)
                        st.write(f"• Điểm cao nhất: {best_score:.1f}")
                        st.write(f"• Điểm thấp nhất: {worst_score:.1f}")
            else:
                st.info("Chưa có dữ liệu phân tích cho phiên này")
        else:
            st.info("Chưa có phiên hoạt động")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Thống kê hệ thống tổng (di chuyển xuống cuối và thu gọn)
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        
        with st.expander("🗄️ Thống kê hệ thống"):
            db_stats = db_manager.get_database_stats()
            if db_stats:
                st.write(f"**Tổng phiên:** {db_stats.get('total_sessions', 0)}")
                st.write(f"**Tổng CV:** {db_stats.get('total_cvs', 0)}")
                st.write(f"**Điểm TB toàn hệ thống:** {db_stats.get('average_score', 0):.1f}")
                
                # Thêm nút migrate old sessions
                if st.button("🔄 Tạo title cho phiên cũ", use_container_width=True):
                    updated = cv_workflow.migrate_old_sessions_to_titles()
                    if updated > 0:
                        st.success(f"✅ Đã tạo title cho {updated} phiên!")
                    else:
                        st.info("Tất cả phiên đã có title")
            else:
                st.write("Không có dữ liệu")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_header():
    """Hiển thị header ứng dụng với session title"""
    # Get current session display name
    session_display = ""
    if st.session_state.current_session_id and st.session_state.session_state:
        session_title = st.session_state.session_state.get('session_title', '')
        if session_title:
            session_display = f" • {session_title}"
    
    st.markdown(f"""
    <div class="app-header">
        <h1>🎯 Hệ thống Đánh giá CV bằng AI{session_display}</h1>
        <p>Trợ lý AI tuyển dụng tương tác • Trò chuyện với kết quả đánh giá • Thông tin chi tiết theo thời gian thực</p>
    </div>
    """, unsafe_allow_html=True)

def render_chat_interface():
    """Hiển thị giao diện chat chính"""
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    
    if not st.session_state.current_session_id:
        render_welcome_screen()
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Bố cục chính
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_chat_messages()
        render_file_upload_area()
    
    with col2:
        render_session_info()
        render_quick_actions()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_welcome_screen():
    """Màn hình chào mừng chuyên nghiệp"""
    st.markdown("""
    <div class="welcome-container">
        <h2>Chào mừng đến với Hệ thống Đánh giá CV bằng AI</h2>
        <p style="font-size: 1.1rem; margin-bottom: 3rem; line-height: 1.6;">
            Biến đổi quy trình tuyển dụng của bạn với đánh giá CV được hỗ trợ bởi AI, 
            chấm điểm tự động và khớp ứng viên thông minh.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Thẻ tính năng
    st.markdown('<div class="feature-grid">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">🤖</span>
            <h4>Phân tích AI Tiên tiến</h4>
            <p>OCR tiên tiến với Gemini và đánh giá thời gian thực sử dụng GPT-3.5-turbo với phản hồi trực tiếp.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">💬</span>
            <h4>Chat AI Tương tác</h4>
            <p>Đặt câu hỏi về ứng viên cụ thể, nhận thông tin chi tiết và tương tác với dữ liệu đánh giá một cách tự nhiên.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📊</span>
            <h4>Thông tin Thời gian Thực</h4>
            <p>Nhận phản hồi tức thì trong quá trình đánh giá, phản hồi trực tiếp và phân tích ứng viên toàn diện theo yêu cầu.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bắt đầu
    st.markdown("""
    <div class="card" style="margin-top: 2rem; text-align: center;">
        <h3 style="color: #2c3e50; margin-bottom: 1rem;">🚀 Bắt đầu</h3>
        <p style="color: #6c757d; margin-bottom: 1.5rem;">Sẵn sàng cách mạng hóa tuyển dụng? Làm theo các bước đơn giản này:</p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">1️⃣</div>
                <strong>Tạo phiên</strong><br>
                <small style="color: #6c757d;">Nhấp "➕ Tạo mới" ở thanh bên</small>
            </div>
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">2️⃣</div>
                <strong>Đặt yêu cầu</strong><br>
                <small style="color: #6c757d;">Định nghĩa mô tả công việc & tiêu chí</small>
            </div>
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">3️⃣</div>
                <strong>Tải CV lên</strong><br>
                <small style="color: #6c757d;">Kéo thả tệp ứng viên</small>
            </div>
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">4️⃣</div>
                <strong>Chat & Khám phá</strong><br>
                <small style="color: #6c757d;">Đặt câu hỏi về ứng viên</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_chat_messages():
    """Hiển thị chat đã sửa lỗi HTML - không có vấn đề khoảng trắng"""
    st.markdown("""
        <h2 style='color: white;'>💬 Cuộc trò chuyện với Trợ lý AI</h2>
    """, unsafe_allow_html=True)
    
    # Tải lịch sử chat mới từ cơ sở dữ liệu
    if st.session_state.current_session_id:
        chat_history = db_manager.get_chat_history(st.session_state.current_session_id)
    else:
        chat_history = []
    
    if chat_history:
        # CSS trong một khối
        st.markdown("""<style>
        .simple-chat {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 1rem;
            max-height: 500px;
            overflow-y: auto;
            margin: 1rem 0;
        }
        .chat-msg {
            margin: 0.8rem 0;
            padding: 0.8rem;
            border-radius: 6px;
            color: #000000 !important;
            font-size: 14px;
            line-height: 1.4;
        }
        .msg-system { background: #f0f8ff; border-left: 3px solid #0066cc; }
        .msg-user { background: #f5f5f5; border-left: 3px solid #666; }
        .msg-result { background: #f0fff0; border-left: 3px solid #00aa00; }
        .msg-error { background: #fff0f0; border-left: 3px solid #cc0000; }
        .msg-summary { background: #fffaf0; border-left: 3px solid #ff8800; }
        .msg-time { font-size: 11px; color: #666; margin-bottom: 4px; }
        .msg-text { color: #000000 !important; font-weight: normal; }
        </style>""", unsafe_allow_html=True)
        
        # Xây dựng chuỗi HTML KHÔNG có khoảng trắng giữa các thẻ
        messages_html = []
        messages_html.append('<div class="simple-chat">')
        
        for message in chat_history:
            msg_type = message.get('type', 'system')
            msg_text = message.get('message', '')
            timestamp = datetime.fromtimestamp(message.get('timestamp', time.time())).strftime("%H:%M:%S")
            
            # Làm sạch văn bản tin nhắn
            clean_msg_text = str(msg_text).replace('<', '&lt;').replace('>', '&gt;')
            
            # Lấy lớp CSS và biểu tượng
            type_map = {
                'system': ('msg-system', '🤖'),
                'user': ('msg-user', '👤'),
                'result': ('msg-result', '📊'),
                'error': ('msg-error', '❌'),
                'summary': ('msg-summary', '📈')
            }
            
            css_class, icon = type_map.get(msg_type, ('msg-system', '💭'))
            
            # Xây dựng HTML tin nhắn - KHÔNG có khoảng trắng giữa các thẻ
            message_html = f'<div class="chat-msg {css_class}"><div class="msg-time">{icon} {timestamp}</div><div class="msg-text">{clean_msg_text}</div></div>'
            messages_html.append(message_html)
        
        messages_html.append('</div>')
        
        # Kết hợp không có bất kỳ dấu phân cách nào để tránh khoảng trắng
        final_html = ''.join(messages_html)
        
        # Hiển thị dưới dạng khối đơn
        st.markdown(final_html, unsafe_allow_html=True)
        
    else:
        # Trạng thái trống
        st.markdown("""<div style="text-align: center; padding: 2rem; background: #f9f9f9; border-radius: 8px; border: 1px dashed #ccc; color: #000000;"><h4 style="color: #000000;">💭 Chưa có tin nhắn nào</h4><p style="color: #666;">Bắt đầu bằng cách tải CV lên hoặc đặt câu hỏi!</p></div>""", unsafe_allow_html=True)
    
    # Đầu vào chat
    if st.session_state.current_session_id:
        st.markdown("---")
        
        # Khu vực đầu vào
        user_question = st.text_input(
            "💬 Hỏi về ứng viên hoặc CV:",
            placeholder="VD: Hãy cho tôi biết về kinh nghiệm của ứng viên hàng đầu",
            key="chat_input"
        )
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("Gửi", type="primary", use_container_width=True):
                if user_question.strip():
                    handle_chat_query(user_question.strip())
                    st.rerun()
        
        with col2:
            if st.button("🧹 Xóa", use_container_width=True):
                if st.session_state.current_session_id:
                    db_manager.clear_chat_history(st.session_state.current_session_id)
                    st.success("Đã xóa chat!")
                    st.rerun()
        
        # Nút nhanh
        if st.session_state.session_state and st.session_state.session_state.get('final_results'):
            with col3:
                if st.button("👥 Top ứng viên", use_container_width=True):
                    handle_chat_query("Ai là 3 ứng viên hàng đầu và tại sao?")
                    st.rerun()
            
            with col4:
                if st.button("📊 Tóm tắt", use_container_width=True):
                    handle_chat_query("Cho tôi một bản tóm tắt tất cả kết quả đánh giá")
                    st.rerun()

def render_file_upload_area():
    """Giao diện tải tệp nâng cao"""
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon">📁</div>
            <h3>Tải lên & Xử lý CV</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Nhập mô tả công việc (nếu chưa đặt)
    if not st.session_state.job_description:
        st.markdown("""
            <h3 style='color: white;'>📋 Yêu cầu công việc</h3>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            job_description = st.text_area(
                "Mô tả công việc",
                height=120,
                placeholder="Nhập yêu cầu công việc chi tiết, kỹ năng, kinh nghiệm cần thiết...",
                key="job_desc_input"
            )
            
        with col2:
            position_title = st.text_input(
                "Tên vị trí",
                placeholder="VD: Lập trình viên Python",
                key="position_input"
            )
            
            required_candidates = st.number_input(
                "Số ứng viên cần tuyển",
                min_value=1, max_value=20,
                value=3,
                key="candidates_input"
            )
        
        if st.button("💾 Lưu thông tin công việc", type="primary", use_container_width=True):
            if job_description.strip():
                st.session_state.job_description = job_description
                st.session_state.position_title = position_title or "Vị trí"
                st.session_state.required_candidates = required_candidates
                st.success("✅ Đã lưu thông tin công việc thành công!")
                st.rerun()
            else:
                st.error("❌ Vui lòng nhập mô tả công việc")
    
    # Khu vực tải tệp
    st.markdown('''
    <div class="upload-area">
        <h4>🎯 Kéo thả tệp CV vào đây</h4>
        <p>Định dạng hỗ trợ: PDF, JPG, PNG, GIF, BMP, TIFF • Kích thước tối đa: 200MB mỗi tệp</p>
    </div>
    ''', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Chọn tệp CV",
        accept_multiple_files=True,
        type=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'],
        key="file_uploader",
        label_visibility="collapsed"
    )
    
    if uploaded_files and st.session_state.job_description:
        # Hiển thị tệp đã tải lên
        st.markdown("""
            <h3 style='color: white;'>📋 Tệp đã chọn</h3>
        """, unsafe_allow_html=True)
        
        valid_files = []
        total_size = 0
        
        # Lưới tệp
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
                    st.error(f"❌ {file.name} - Loại tệp không được hỗ trợ")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if valid_files:
            # Tóm tắt
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tệp hợp lệ", len(valid_files))
            with col2:
                st.metric("Tổng kích thước", format_file_size(total_size))
            with col3:
                estimated_time = len(valid_files) * 15
                st.metric("Thời gian ước tính", f"{estimated_time}s")
            
            # Nút xử lý
            if st.button("🚀 Bắt đầu đánh giá AI", type="primary", use_container_width=True):
                start_chat_evaluation_with_streaming(valid_files)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_session_info():
    """Thông tin phiên nâng cao với session_title"""
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon">📊</div>
            <h3>Thông tin phiên</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.current_session_id and st.session_state.session_state:
        session = st.session_state.session_state
        
        # Hiển thị session title prominently
        session_title = session.get('session_title', 'Phiên không có tên')
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; text-align: center;">
            <h3 style="margin: 0; color: white;">📝 {session_title}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Lấy phân tích chi tiết từ cơ sở dữ liệu
        analytics = db_manager.get_session_analytics(st.session_state.current_session_id)
        session_info = db_manager.get_session(st.session_state.current_session_id)
        
        # Chi tiết phiên
        if session_info:
            st.markdown(f"**🎯 Vị trí:** {session_info.get('position_title', 'N/A')}")
            st.markdown(f"**📅 Tạo lúc:** {format_datetime(session_info.get('created_at', ''))}")
            st.markdown(f"**👥 Cần tuyển:** {session_info.get('required_candidates', 'N/A')} người")
            st.markdown(f"**⚡ Trạng thái:** {session_info.get('status', 'đang hoạt động').title()}")
        
        st.markdown("---")
        
        # Thống kê xử lý (giữ nguyên phần còn lại)
        if analytics:
            st.markdown("### 📈 Thống kê xử lý")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{analytics.get('total_files_uploaded', 0)}</div>
                    <div class="metric-label">Tệp đã tải</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{analytics.get('total_files_processed', 0)}</div>
                    <div class="metric-label">Tệp đã xử lý</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{analytics.get('total_chat_messages', 0)}</div>
                    <div class="metric-label">Tin nhắn chat</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Kết quả đánh giá
        if 'final_results' in session and session['final_results']:
            results = session['final_results']
            
            st.markdown("### 📊 Kết quả đánh giá")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{results.get('total_cvs', 0)}</div>
                    <div class="metric-label">Tổng CV</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{results.get('qualified_count', 0)}</div>
                    <div class="metric-label">Đạt yêu cầu</div>
                </div>
                """, unsafe_allow_html=True)
            
            avg_score = results.get('average_score', 0)
            qualification_rate = results.get('summary', {}).get('qualification_rate', 0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_score:.1f}</div>
                    <div class="metric-label">Điểm TB</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{qualification_rate:.1f}%</div>
                    <div class="metric-label">Tỷ lệ đạt</div>
                </div>
                """, unsafe_allow_html=True)
    
    else:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #6c757d;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔄</div>
            <p>Chưa có phiên hoạt động</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_quick_actions():
    """Bảng thao tác nhanh nâng cao"""
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon">⚡</div>
            <h3>Thao tác nhanh</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.session_state and st.session_state.session_state.get('final_results'):
        results = st.session_state.session_state['final_results']
        
        # Nút thao tác chính
        if st.button("📊 Xem kết quả chi tiết", use_container_width=True):
            render_detailed_results(results)
        
        if st.button("📋 Yêu cầu phân tích AI", use_container_width=True):
            render_ai_report()
        
        st.markdown("### 📧 Thao tác email")
        
        qualified_count = results.get('qualified_count', 0)
        rejected_count = results.get('total_cvs', 0) - qualified_count
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"❌ Từ chối\n({rejected_count})", use_container_width=True):
                send_rejection_emails_manual()
        
        with col2:
            if st.button(f"✅ Phỏng vấn\n({qualified_count})", use_container_width=True):
                schedule_interview_emails_manual()
        
        st.markdown("### 📤 Tùy chọn xuất")
        
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
            <p style="margin: 0;">Hoàn thành đánh giá để mở khóa thao tác</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def handle_chat_query(question: str):
    """Xử lý truy vấn chat người dùng với lưu trữ cơ sở dữ liệu"""
    try:
        if not st.session_state.current_session_id:
            st.error("Không có phiên hoạt động. Vui lòng tạo phiên mới trước.")
            return
        
        # Lưu tin nhắn người dùng vào cơ sở dữ liệu
        cv_workflow.add_chat_message_to_session(
            st.session_state.current_session_id,
            'user',
            question,
            'user'
        )
        
        # Kiểm tra nếu chúng ta có dữ liệu đánh giá
        if not st.session_state.session_state or not st.session_state.session_state.get('final_results'):
            cv_workflow.add_chat_message_to_session(
                st.session_state.current_session_id,
                'system',
                "🤖 Tôi chưa có dữ liệu đánh giá nào. Vui lòng tải lên và đánh giá một số CV trước!"
            )
            return
        
        # Lấy dữ liệu phiên hiện tại
        session_data = st.session_state.session_state
        results = session_data.get('final_results', {})
        job_description = session_data.get('job_description', '')
        
        # Tạo ngữ cảnh cho AI
        context = create_chat_context(results, job_description, question)
        
        # Tạo phản hồi AI
        with st.spinner("🤖 AI đang suy nghĩ..."):
            response = generate_chat_response(context, question)
        
        # Lưu phản hồi AI vào cơ sở dữ liệu
        cv_workflow.add_chat_message_to_session(
            st.session_state.current_session_id,
            'result',
            f"🤖 {response}",
            'assistant'
        )
        
    except Exception as e:
        logger.error(f"Lỗi xử lý truy vấn chat: {e}")
        cv_workflow.add_chat_message_to_session(
            st.session_state.current_session_id,
            'error',
            f"❌ Lỗi xử lý câu hỏi của bạn: {str(e)}",
            'system'
        )

def create_chat_context(results: Dict, job_description: str, question: str) -> str:
    """Tạo ngữ cảnh cho phản hồi chat AI"""
    try:
        all_evaluations = results.get('all_evaluations', [])
        
        # Tạo ngữ cảnh tóm tắt
        context = f"""
        MÔ TẢ CÔNG VIỆC:
        {job_description}
        
        TÓM TẮT KẾT QUẢ ĐÁNH GIÁ:
        - Tổng CV: {results.get('total_cvs', 0)}
        - Ứng viên đạt yêu cầu: {results.get('qualified_count', 0)}
        - Điểm trung bình: {results.get('average_score', 0):.1f}/10
        - Tỷ lệ đạt: {results.get('summary', {}).get('qualification_rate', 0):.1f}%
        
        CHI TIẾT ỨNG VIÊN:
        """
        
        # Thêm thông tin ứng viên
        for i, candidate in enumerate(all_evaluations[:10], 1):  # Giới hạn 10 ứng viên hàng đầu
            filename = candidate.get('filename', f'Ứng viên {i}')
            score = candidate.get('score', 0)
            qualified = "✅ Đạt yêu cầu" if candidate.get('is_qualified', False) else "❌ Không đạt yêu cầu"
            
            context += f"\n{i}. {filename} - Điểm: {score:.1f}/10 - {qualified}"
            
            # Thêm chi tiết đánh giá nếu có
            eval_text = candidate.get('evaluation_text', '')
            if eval_text:
                try:
                    eval_data = json.loads(eval_text)
                    if isinstance(eval_data, dict):
                        summary = eval_data.get('Tổng kết', '')
                        strengths = eval_data.get('Điểm mạnh', [])
                        if summary:
                            context += f"\n   Tóm tắt: {summary}"
                        if strengths:
                            context += f"\n   Điểm mạnh: {', '.join(strengths[:3])}"
                except:
                    pass
            
            # Thêm văn bản CV đã trích xuất cho các truy vấn chi tiết
            extracted_text = candidate.get('extracted_text', '')
            if extracted_text and len(question) > 50:  # Cho các câu hỏi chi tiết
                context += f"\n   Nội dung CV: {extracted_text[:500]}..."
        
        return context
        
    except Exception as e:
        logger.error(f"Lỗi tạo ngữ cảnh chat: {e}")
        return f"Mô tả công việc: {job_description}\nDữ liệu đánh giá có sẵn nhưng lỗi xử lý chi tiết."

def generate_chat_response(context: str, question: str) -> str:
    """Tạo phản hồi AI cho truy vấn chat"""
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return "Khóa API OpenAI chưa được cấu hình. Vui lòng kiểm tra cài đặt môi trường."
        
        client = OpenAI(api_key=openai_api_key)
        
        prompt = f"""
        Bạn là một trợ lý AI chuyên gia tư vấn tuyển dụng. Bạn có quyền truy cập vào dữ liệu đánh giá CV và nên cung cấp thông tin hữu ích, chuyên nghiệp về ứng viên.
        
        NGỮ CẢNH:
        {context}
        
        CÂU HỎI NGƯỜI DÙNG: {question}
        
        Vui lòng cung cấp phản hồi hữu ích, chuyên nghiệp dựa trên dữ liệu đánh giá. Nếu câu hỏi về ứng viên cụ thể, hãy sử dụng dữ liệu thực tế của họ. Hãy súc tích nhưng đầy đủ thông tin.
        
        Hướng dẫn:
        - Hãy chuyên nghiệp và hữu ích
        - Sử dụng dữ liệu cụ thể từ các đánh giá khi có
        - Nếu được hỏi về ứng viên theo tên, hãy tìm kiếm qua nội dung CV
        - Cung cấp thông tin chi tiết có thể thực hiện cho các quyết định tuyển dụng
        - Giữ phản hồi súc tích nhưng đầy đủ
        - Sử dụng tiếng Việt để trả lời
        - Luôn trả lời bằng tiếng Việt
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Bạn là trợ lý AI tuyển dụng chuyên nghiệp. Cung cấp thông tin hữu ích dựa trên dữ liệu đánh giá CV. Luôn trả lời bằng tiếng Việt."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Lỗi tạo phản hồi chat: {e}")
        return f"Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn: {str(e)}"

def start_chat_evaluation_with_streaming(uploaded_files: List):
    """Bắt đầu đánh giá với tích hợp cơ sở dữ liệu"""
    try:
        if not st.session_state.current_session_id:
            st.error("Không có phiên hoạt động. Vui lòng tạo phiên mới trước.")
            return
        
        if not st.session_state.job_description:
            st.error("Vui lòng đặt mô tả công việc trước.")
            return
        
        setup_directories()
        
        # Lưu tệp
        saved_files = []
        for file in uploaded_files:
            file_path = save_uploaded_file(file)
            file_info = get_file_info(file, file_path)
            saved_files.append(file_info)
        
        # Sử dụng quy trình làm việc đã cập nhật với tích hợp cơ sở dữ liệu
        cv_workflow_instance = get_cached_workflow()
        
        with st.spinner("🚀 Đang bắt đầu quy trình đánh giá AI..."):
            result = cv_workflow_instance.run_evaluation(
                st.session_state.current_session_id,
                st.session_state.job_description,
                st.session_state.required_candidates,
                saved_files,
                st.session_state.position_title
            )
        
        if result["success"]:
            # Cập nhật trạng thái phiên
            st.session_state.session_state = {
                "session_id": result["session_id"],
                "final_results": result.get("results", {}),
                "processing_status": result.get("status", "hoàn thành"),
                "job_description": st.session_state.job_description,
                "position_title": st.session_state.position_title,
                "required_candidates": st.session_state.required_candidates
            }
            
            st.success("✅ Đánh giá hoàn thành thành công!")
            
        else:
            st.error(f"❌ Đánh giá thất bại: {result.get('error', 'Lỗi không xác định')}")
            
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Lỗi bắt đầu đánh giá: {str(e)}")
        logger.error(f"Lỗi bắt đầu đánh giá chat: {e}")

def render_detailed_results(results: Dict):
    """Hiển thị kết quả đánh giá chi tiết"""
    st.subheader("📊 Kết quả đánh giá chi tiết")
    
    # Chỉ số tóm tắt
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Tổng CV", results.get("total_cvs", 0))
    with col2:
        st.metric("✅ Đạt yêu cầu", results.get("qualified_count", 0))
    with col3:
        st.metric("📊 Điểm trung bình", f"{results.get('average_score', 0):.1f}/10")
    with col4:
        qualification_rate = results.get("summary", {}).get("qualification_rate", 0)
        st.metric("📈 Tỷ lệ đạt", f"{qualification_rate}%")
    
    # Ứng viên hàng đầu
    st.subheader("🏆 Ứng viên hàng đầu")
    top_candidates = results.get("top_candidates", [])
    
    for i, candidate in enumerate(top_candidates, 1):
        with st.expander(f"#{i} - {candidate.get('filename', 'Không rõ')} {format_score(candidate.get('score', 0))}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write(f"**Điểm:** {candidate.get('score', 0):.1f}/10")
                status = "✅ Đạt yêu cầu" if candidate.get('is_qualified', False) else "❌ Không đạt yêu cầu"
                st.write(f"**Trạng thái:** {status}")
            
            with col2:
                evaluation_text = candidate.get('evaluation_text', '')
                if evaluation_text:
                    try:
                        eval_data = json.loads(evaluation_text)
                        if isinstance(eval_data, dict):
                            st.write("**Tóm tắt:**", eval_data.get('Tổng kết', 'N/A'))
                            
                            strengths = eval_data.get('Điểm mạnh', [])
                            if strengths:
                                st.write("**Điểm mạnh:**")
                                for strength in strengths[:3]:
                                    st.write(f"• {strength}")
                                    
                            weaknesses = eval_data.get('Điểm yếu', [])
                            if weaknesses:
                                st.write("**Điểm cần cải thiện:**")
                                for weakness in weaknesses[:2]:
                                    st.write(f"• {weakness}")
                        else:
                            st.write(evaluation_text[:200] + "..." if len(evaluation_text) > 200 else evaluation_text)
                    except:
                        st.write(evaluation_text[:200] + "..." if len(evaluation_text) > 200 else evaluation_text)
    
    # Biểu đồ phân bổ điểm
    st.subheader("📈 Phân bổ điểm số")
    all_evaluations = results.get("all_evaluations", [])
    
    if all_evaluations:
        scores = [eval.get('score', 0) for eval in all_evaluations]
        
        # Tạo histogram đơn giản
        score_ranges = {
            "9.0-10.0": sum(1 for s in scores if 9 <= s <= 10),
            "8.0-8.9": sum(1 for s in scores if 8 <= s < 9),
            "7.0-7.9": sum(1 for s in scores if 7 <= s < 8),
            "6.0-6.9": sum(1 for s in scores if 6 <= s < 7),
            "5.0-5.9": sum(1 for s in scores if 5 <= s < 6),
            "0.0-4.9": sum(1 for s in scores if 0 <= s < 5)
        }
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(score_ranges)
        
        with col2:
            st.write("**Phân tích:**")
            excellent = score_ranges["9.0-10.0"]
            good = score_ranges["8.0-8.9"] + score_ranges["7.0-7.9"]
            average = score_ranges["6.0-6.9"] + score_ranges["5.0-5.9"]
            poor = score_ranges["0.0-4.9"]
            
            st.write(f"• Xuất sắc (9-10): {excellent} người")
            st.write(f"• Tốt (7-8.9): {good} người")
            st.write(f"• Trung bình (5-6.9): {average} người")
            st.write(f"• Yếu (0-4.9): {poor} người")

def render_ai_report():
    """Chat AI đơn giản về kết quả thay vì báo cáo chính thức"""
    if not st.session_state.session_state or not st.session_state.session_state.get('final_results'):
        st.error("Không có kết quả đánh giá")
        return
    
    # Kích hoạt truy vấn chat để phân tích toàn diện
    comprehensive_query = "Vui lòng cung cấp phân tích toàn diện về tất cả kết quả đánh giá bao gồm ứng viên hàng đầu, đánh giá tổng thể và khuyến nghị tuyển dụng."
    handle_chat_query(comprehensive_query)
    st.rerun()

def send_rejection_emails_manual():
    """Kích hoạt thủ công cho email từ chối"""
    if not st.session_state.session_state:
        st.error("Không có dữ liệu phiên")
        return
    
    results = st.session_state.session_state.get('final_results', {})
    rejected_candidates = results.get('rejected_candidates', [])
    position_title = st.session_state.session_state.get('position_title', 'Vị trí')
    
    if not rejected_candidates:
        st.info("Không có ứng viên bị từ chối để gửi email")
        return
    
    try:
        email_svc = get_cached_email_service()
        email_svc.send_rejection_emails(rejected_candidates, position_title)
        st.success(f"📧 Đang gửi email từ chối đến {len(rejected_candidates)} ứng viên")
        
        cv_workflow.add_chat_message_to_session(
            st.session_state.current_session_id,
            'system',
            f"📧 Đã kích hoạt thủ công email từ chối cho {len(rejected_candidates)} ứng viên",
            'system'
        )
        
    except Exception as e:
        st.error(f"Lỗi gửi email từ chối: {str(e)}")

def schedule_interview_emails_manual():
    """Kích hoạt thủ công cho lịch hẹn email phỏng vấn"""
    if not st.session_state.session_state:
        st.error("Không có dữ liệu phiên")
        return
    
    results = st.session_state.session_state.get('final_results', {})
    qualified_candidates = results.get('qualified_candidates', [])
    position_title = st.session_state.session_state.get('position_title', 'Vị trí')
    
    if not qualified_candidates:
        st.info("Không có ứng viên đạt yêu cầu để lên lịch phỏng vấn")
        return
    
    try:
        email_svc = get_cached_email_service()
        email_svc.schedule_interview_emails(qualified_candidates, position_title)
        st.success(f"⏰ Đã lên lịch email phỏng vấn cho {len(qualified_candidates)} ứng viên")
        
        cv_workflow.add_chat_message_to_session(
            st.session_state.current_session_id,
            'system',
            f"⏰ Đã lên lịch thủ công email phỏng vấn cho {len(qualified_candidates)} ứng viên",
            'system'
        )
        
    except Exception as e:
        st.error(f"Lỗi lên lịch email phỏng vấn: {str(e)}")

def export_results_json():
    """Xuất kết quả dưới dạng JSON"""
    if not st.session_state.session_state:
        st.error("Không có dữ liệu để xuất")
        return
    
    try:
        data = {
            "session_id": st.session_state.current_session_id,
            "export_timestamp": datetime.now().isoformat(),
            "job_description": st.session_state.session_state.get('job_description', ''),
            "position_title": st.session_state.session_state.get('position_title', ''),
            "results": st.session_state.session_state.get('final_results', {}),
            "chat_history": st.session_state.chat_history if hasattr(st.session_state, 'chat_history') else []
        }
        
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label="💾 Tải xuống JSON",
            data=json_str,
            file_name=f"danh_gia_cv_{st.session_state.current_session_id[:8]}.json",
            mime="application/json"
        )
        
    except Exception as e:
        st.error(f"Lỗi xuất JSON: {str(e)}")

def export_summary_csv():
    """Xuất tóm tắt dưới dạng CSV"""
    if not st.session_state.session_state:
        st.error("Không có dữ liệu để xuất")
        return
    
    try:
        results = st.session_state.session_state.get('final_results', {})
        all_evaluations = results.get('all_evaluations', [])
        
        if not all_evaluations:
            st.error("Không có dữ liệu đánh giá để xuất")
            return
        
        csv_lines = ["Tên_file,Điểm,Đạt_yêu_cầu,Tóm_tắt"]
        
        for eval in all_evaluations:
            filename = eval.get('filename', '').replace(',', ';')
            score = eval.get('score', 0)
            qualified = "Có" if eval.get('is_qualified', False) else "Không"
            
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
            label="📊 Tải xuống CSV",
            data=csv_content,
            file_name=f"tom_tat_cv_{st.session_state.current_session_id[:8]}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Lỗi xuất CSV: {str(e)}")

def render_system_status():
    """Hiển thị trạng thái hệ thống"""
    with st.sidebar:
        with st.expander("🔧 Trạng thái hệ thống"):
            st.write("**Dịch vụ:**")
            
            # Kiểm tra OpenAI
            try:
                gpt_evaluator = get_cached_gpt_evaluator()
                if gpt_evaluator:
                    st.write("✅ OpenAI GPT-3.5")
                else:
                    st.write("❌ OpenAI GPT-3.5")
            except:
                st.write("❌ OpenAI GPT-3.5")
            
            # Kiểm tra Gemini
            try:
                if gemini_ocr:
                    st.write("✅ Gemini OCR")
                else:
                    st.write("❌ Gemini OCR")
            except:
                st.write("❌ Gemini OCR")
            
            # Kiểm tra Email
            try:
                email_svc = get_cached_email_service()
                if email_svc.validate_config():
                    st.write("✅ Email Service")
                else:
                    st.write("⚠️ Email (Chưa cấu hình)")
            except:
                st.write("❌ Email Service")
            
            # Kiểm tra Database
            try:
                stats = db_manager.get_database_stats()
                if stats:
                    st.write("✅ Database")
                else:
                    st.write("❌ Database")
            except:
                st.write("❌ Database")

def render_help_section():
    """Hiển thị phần trợ giúp"""
    with st.sidebar:
        with st.expander("❓ Trợ giúp"):
            st.markdown("""
            **🚀 Cách sử dụng:**
            1. Tạo phiên mới
            2. Nhập mô tả công việc
            3. Tải CV lên (PDF/Hình ảnh)
            4. Chờ AI đánh giá
            5. Chat để phân tích thêm
            
            **📧 Hỗ trợ:**
            - Email: nguyentuongbachhy@gmail.com
            - Hotline: 0911076983
            
            **🔧 Xử lý sự cố:**
            - Làm mới trang nếu gặp lỗi
            - Kiểm tra kết nối internet
            - Đảm bảo file CV < 10MB
            """)

def main():
    """Hàm ứng dụng chính nâng cao với cơ sở dữ liệu"""
    initialize_session_state()
    setup_directories()
    
    # Logic tự động làm mới với cơ sở dữ liệu
    if st.session_state.auto_refresh and st.session_state.current_session_id:
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()
        
        if time.time() - st.session_state.last_refresh > 30:
            session_state = cv_workflow.get_session_state(st.session_state.current_session_id)
            if session_state:
                st.session_state.session_state = session_state
            st.session_state.last_refresh = time.time()
            st.rerun()
    
    # Bố cục
    render_sidebar()
    render_system_status()  # Thêm trạng thái hệ thống
    render_help_section()   # Thêm phần trợ giúp
    render_header()
    render_chat_interface()

if __name__ == "__main__":
    main()