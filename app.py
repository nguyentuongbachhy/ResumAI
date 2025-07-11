import streamlit as st
import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Import local modules
from database import db_manager
from workflow import get_cv_workflow, cv_workflow
from gpt_evaluator import get_gpt_evaluator
from email_service import email_service
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

@st.cache_data(ttl=60)  # Cache for 60 seconds
def check_model_status_cached():
    """Cached model status check"""
    return check_model_status_internal()

def check_model_status_internal():
    """Internal model status check without caching"""
    status = {
        "gemini_ocr": False,
        "gpt_evaluator": False,
        "email_service": False,
        "database": False
    }
    
    try:
        # Check Gemini OCR
        if os.getenv('GOOGLE_API_KEY'):
            status["gemini_ocr"] = True
        
        # Check GPT Evaluator
        if os.getenv('OPENAI_API_KEY'):
            try:
                gpt_eval = get_cached_gpt_evaluator()
                status["gpt_evaluator"] = True  # Assume OK if no exception
            except Exception as e:
                logger.error(f"GPT evaluator check failed: {e}")
                status["gpt_evaluator"] = False
        
        # Check Email Service
        smtp_user = os.getenv('SMTP_USER') or os.getenv('SMTP_EMAIL')
        smtp_pass = os.getenv('SMTP_PASS') or os.getenv('SMTP_PASSWORD')
        if smtp_user and smtp_pass:
            try:
                email_svc = get_cached_email_service()
                # Don't test connection every time, just check if credentials exist
                status["email_service"] = True
            except Exception as e:
                logger.error(f"Email service check failed: {e}")
                status["email_service"] = False
        else:
            status["email_service"] = False
        
        # Check Database
        try:
            db_manager.get_database_stats()
            status["database"] = True
        except:
            status["database"] = False
            
    except Exception as e:
        logger.error(f"Error checking model status: {e}")
    
    return status

