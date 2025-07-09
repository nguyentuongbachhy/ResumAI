import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any
import streamlit as st
import logging

logger = logging.getLogger(__name__)

def setup_directories():
    """Setup necessary directories"""
    directories = [
        os.getenv("CV_UPLOAD_DIR", "./uploads"),
        os.getenv("OUTPUT_DIR", "./outputs"),
        os.getenv("TEMP_DIR", "./temp")
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def save_uploaded_file(uploaded_file, upload_dir: str = None) -> str:
    """Save uploaded file and return path"""
    if upload_dir is None:
        upload_dir = os.getenv("CV_UPLOAD_DIR", "./uploads")
    
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    file_extension = Path(uploaded_file.name).suffix
    filename = f"{unique_id}_{uploaded_file.name}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def get_file_info(uploaded_file, file_path: str) -> Dict[str, Any]:
    """Get file information"""
    return {
        "filename": uploaded_file.name,
        "path": file_path,
        "type": uploaded_file.type,
        "size": uploaded_file.size
    }

def validate_file_type(file_type: str) -> bool:
    """Validate if file type is supported"""
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
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up {file_path}: {e}")

def generate_session_id() -> str:
    """Generate unique session ID"""
    return str(uuid.uuid4())

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def format_score(score: float) -> str:
    """Format score with appropriate styling"""
    if score >= 8:
        return f"🟢 {score:.1f}"
    elif score >= 6:
        return f"🟡 {score:.1f}"
    else:
        return f"🔴 {score:.1f}"

def get_pass_status_emoji(is_passed: bool) -> str:
    """Get emoji for pass/fail status"""
    return "✅" if is_passed else "❌"

def create_download_link(data: str, filename: str, text: str = "Download") -> str:
    """Create download link for data"""
    import base64
    
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'
    return href

def parse_job_requirements(job_description: str) -> Dict[str, List[str]]:
    """Parse job requirements from job description"""
    requirements = {
        "skills": [],
        "experience": [],
        "education": [],
        "languages": []
    }
    
    # Simple keyword-based parsing
    text = job_description.lower()
    
    # Common skill keywords
    skill_keywords = [
        "python", "java", "javascript", "react", "nodejs", "mysql", "postgresql",
        "docker", "kubernetes", "aws", "azure", "git", "html", "css", "php",
        "laravel", "django", "flask", "vue", "angular", "mongodb", "redis"
    ]
    
    for skill in skill_keywords:
        if skill in text:
            requirements["skills"].append(skill)
    
    # Experience keywords
    if "năm kinh nghiệm" in text or "years experience" in text:
        requirements["experience"].append("Có kinh nghiệm làm việc")
    
    # Education keywords
    if "đại học" in text or "university" in text or "bachelor" in text:
        requirements["education"].append("Tốt nghiệp đại học")
    
    # Language keywords
    if "tiếng anh" in text or "english" in text:
        requirements["languages"].append("Tiếng Anh")
    
    return requirements

def estimate_processing_time(num_files: int) -> str:
    """Estimate processing time based on number of files"""
    # Rough estimate: 30 seconds per file
    total_seconds = num_files * 30
    
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
    """Create progress callback function"""
    def update_progress(step_name: str):
        nonlocal current_step
        current_step += 1
        progress = current_step / total_steps
        progress_bar.progress(progress, text=f"Đang xử lý: {step_name}")
    
    return update_progress

def format_datetime(datetime_str: str) -> str:
    """Format datetime string for display"""
    from datetime import datetime
    
    try:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return datetime_str

def get_file_icon(file_type: str) -> str:
    """Get appropriate icon for file type"""
    if file_type == "application/pdf":
        return "📄"
    elif file_type.startswith("image/"):
        return "🖼️"
    else:
        return "📁"