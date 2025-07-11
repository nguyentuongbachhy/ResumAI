import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any
import streamlit as st
import logging

logger = logging.getLogger(__name__)

def setup_directories():
    """Thiết lập các thư mục cần thiết"""
    directories = [
        os.getenv("CV_UPLOAD_DIR", "./uploads"),
        os.getenv("OUTPUT_DIR", "./outputs"),
        os.getenv("TEMP_DIR", "./temp")
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def save_uploaded_file(uploaded_file, upload_dir: str = None) -> str:
    """Lưu file đã upload và trả về đường dẫn"""
    if upload_dir is None:
        upload_dir = os.getenv("CV_UPLOAD_DIR", "./uploads")
    
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    
    # Tạo tên file duy nhất
    unique_id = str(uuid.uuid4())
    file_extension = Path(uploaded_file.name).suffix
    filename = f"{unique_id}_{uploaded_file.name}"
    file_path = os.path.join(upload_dir, filename)
    
    # Lưu file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def get_file_info(uploaded_file, file_path: str) -> Dict[str, Any]:
    """Lấy thông tin file"""
    return {
        "filename": uploaded_file.name,
        "path": file_path,
        "type": uploaded_file.type,
        "size": uploaded_file.size
    }

def validate_file_type(file_type: str) -> bool:
    """Kiểm tra loại file có được hỗ trợ hay không"""
    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/jpg", 
        "image/png",
        "image/gif",
        "image/bmp",
        "image/tiff"
    ]
    return file_type in allowed_types

def format_file_size(size_bytes: int) -> str:
    """Định dạng kích thước file dễ đọc"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def cleanup_temp_files(file_paths: List[str]):
    """Dọn dẹp các file tạm thời"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Đã dọn dẹp file tạm: {file_path}")
        except Exception as e:
            logger.error(f"Lỗi dọn dẹp {file_path}: {e}")

def generate_session_id() -> str:
    """Tạo ID session duy nhất"""
    return str(uuid.uuid4())

def truncate_text(text: str, max_length: int = 100) -> str:
    """Cắt ngắn text đến độ dài chỉ định"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def format_score(score: float) -> str:
    """Định dạng điểm số với màu sắc phù hợp"""
    if score >= 8:
        return f"🟢 {score:.1f}"
    elif score >= 6:
        return f"🟡 {score:.1f}"
    else:
        return f"🔴 {score:.1f}"

def get_pass_status_emoji(is_passed: bool) -> str:
    """Lấy emoji cho trạng thái đạt/không đạt"""
    return "✅" if is_passed else "❌"

def create_download_link(data: str, filename: str, text: str = "Tải xuống") -> str:
    """Tạo link tải xuống cho dữ liệu"""
    import base64
    
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'
    return href

def parse_job_requirements(job_description: str) -> Dict[str, List[str]]:
    """Phân tích yêu cầu công việc từ mô tả công việc"""
    requirements = {
        "skills": [],
        "experience": [],
        "education": [],
        "languages": []
    }
    
    # Phân tích đơn giản dựa trên từ khóa
    text = job_description.lower()
    
    # Từ khóa kỹ năng phổ biến
    skill_keywords = [
        "python", "java", "javascript", "react", "nodejs", "mysql", "postgresql",
        "docker", "kubernetes", "aws", "azure", "git", "html", "css", "php",
        "laravel", "django", "flask", "vue", "angular", "mongodb", "redis",
        "machine learning", "ai", "data science", "blockchain", "devops"
    ]
    
    for skill in skill_keywords:
        if skill in text:
            requirements["skills"].append(skill)
    
    # Từ khóa kinh nghiệm
    if any(keyword in text for keyword in ["năm kinh nghiệm", "years experience", "kinh nghiệm"]):
        requirements["experience"].append("Có kinh nghiệm làm việc")
    
    # Từ khóa học vấn
    if any(keyword in text for keyword in ["đại học", "university", "bachelor", "thạc sĩ", "master"]):
        requirements["education"].append("Tốt nghiệp đại học")
    
    # Từ khóa ngôn ngữ
    if any(keyword in text for keyword in ["tiếng anh", "english", "ielts", "toeic"]):
        requirements["languages"].append("Tiếng Anh")
    
    return requirements

def estimate_processing_time(num_files: int) -> str:
    """Ước tính thời gian xử lý dựa trên số file"""
    # Ước tính thô: 15 giây mỗi file với GPT-3.5-turbo (nhanh hơn)
    total_seconds = num_files * 15
    
    if total_seconds < 60:
        return f"~{total_seconds} giây"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"~{minutes} phút"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"~{hours} giờ {minutes} phút"

def create_progress_callback(progress_bar, total_steps: int, current_step: int = 0):
    """Tạo hàm callback cho progress"""
    def update_progress(step_name: str):
        nonlocal current_step
        current_step += 1
        progress = current_step / total_steps
        progress_bar.progress(progress, text=f"Đang xử lý: {step_name}")
    
    return update_progress

def format_datetime(datetime_str: str) -> str:
    """Định dạng chuỗi datetime để hiển thị"""
    from datetime import datetime
    
    try:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return datetime_str

def get_file_icon(file_type: str) -> str:
    """Lấy icon phù hợp cho loại file"""
    if file_type == "application/pdf":
        return "📄"
    elif file_type.startswith("image/"):
        return "🖼️"
    else:
        return "📁"

def get_score_color(score: float) -> str:
    """Lấy màu sắc cho điểm số"""
    if score >= 8:
        return "green"
    elif score >= 6:
        return "orange"
    else:
        return "red"

def format_percentage(value: float) -> str:
    """Định dạng phần trăm"""
    return f"{value:.1f}%"

def get_qualification_status(is_qualified: bool) -> str:
    """Lấy trạng thái đạt/không đạt yêu cầu"""
    return "Đạt yêu cầu" if is_qualified else "Không đạt yêu cầu"

def create_summary_stats(results: List[Dict]) -> Dict:
    """Tạo thống kê tóm tắt từ kết quả"""
    if not results:
        return {
            "total": 0,
            "qualified": 0,
            "average_score": 0,
            "qualification_rate": 0,
            "highest_score": 0,
            "lowest_score": 0
        }
    
    total = len(results)
    qualified = sum(1 for r in results if r.get('is_qualified', False))
    scores = [r.get('score', 0) for r in results]
    
    return {
        "total": total,
        "qualified": qualified,
        "average_score": round(sum(scores) / total, 2),
        "qualification_rate": round(qualified / total * 100, 1),
        "highest_score": max(scores) if scores else 0,
        "lowest_score": min(scores) if scores else 0
    }

def validate_session_data(session_data: Dict) -> bool:
    """Kiểm tra tính hợp lệ của dữ liệu session"""
    required_fields = ['session_id', 'job_description', 'required_candidates']
    return all(field in session_data for field in required_fields)

def sanitize_filename(filename: str) -> str:
    """Làm sạch tên file để đảm bảo an toàn"""
    import re
    # Loại bỏ các ký tự không an toàn
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Giới hạn độ dài
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    return filename

def log_evaluation_metrics(session_id: str, metrics: Dict):
    """Ghi log các metrics đánh giá"""
    logger.info(f"Session {session_id} - Metrics: {metrics}")

def create_error_response(error_message: str) -> Dict:
    """Tạo phản hồi lỗi chuẩn"""
    return {
        "success": False,
        "error": error_message,
        "timestamp": str(uuid.uuid4())
    }