import streamlit as st
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Import local modules
from database import db_manager
from workflow import cv_workflow
from utils import (
    setup_directories, save_uploaded_file, get_file_info,
    validate_file_type, format_file_size, generate_session_id,
    truncate_text, format_score, get_pass_status_emoji,
    estimate_processing_time, format_datetime, get_file_icon
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enable debug logging for API calls (uncomment for debugging)
# logging.getLogger("vintern_api").setLevel(logging.DEBUG)
# logging.getLogger("workflow").setLevel(logging.DEBUG)

# Page configuration
st.set_page_config(
    page_title="CV Evaluator AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
    }
    
    .result-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
    }
    
    .pass-card {
        border-left-color: #28a745;
    }
    
    .fail-card {
        border-left-color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'evaluation_results' not in st.session_state:
        st.session_state.evaluation_results = None
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

def render_sidebar():
    """Render sidebar with session management"""
    st.sidebar.title("🗂️ Quản lý Sessions")
    
    # Create new session
    if st.sidebar.button("➕ Tạo Session mới"):
        st.session_state.current_session_id = generate_session_id()
        st.session_state.evaluation_results = None
        st.session_state.uploaded_files = []
        st.rerun()
    
    # Show current session
    if st.session_state.current_session_id:
        st.sidebar.success(f"Session hiện tại: {st.session_state.current_session_id[:8]}...")
    
    st.sidebar.markdown("---")
    
    # Session history
    st.sidebar.subheader("📋 Lịch sử Sessions")
    sessions = db_manager.get_all_sessions()
    
    if sessions:
        for session in sessions[:10]:  # Show last 10 sessions
            with st.sidebar.expander(
                f"📅 {format_datetime(session['created_at'])}"
            ):
                st.write(f"**JD:** {session['job_description']}")
                st.write(f"**Số lượng cần tuyển:** {session['required_candidates']}")
                st.write(f"**Tổng CV:** {session['total_cvs']}")
                st.write(f"**Đã đánh giá:** {session['total_evaluations']}")
                
                if st.button(f"Xem kết quả", key=f"view_{session['session_id']}"):
                    st.session_state.current_session_id = session['session_id']
                    st.session_state.evaluation_results = db_manager.get_session_results(session['session_id'])
                    st.rerun()
    else:
        st.sidebar.info("Chưa có session nào")

def render_main_content():
    """Render main content area"""
    st.markdown("""
    <div class="main-header">
        <h1>🤖 CV Evaluator AI</h1>
        <p>Hệ thống đánh giá CV tự động sử dụng AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if we have a current session
    if not st.session_state.current_session_id:
        st.info("👈 Vui lòng tạo session mới từ sidebar để bắt đầu")
        return
    
    # Show evaluation results if available
    if st.session_state.evaluation_results:
        render_evaluation_results()
        return
    
    # Main form
    render_evaluation_form()

def render_evaluation_form():
    """Render the main evaluation form"""
    st.subheader("📝 Thiết lập đánh giá CV")
    
    # Job description input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        job_description = st.text_area(
            "📋 Mô tả công việc (Job Description)",
            height=200,
            placeholder="Nhập mô tả công việc, yêu cầu kỹ năng, kinh nghiệm..."
        )
    
    with col2:
        required_candidates = st.number_input(
            "👥 Số lượng cần tuyển",
            min_value=1,
            max_value=50,
            value=5
        )
        
        st.markdown("### 📊 Thông tin")
        st.info(f"Session ID: {st.session_state.current_session_id[:8]}...")
    
    # File upload section
    st.subheader("📁 Upload CV")
    uploaded_files = st.file_uploader(
        "Chọn các file CV (PDF hoặc ảnh)",
        accept_multiple_files=True,
        type=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']
    )
    
    if uploaded_files:
        st.write(f"**Đã chọn {len(uploaded_files)} file:**")
        
        total_size = 0
        valid_files = []
        
        for file in uploaded_files:
            file_size = file.size
            total_size += file_size
            
            # Validate file type
            if validate_file_type(file.type):
                valid_files.append(file)
                st.write(f"- {get_file_icon(file.type)} {file.name} ({format_file_size(file_size)})")
            else:
                st.error(f"❌ {file.name} - Loại file không được hỗ trợ")
        
        if valid_files:
            st.success(f"✅ {len(valid_files)} file hợp lệ - Tổng dung lượng: {format_file_size(total_size)}")
            
            # Estimate processing time
            estimated_time = estimate_processing_time(len(valid_files))
            st.info(f"⏱️ Thời gian xử lý ước tính: {estimated_time}")
            
            # Start evaluation button
            if st.button("🚀 Bắt đầu đánh giá", type="primary"):
                if not job_description.strip():
                    st.error("❌ Vui lòng nhập mô tả công việc")
                    return
                
                start_evaluation(job_description, required_candidates, valid_files)

def start_evaluation(job_description: str, required_candidates: int, uploaded_files: List):
    """Start the evaluation process"""
    # Setup directories
    setup_directories()
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Save uploaded files
        status_text.text("🔄 Đang lưu file...")
        progress_bar.progress(0.1)
        
        saved_files = []
        for i, file in enumerate(uploaded_files):
            file_path = save_uploaded_file(file)
            file_info = get_file_info(file, file_path)
            saved_files.append(file_info)
            
            progress_bar.progress(0.1 + (i + 1) / len(uploaded_files) * 0.2)
        
        # Step 2: Run workflow
        status_text.text("🤖 Đang xử lý CV...")
        progress_bar.progress(0.3)
        
        result = cv_workflow.run_evaluation(
            st.session_state.current_session_id,
            job_description,
            required_candidates,
            saved_files
        )
        
        progress_bar.progress(1.0)
        
        if result["success"]:
            status_text.text("✅ Hoàn thành!")
            st.session_state.evaluation_results = result["results"]
            st.success("🎉 Đánh giá CV hoàn thành!")
            st.rerun()
        else:
            status_text.text("❌ Có lỗi xảy ra")
            st.error(f"Lỗi: {result['error']}")
            
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        st.error(f"Có lỗi xảy ra: {str(e)}")
    finally:
        # Clean up progress indicators
        progress_bar.empty()
        status_text.empty()

def render_evaluation_results():
    """Render evaluation results"""
    results = st.session_state.evaluation_results
    
    if isinstance(results, dict):
        # Results from workflow
        st.subheader("📊 Kết quả đánh giá")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📋 Tổng số CV", results.get("total_cvs", 0))
        
        with col2:
            st.metric("✅ Đạt yêu cầu", results.get("passed_count", 0))
        
        with col3:
            st.metric("📊 Điểm trung bình", f"{results.get('average_score', 0):.1f}/10")
        
        with col4:
            pass_rate = results.get("summary", {}).get("pass_rate", 0)
            st.metric("📈 Tỷ lệ đạt", f"{pass_rate}%")
        
        # Top candidates
        st.subheader("🏆 Ứng viên xuất sắc")
        top_candidates = results.get("top_candidates", [])
        
        if top_candidates:
            for i, candidate in enumerate(top_candidates, 1):
                with st.expander(f"#{i} - {candidate['filename']} {format_score(candidate['score'])}"):
                    st.write(f"**Điểm số:** {candidate['score']:.1f}/10")
                    st.write(f"**Trạng thái:** {get_pass_status_emoji(candidate['is_passed'])} {'Đạt' if candidate['is_passed'] else 'Không đạt'}")
                    
                    # Parse evaluation if it's JSON
                    try:
                        eval_data = json.loads(candidate['evaluation_text'])
                        if isinstance(eval_data, dict):
                            evaluation = eval_data.get('evaluation', {})
                            
                            st.write("**Điểm mạnh:**")
                            for strength in evaluation.get('strengths', []):
                                st.write(f"- ✅ {strength}")
                            
                            st.write("**Điểm yếu:**")
                            for weakness in evaluation.get('weaknesses', []):
                                st.write(f"- ❌ {weakness}")
                            
                            st.write(f"**Phù hợp công việc:** {evaluation.get('job_fit', 'N/A')}")
                            st.write(f"**Khuyến nghị:** {evaluation.get('recommendation', 'N/A')}")
                    except:
                        st.write("**Đánh giá:**")
                        st.write(candidate['evaluation_text'])
        
        # All results
        st.subheader("📋 Tất cả kết quả")
        all_evaluations = results.get("all_evaluations", [])
        
        if all_evaluations:
            for evaluation in all_evaluations:
                card_class = "pass-card" if evaluation['is_passed'] else "fail-card"
                st.markdown(f"""
                <div class="result-card {card_class}">
                    <h4>{evaluation['filename']} - {format_score(evaluation['score'])}</h4>
                    <p><strong>Trạng thái:</strong> {get_pass_status_emoji(evaluation['is_passed'])} {'Đạt yêu cầu' if evaluation['is_passed'] else 'Không đạt yêu cầu'}</p>
                </div>
                """, unsafe_allow_html=True)
    
    else:
        # Results from database
        st.subheader("📊 Kết quả đánh giá")
        
        if results:
            # Calculate summary
            total_cvs = len(results)
            passed_cvs = sum(1 for r in results if r['is_passed'])
            avg_score = sum(r['score'] for r in results) / total_cvs
            pass_rate = passed_cvs / total_cvs * 100
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📋 Tổng số CV", total_cvs)
            
            with col2:
                st.metric("✅ Đạt yêu cầu", passed_cvs)
            
            with col3:
                st.metric("📊 Điểm trung bình", f"{avg_score:.1f}/10")
            
            with col4:
                st.metric("📈 Tỷ lệ đạt", f"{pass_rate:.1f}%")
            
            # Results table
            st.subheader("📋 Chi tiết kết quả")
            
            for result in results:
                with st.expander(f"{result['filename']} - {format_score(result['score'])}"):
                    st.write(f"**Điểm số:** {result['score']:.1f}/10")
                    st.write(f"**Trạng thái:** {get_pass_status_emoji(result['is_passed'])} {'Đạt' if result['is_passed'] else 'Không đạt'}")
                    st.write(f"**Thời gian:** {format_datetime(result['created_at'])}")
                    
                    # Show evaluation details
                    st.write("**Đánh giá chi tiết:**")
                    try:
                        eval_data = json.loads(result['evaluation_text'])
                        if isinstance(eval_data, dict):
                            evaluation = eval_data.get('evaluation', {})
                            
                            st.write("**Điểm mạnh:**")
                            for strength in evaluation.get('strengths', []):
                                st.write(f"- ✅ {strength}")
                            
                            st.write("**Điểm yếu:**")
                            for weakness in evaluation.get('weaknesses', []):
                                st.write(f"- ❌ {weakness}")
                            
                            st.write(f"**Phù hợp công việc:** {evaluation.get('job_fit', 'N/A')}")
                            st.write(f"**Khuyến nghị:** {evaluation.get('recommendation', 'N/A')}")
                        else:
                            st.write(result['evaluation_text'])
                    except:
                        st.write(result['evaluation_text'])
        else:
            st.info("Không có kết quả đánh giá nào")
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Đánh giá mới"):
            st.session_state.evaluation_results = None
            st.rerun()
    
    with col2:
        if st.button("📊 Xuất báo cáo"):
            # Export functionality can be added here
            st.info("Tính năng xuất báo cáo sẽ được thêm vào")

def main():
    """Main application function"""
    # Initialize
    initialize_session_state()
    setup_directories()
    
    # Render UI
    render_sidebar()
    render_main_content()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "CV Evaluator AI - Powered by Vintern & LangGraph"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()