# Page configuration
st.set_page_config(
    page_title="CV Evaluator AI - Chat Interface",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for chat interface
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .chat-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
    }
    
    .chat-message {
        margin: 0.8rem 0;
        padding: 0.8rem;
        border-radius: 8px;
        max-width: 80%;
    }
    
    .user-message {
        background: #007bff;
        color: white;
        margin-left: auto;
        text-align: right;
    }
    
    .system-message {
        background: #28a745;
        color: white;
        margin-right: auto;
    }
    
    .result-message {
        background: #17a2b8;
        color: white;
        margin-right: auto;
    }
    
    .error-message {
        background: #dc3545;
        color: white;
        margin-right: auto;
    }
    
    .summary-message {
        background: #ffc107;
        color: black;
        margin-right: auto;
        font-weight: bold;
    }
    
    .upload-area {
        color: black;
        border: 2px dashed #007bff;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
        background: #f8f9ff;
    }
    
    .status-indicator {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 0.2rem;
    }
    
    .status-ready {
        background: #d4edda;
        color: #155724;
    }
    
    .status-processing {
        background: #fff3cd;
        color: #856404;
    }
    
    .status-completed {
        background: #d1ecf1;
        color: #0c5460;
    }
    
    .status-error {
        background: #f8d7da;
        color: #721c24;
    }
    
    .model-status {
        color: black;
        background: #e8f5e8;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 3px solid #28a745;
        margin: 0.5rem 0;
    }
    
    .email-status {
        color: black;
        background: #e7f3ff;
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
    }
    
    .quick-actions {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
    
    .file-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .file-card {
        color: black;
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        text-align: center;
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

def check_model_status():
    """Check the status of all models and services"""
    status = {
        "gemini_ocr": False,
        "gpt_evaluator": False,
        "email_service": False,
        "database": False
    }
    
    try:
        # Check Gemini OCR
        if os.getenv('GOOGLE_API_KEY'):
            status["gemini_ocr"] = True
        
        # Check GPT Evaluator
        if os.getenv('OPENAI_API_KEY'):
            gpt_eval = get_gpt_evaluator()
            status["gpt_evaluator"] = True
        
        # Check Email Service
        if os.getenv('SMTP_EMAIL') and os.getenv('SMTP_PASSWORD'):
            status["email_service"] = email_service.test_email_connection()
        
        # Check Database
        try:
            db_manager.get_database_stats()
            status["database"] = True
        except:
            status["database"] = False
            
    except Exception as e:
        logger.error(f"Error checking model status: {e}")
    
    return status

def render_sidebar():
    """Enhanced sidebar with session management and model status"""
    st.sidebar.title("💬 CV Evaluator Chat")
    
    # Session management
    st.sidebar.subheader("🗂️ Session Management")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("➕ New Session", help="Create a new evaluation session"):
            st.session_state.current_session_id = generate_session_id()
            st.session_state.chat_history = []
            st.session_state.session_state = None
            st.session_state.job_description = ""
            st.session_state.position_title = ""
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh", help="Refresh current session"):
            if st.session_state.current_session_id:
                # Reload session state
                session_state = cv_workflow.get_session_state(st.session_state.current_session_id)
                if session_state:
                    st.session_state.session_state = session_state
                    st.session_state.chat_history = session_state.get('chat_history', [])
            st.rerun()
    
    # Current session info
    if st.session_state.current_session_id:
        st.sidebar.success(f"Session: {st.session_state.current_session_id[:8]}...")
        
        # Session settings
        with st.sidebar.expander("⚙️ Session Settings"):
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
    
    st.sidebar.markdown("---")
    
    # Model and service status
    st.sidebar.subheader("🤖 System Status")
    model_status = check_model_status()
    
    # Status indicators
    for service, status in model_status.items():
        service_name = {
            "gemini_ocr": "🔍 Gemini OCR",
            "gpt_evaluator": "🤖 GPT-3.5-turbo", 
            "email_service": "📧 Email Service",
            "database": "💾 Database"
        }[service]
        
        if status:
            st.sidebar.markdown(
                f'<div class="model-status">✅ {service_name}: Ready</div>',
                unsafe_allow_html=True
            )
        else:
            st.sidebar.error(f"❌ {service_name}: Not Ready")
    
    # Email configuration status
    if model_status["email_service"]:
        st.sidebar.info("📧 Email notifications enabled")
    else:
        st.sidebar.warning("📧 Email not configured")
    
    st.sidebar.markdown("---")
    
    # Recent sessions
    st.sidebar.subheader("📋 Recent Sessions")
    sessions = db_manager.get_all_sessions()
    
    if sessions:
        for session in sessions[:3]:  # Show last 3 sessions
            with st.sidebar.expander(f"📅 {format_datetime(session['created_at'])}"):
                st.write(f"**CVs:** {session['total_cvs']}")
                st.write(f"**Evaluations:** {session['total_evaluations']}")
                
                if st.button(f"Load Session", key=f"load_{session['session_id']}"):
                    st.session_state.current_session_id = session['session_id']
                    # Load session state
                    session_state = cv_workflow.get_session_state(session['session_id'])
                    if session_state:
                        st.session_state.session_state = session_state
                        st.session_state.chat_history = session_state.get('chat_history', [])
                        st.session_state.job_description = session_state.get('job_description', '')
                        st.session_state.position_title = session_state.get('position_title', '')
                    st.rerun()
    else:
        st.sidebar.info("No recent sessions")

def render_chat_interface():
    """Render the main chat interface"""
    st.markdown("""
    <div class="main-header">
        <h1>💬 CV Evaluator Chat Interface</h1>
        <p>Upload CVs, get evaluations, and receive automated email notifications</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if we have a current session
    if not st.session_state.current_session_id:
        render_welcome_screen()
        return
    
    # Main chat layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_chat_messages()
        render_file_upload_area()
    
    with col2:
        render_session_info()
        render_quick_actions()

def render_welcome_screen():
    """Render welcome screen for new users"""
    st.markdown("""
    ### 👋 Welcome to CV Evaluator AI Chat!
    
    This enhanced system provides:
    - 💬 **Chat Interface**: Upload and evaluate CVs in a conversational way
    - 🤖 **AI-Powered Evaluation**: Using Gemini OCR + GPT-3.5-turbo
    - 📧 **Automated Emails**: Send interview invites and rejection emails
    - 📊 **Real-time Updates**: See evaluation progress in real-time
    - 💾 **Persistent Sessions**: Continue your work anytime
    
    **To get started:**
    1. Click "➕ New Session" in the sidebar
    2. Set up your job description and requirements
    3. Upload CV files and start chatting!
    """)
    
    # Sample job descriptions
    with st.expander("📝 Sample Job Descriptions"):
        st.markdown("""
        **Python Developer:**
        ```
        Tuyển dụng Python Developer
        - Kinh nghiệm 2+ năm với Python
        - Thành thạo Django/Flask
        - Kiến thức về PostgreSQL, Redis
        - Kinh nghiệm Docker, AWS
        - Kỹ năng làm việc nhóm tốt
        ```
        
        **Frontend Developer:**
        ```
        Tuyển dụng Frontend Developer
        - Thành thạo React.js, Vue.js
        - Kinh nghiệm HTML5, CSS3, JavaScript ES6+
        - Hiểu biết về responsive design
        - Kinh nghiệm Git, npm/yarn
        - Portfolio về UI/UX
        ```
        """)

def render_chat_messages():
    """Render chat message history"""
    st.subheader("💬 Chat History")
    
    chat_container = st.container()
    
    with chat_container:
        if st.session_state.chat_history:
            # Create scrollable chat area
            chat_html = '<div class="chat-container">'
            
            for message in st.session_state.chat_history:
                msg_type = message.get('type', 'system')
                msg_text = message.get('message', '')
                timestamp = datetime.fromtimestamp(message.get('timestamp', time.time())).strftime("%H:%M:%S")
                
                css_class = f"{msg_type}-message"
                chat_html += f'''
                <div class="chat-message {css_class}">
                    <small>{timestamp}</small><br>
                    {msg_text}
                </div>
                '''
            
            chat_html += '</div>'
            st.markdown(chat_html, unsafe_allow_html=True)
        else:
            st.info("💬 No messages yet. Upload some CVs to start the conversation!")

def render_file_upload_area():
    """Render enhanced file upload area"""
    st.subheader("📁 Upload CV Files")
    
    # Job description input (if not set)
    if not st.session_state.job_description:
        with st.expander("📋 Job Requirements (Required)", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                job_description = st.text_area(
                    "Job Description",
                    height=150,
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
            
            if st.button("💾 Save Job Info", type="primary"):
                if job_description.strip():
                    st.session_state.job_description = job_description
                    st.session_state.position_title = position_title or "Position"
                    st.session_state.required_candidates = required_candidates
                    st.success("✅ Job information saved!")
                    st.rerun()
                else:
                    st.error("❌ Please enter job description")
    
    # File upload area
    st.markdown('''
    <div class="upload-area">
        <h4>🎯 Drag & Drop CV Files Here</h4>
        <p>Supported: PDF, JPG, PNG, GIF, BMP, TIFF</p>
    </div>
    ''', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Choose CV files",
        accept_multiple_files=True,
        type=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'],
        key="file_uploader"
    )
    
    if uploaded_files and st.session_state.job_description:
        # Display uploaded files in grid
        st.markdown("### 📋 Selected Files:")
        
        valid_files = []
        total_size = 0
        
        # Create file grid
        num_cols = 3
        cols = st.columns(num_cols)
        
        for i, file in enumerate(uploaded_files):
            col_idx = i % num_cols
            
            with cols[col_idx]:
                if validate_file_type(file.type):
                    valid_files.append(file)
                    total_size += file.size
                    
                    st.markdown(f'''
                    <div class="file-card">
                        {get_file_icon(file.type)} <br>
                        <strong>{file.name}</strong><br>
                        <small>{format_file_size(file.size)}</small>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.error(f"❌ {file.name} - Unsupported file type")
        
        if valid_files:
            st.success(f"✅ {len(valid_files)} valid files - Total: {format_file_size(total_size)}")
            
            # Processing time estimate
            estimated_time = len(valid_files) * 15  # 15 seconds per file
            st.info(f"⏱️ Estimated processing time: ~{estimated_time} seconds")
            
            # Process button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 Start AI Evaluation", type="primary", use_container_width=True):
                    start_chat_evaluation(valid_files)

def render_session_info():
    """Render current session information panel"""
    st.subheader("📊 Session Info")
    
    if st.session_state.session_state:
        session = st.session_state.session_state
        
        # Processing status
        status = session.get('processing_status', 'unknown')
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
        st.markdown(f'''
        <div class="status-indicator {status_class}">
            Status: {status.replace('_', ' ').title()}
        </div>
        ''', unsafe_allow_html=True)
        
        # Session details
        st.write(f"**Position:** {session.get('position_title', 'N/A')}")
        st.write(f"**Required:** {session.get('required_candidates', 'N/A')} candidates")
        
        # Processing progress
        if 'final_results' in session and session['final_results']:
            results = session['final_results']
            st.write(f"**CVs Processed:** {results.get('total_cvs', 0)}")
            st.write(f"**Qualified:** {results.get('qualified_count', 0)}")
            st.write(f"**Average Score:** {results.get('average_score', 0):.1f}/10")
        
        # Email status
        email_status = session.get('email_status', {})
        if email_status.get('sent'):
            st.markdown(f'''
            <div class="email-status">
                📧 <strong>Email Status:</strong><br>
                • Rejection emails: {email_status.get('rejection_count', 0)} sent<br>
                • Interview invites: {email_status.get('interview_count', 0)} scheduled
            </div>
            ''', unsafe_allow_html=True)
    
    else:
        st.info("No active session")

def render_quick_actions():
    """Render quick action buttons"""
    st.subheader("⚡ Quick Actions")
    
    if st.session_state.session_state and st.session_state.session_state.get('final_results'):
        results = st.session_state.session_state['final_results']
        
        # View results button
        if st.button("📊 View Detailed Results", use_container_width=True):
            render_detailed_results(results)
        
        # Generate report button
        if st.button("📋 Generate AI Report", use_container_width=True):
            render_ai_report()
        
        # Email actions
        st.markdown("### 📧 Email Actions")
        
        qualified_count = results.get('qualified_count', 0)
        rejected_count = results.get('total_cvs', 0) - qualified_count
        
        if st.button(f"📧 Send Rejection Emails ({rejected_count})", use_container_width=True):
            send_rejection_emails_manual()
        
        if st.button(f"⏰ Schedule Interview Emails ({qualified_count})", use_container_width=True):
            schedule_interview_emails_manual()
    
    # Export options
    st.markdown("### 📤 Export Options")
    
    if st.button("💾 Export Results (JSON)", use_container_width=True):
        export_results_json()
    
    if st.button("📊 Export Summary (CSV)", use_container_width=True):
        export_summary_csv()

def start_chat_evaluation(uploaded_files: List):
    """Start evaluation process with chat updates"""
    try:
        # Setup directories
        setup_directories()
        
        # Save files
        saved_files = []
        for file in uploaded_files:
            file_path = save_uploaded_file(file)
            file_info = get_file_info(file, file_path)
            saved_files.append(file_info)
        
        # Add user message to chat
        st.session_state.chat_history.append({
            "type": "user",
            "message": f"📁 Uploaded {len(saved_files)} CV files for evaluation",
            "timestamp": time.time()
        })
        
        # Start workflow with cached instance
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
            # Update session state
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
            
            # Merge chat histories
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
                            # Show structured evaluation
                            st.write("**Summary:**", eval_data.get('Tổng kết', 'N/A'))
                            
                            strengths = eval_data.get('Điểm mạnh', [])
                            if strengths:
                                st.write("**Strengths:**")
                                for strength in strengths[:3]:  # Show top 3
                                    st.write(f"• {strength}")
                        else:
                            st.write(evaluation_text[:200] + "..." if len(evaluation_text) > 200 else evaluation_text)
                    except:
                        st.write(evaluation_text[:200] + "..." if len(evaluation_text) > 200 else evaluation_text)

def render_ai_report():
    """Render AI-generated comprehensive report"""
    st.subheader("📋 AI-Generated Comprehensive Report")
    
    if not st.session_state.session_state or not st.session_state.session_state.get('final_results'):
        st.error("No evaluation results available")
        return
    
    results = st.session_state.session_state['final_results']
    job_description = st.session_state.session_state.get('job_description', '')
    
    st.info("🤖 Generating comprehensive report with GPT-3.5-turbo...")
    
    # Create streaming container
    report_container = st.empty()
    
    try:
        full_response = ""
        
        cv_workflow_instance = get_cached_workflow()
        for chunk in cv_workflow_instance.generate_final_response_stream(results, job_description):
            full_response += chunk
            # Update display with streaming effect
            report_container.markdown(full_response)
            time.sleep(0.03)  # Smooth streaming
        
        # Final formatted display
        report_container.markdown(full_response)
        
    except Exception as e:
        report_container.error(f"Error generating report: {str(e)}")

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
        
        # Update chat history
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
        
        # Update chat history
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
        
        # Create CSV content
        csv_lines = ["Filename,Score,Qualified,Summary"]
        
        for eval in all_evaluations:
            filename = eval.get('filename', '').replace(',', ';')
            score = eval.get('score', 0)
            qualified = "Yes" if eval.get('is_qualified', False) else "No"
            
            # Extract summary from evaluation text
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
    # Initialize
    initialize_session_state()
    setup_directories()
    
    # Auto-refresh logic
    if st.session_state.auto_refresh and st.session_state.current_session_id:
        # Check for session updates every 30 seconds
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
    
    # Render UI
    render_sidebar()
    render_chat_interface()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "💬 CV Evaluator AI Chat - Enhanced with Email Automation<br>"
        "🤖 Powered by Gemini OCR + GPT-3.5-turbo + Smart Email Service"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()