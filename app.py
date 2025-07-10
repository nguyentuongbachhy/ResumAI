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
from workflow import cv_workflow
from gpt_evaluator import get_gpt_evaluator  # Updated import
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

# Page configuration
st.set_page_config(
    page_title="CV Evaluator AI - GPT-3.5-turbo",  # Updated title
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .result-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .qualified-card {
        border-left-color: #28a745;
        background: #f8fff9;
    }
    
    .not-qualified-card {
        border-left-color: #dc3545;
        background: #fff8f8;
    }
    
    .streaming-container {
        color: black;
        background: #f0f2f6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        min-height: 200px;
        border: 1px solid #d1d5db;
    }
    
    .model-status {
        color: black;
        background: #e8f5e8;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 3px solid #28a745;
        margin: 0.5rem 0;
    }
    
    .gpt-highlight {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'evaluation_results' not in st.session_state:
        st.session_state.evaluation_results = None
    if 'show_final_report' not in st.session_state:
        st.session_state.show_final_report = False

def convert_db_results_to_format(db_results: List[Dict]) -> Dict:
    """Convert database results list to expected dictionary format"""
    if not db_results:
        return {
            "total_cvs": 0,
            "qualified_count": 0,
            "average_score": 0,
            "top_candidates": [],
            "all_evaluations": [],
            "summary": {
                "best_score": 0,
                "worst_score": 0,
                "qualification_rate": 0
            }
        }
    
    # Sort by score (highest first)
    sorted_results = sorted(db_results, key=lambda x: x.get('score', 0), reverse=True)
    
    # Calculate statistics
    total_cvs = len(sorted_results)
    qualified_cvs = sum(1 for result in sorted_results if result.get('is_passed', False))
    avg_score = sum(result.get('score', 0) for result in sorted_results) / total_cvs if total_cvs > 0 else 0
    
    # Convert to expected format
    converted_results = []
    for result in sorted_results:
        converted_result = {
            "cv_id": result.get('filename', ''),  # Use filename as identifier
            "filename": result.get('filename', ''),
            "score": result.get('score', 0),
            "is_qualified": result.get('is_passed', False),
            "evaluation_text": result.get('evaluation_text', ''),
            "gpt_response": result.get('evaluation_text', '')  # Same as evaluation_text for db results
        }
        converted_results.append(converted_result)
    
    return {
        "total_cvs": total_cvs,
        "qualified_count": qualified_cvs,
        "average_score": round(avg_score, 2),
        "top_candidates": converted_results[:3],  # Top 3
        "all_evaluations": converted_results,
        "summary": {
            "best_score": sorted_results[0].get('score', 0) if sorted_results else 0,
            "worst_score": sorted_results[-1].get('score', 0) if sorted_results else 0,
            "qualification_rate": round(qualified_cvs / total_cvs * 100, 1) if total_cvs > 0 else 0
        }
    }

def check_model_status():
    """Check the status of all models"""
    status = {
        "gemini_ocr": False,
        "gpt_evaluator": False,
        "gpt_streaming": False
    }
    
    try:
        # Check Gemini OCR
        if os.getenv('GOOGLE_API_KEY'):
            status["gemini_ocr"] = True
        
        # Check GPT Evaluator
        if os.getenv('OPENAI_API_KEY'):
            gpt_eval = get_gpt_evaluator()
            if gpt_eval.test_connection():
                status["gpt_evaluator"] = True
                status["gpt_streaming"] = True
    except Exception as e:
        logger.error(f"Error checking model status: {e}")
    
    return status

def render_sidebar():
    """Render sidebar with session management"""
    st.sidebar.title("🗂️ Quản lý Sessions")
    
    # Create new session
    if st.sidebar.button("➕ Tạo Session mới"):
        st.session_state.current_session_id = generate_session_id()
        st.session_state.evaluation_results = None
        st.session_state.show_final_report = False
        st.rerun()
    
    # Show current session
    if st.session_state.current_session_id:
        st.sidebar.success(f"Session: {st.session_state.current_session_id[:8]}...")
    
    st.sidebar.markdown("---")
    
    # Model status
    st.sidebar.subheader("🤖 AI Models Status")
    model_status = check_model_status()
    
    # Gemini OCR Status
    if model_status["gemini_ocr"]:
        st.sidebar.markdown(
            '<div class="model-status">✅ Gemini OCR: Ready</div>',
            unsafe_allow_html=True
        )
    else:
        st.sidebar.error("❌ Gemini OCR: API key missing")
    
    # GPT Evaluator Status
    if model_status["gpt_evaluator"]:
        st.sidebar.markdown(
            '<div class="gpt-highlight">🚀 GPT-3.5-turbo: Ready & Active</div>',
            unsafe_allow_html=True
        )
    else:
        st.sidebar.error("❌ GPT-3.5-turbo: Connection failed")
    
    # GPT Streaming Status
    if model_status["gpt_streaming"]:
        st.sidebar.markdown(
            '<div class="model-status">📡 GPT Streaming: Ready</div>',
            unsafe_allow_html=True
        )
    else:
        st.sidebar.error("❌ GPT Streaming: Not available")
    
    # Model Info
    st.sidebar.info("💡 Sử dụng GPT-3.5-turbo để đánh giá CV nhanh chóng và chính xác")
    
    st.sidebar.markdown("---")
    
    # Session history
    st.sidebar.subheader("📋 Lịch sử Sessions")
    sessions = db_manager.get_all_sessions()
    
    if sessions:
        for session in sessions[:5]:  # Show last 5 sessions
            with st.sidebar.expander(f"📅 {format_datetime(session['created_at'])}"):
                st.write(f"**CV:** {session['total_cvs']}")
                st.write(f"**Đánh giá:** {session['total_evaluations']}")
                
                if st.button(f"Xem kết quả", key=f"view_{session['session_id']}"):
                    st.session_state.current_session_id = session['session_id']
                    # Convert list results from database to expected dictionary format
                    raw_results = db_manager.get_session_results(session['session_id'])
                    st.session_state.evaluation_results = convert_db_results_to_format(raw_results)
                    st.session_state.show_final_report = False
                    st.rerun()
    else:
        st.sidebar.info("Chưa có session nào")

def render_main_content():
    """Render main content area"""
    st.markdown("""
    <div class="main-header">
        <h1>🤖 CV Evaluator AI</h1>
        <p>Gemini OCR → GPT-3.5-turbo → GPT Streaming Report</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show performance improvement notice
    st.info("""
    🚀 **Cải tiến hiệu suất**: Hệ thống đã được nâng cấp sử dụng GPT-3.5-turbo thay vì Vietnamese LLaMA để:
    - ⚡ Tăng tốc độ xử lý gấp 10 lần
    - 🎯 Cải thiện độ chính xác đánh giá
    - 📊 Phân tích JSON ổn định hơn
    - 💰 Giảm chi phí vận hành
    """)
    
    # Check if we have a current session
    if not st.session_state.current_session_id:
        st.info("👈 Vui lòng tạo session mới từ sidebar để bắt đầu")
        return
    
    # Show results if available
    if st.session_state.evaluation_results:
        if st.session_state.show_final_report:
            render_final_report()
        else:
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
            placeholder="""Ví dụ:
Tuyển dụng Python Developer
- Có kinh nghiệm từ 2 năm trở lên
- Thành thạo Python, Django/Flask
- Kinh nghiệm với database (PostgreSQL, MySQL)
- Hiểu biết về Docker, AWS
- Có khả năng làm việc nhóm tốt"""
        )
    
    with col2:
        required_candidates = st.number_input(
            "👥 Số lượng cần tuyển",
            min_value=1,
            max_value=20,
            value=3
        )
        
        st.markdown("### 📊 Session Info")
        st.info(f"ID: {st.session_state.current_session_id[:8]}...")
        
        # Show AI model being used
        st.markdown("### 🤖 AI Model")
        st.success("GPT-3.5-turbo")
    
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
            
            # Performance estimate
            estimated_time = len(valid_files) * 15  # 15 seconds per file with GPT
            st.info(f"⏱️ Thời gian ước tính: ~{estimated_time} giây (GPT-3.5-turbo)")
            
            # Start evaluation button
            if st.button("🚀 Bắt đầu đánh giá", type="primary"):
                if not job_description.strip():
                    st.error("❌ Vui lòng nhập mô tả công việc")
                    return
                
                start_evaluation(job_description, required_candidates, valid_files)

def start_evaluation(job_description: str, required_candidates: int, uploaded_files: List):
    """Start the evaluation process with step-by-step display"""
    # Setup directories
    setup_directories()
    
    # Progress tracking
    progress_container = st.container()
    
    with progress_container:
        st.subheader("🔄 Đang xử lý...")
        
        # Step 1: Save files
        step1_placeholder = st.empty()
        step1_placeholder.info("📁 Đang lưu file...")
        
        saved_files = []
        try:
            for i, file in enumerate(uploaded_files):
                file_path = save_uploaded_file(file)
                file_info = get_file_info(file, file_path)
                saved_files.append(file_info)
                step1_placeholder.info(f"📁 Đã lưu {i+1}/{len(uploaded_files)} file")
            
            step1_placeholder.success("✅ Đã lưu tất cả file")
            
        except Exception as e:
            step1_placeholder.error(f"❌ Lỗi lưu file: {str(e)}")
            return
        
        # Step 2: Run workflow
        step2_placeholder = st.empty()
        step2_placeholder.info("🤖 Đang chạy workflow với GPT-3.5-turbo...")
        
        try:
            # Show progress bar
            progress_bar = st.progress(0)
            
            # Run evaluation
            result = cv_workflow.run_evaluation(
                st.session_state.current_session_id,
                job_description,
                required_candidates,
                saved_files
            )
            
            progress_bar.progress(100)
            
            if result["success"]:
                step2_placeholder.success("✅ Đánh giá hoàn thành với GPT-3.5-turbo!")
                st.session_state.evaluation_results = result["results"]
                st.session_state.show_final_report = False
                time.sleep(1)
                st.rerun()
            else:
                step2_placeholder.error(f"❌ Lỗi workflow: {result['error']}")
                
        except Exception as e:
            step2_placeholder.error(f"❌ Lỗi: {str(e)}")

def render_evaluation_results():
    """Render evaluation results"""
    results = st.session_state.evaluation_results
    
    # Validate results format
    if not results:
        st.error("❌ Không có kết quả đánh giá")
        return
    
    # Handle case where results might be a list (from old database format)
    if isinstance(results, list):
        results = convert_db_results_to_format(results)
        st.session_state.evaluation_results = results
    
    # Ensure results is a dictionary with required keys
    if not isinstance(results, dict):
        st.error("❌ Định dạng kết quả không hợp lệ")
        return
    
    st.subheader("📊 Kết quả đánh giá")
    
    # Show AI model used
    st.success("🤖 Đánh giá bằng GPT-3.5-turbo")
    
    # Summary metrics with safe access
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Tổng số CV", results.get("total_cvs", 0))
    
    with col2:
        st.metric("✅ Đạt yêu cầu", results.get("qualified_count", 0))
    
    with col3:
        st.metric("📊 Điểm TB", f"{results.get('average_score', 0):.1f}/10")
    
    with col4:
        qualification_rate = results.get("summary", {}).get("qualification_rate", 0)
        st.metric("📈 Tỷ lệ đạt", f"{qualification_rate}%")
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Xem báo cáo chi tiết GPT", type="primary"):
            st.session_state.show_final_report = True
            st.rerun()
    
    with col2:
        if st.button("🔄 Đánh giá mới"):
            st.session_state.evaluation_results = None
            st.session_state.show_final_report = False
            st.rerun()
    
    # Top candidates
    st.subheader("🏆 Top ứng viên")
    top_candidates = results.get("top_candidates", [])
    
    if top_candidates:
        for i, candidate in enumerate(top_candidates, 1):
            with st.expander(f"#{i} - {candidate.get('filename', 'Unknown')} {format_score(candidate.get('score', 0))}"):
                st.write(f"**Điểm số:** {candidate.get('score', 0):.1f}/10")
                st.write(f"**Trạng thái:** {get_pass_status_emoji(candidate.get('is_qualified', False))} {'Đạt yêu cầu' if candidate.get('is_qualified', False) else 'Không đạt yêu cầu'}")
                
                # Show evaluation details
                evaluation_text = candidate.get('evaluation_text', '')
                if evaluation_text:
                    try:
                        eval_data = json.loads(evaluation_text)
                        if isinstance(eval_data, dict):
                            
                            # Show criteria scores if available
                            criteria = eval_data.get('criteria_scores', {})
                            if criteria:
                                st.write("**Điểm chi tiết:**")
                                for criterion, score in criteria.items():
                                    st.write(f"- {criterion}: {score}/10")
                            
                            # Show strengths and weaknesses
                            strengths = eval_data.get('strengths', [])
                            if strengths:
                                st.write("**Điểm mạnh:**")
                                for strength in strengths:
                                    st.write(f"- ✅ {strength}")
                            
                            weaknesses = eval_data.get('weaknesses', [])
                            if weaknesses:
                                st.write("**Điểm yếu:**")
                                for weakness in weaknesses:
                                    st.write(f"- ❌ {weakness}")
                            
                            summary = eval_data.get('summary', '')
                            if summary:
                                st.write(f"**Tóm tắt:** {summary}")
                                
                    except json.JSONDecodeError:
                        st.write("**Đánh giá:**")
                        st.write(evaluation_text)
                else:
                    st.write("Không có đánh giá chi tiết")
    else:
        st.info("Không có ứng viên nào để hiển thị")

def render_final_report():
    """Render final report with streaming GPT response"""
    st.subheader("📋 Báo cáo tổng hợp từ GPT-3.5-turbo")
    
    # Back button
    if st.button("← Quay lại kết quả", type="secondary"):
        st.session_state.show_final_report = False
        st.rerun()
    
    # Get job description from database
    session_info = db_manager.get_session(st.session_state.current_session_id)
    if not session_info:
        st.error("Không tìm thấy thông tin session")
        return
    
    job_description = session_info['job_description']
    results = st.session_state.evaluation_results
    
    # Show AI model info
    st.info("🤖 Báo cáo được tạo bởi GPT-3.5-turbo với streaming response")
    
    # Show streaming response
    st.markdown("### 📊 Báo cáo chuyên gia:")
    
    report_container = st.empty()
    
    # Generate streaming response
    with st.spinner("Đang tạo báo cáo với GPT-3.5-turbo..."):
        full_response = ""
        
        try:
            for chunk in cv_workflow.generate_final_response_stream(results, job_description):
                full_response += chunk
                # Update the display with accumulated response
                report_container.markdown(f"""
                <div class="streaming-container">
                    {full_response}
                </div>
                """, unsafe_allow_html=True)
                time.sleep(0.03)  # Small delay for smooth streaming effect
            
            # Final formatted display
            report_container.markdown(full_response)
            
        except Exception as e:
            report_container.error(f"Lỗi tạo báo cáo: {str(e)}")

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
        "🚀 CV Evaluator AI - Gemini OCR + GPT-3.5-turbo + GPT Streaming<br>"
        "Nâng cấp từ Vietnamese LLaMA để tăng hiệu suất và độ chính xác"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()