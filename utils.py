import os
import uuid
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
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
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
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
    
    # Từ khóa kỹ năng phổ biến (cập nhật cho tiếng Việt)
    skill_keywords = [
        "python", "java", "javascript", "react", "nodejs", "mysql", "postgresql",
        "docker", "kubernetes", "aws", "azure", "git", "html", "css", "php",
        "laravel", "django", "flask", "vue", "angular", "mongodb", "redis",
        "machine learning", "ai", "data science", "blockchain", "devops",
        "spring boot", "hibernate", "microservices", "restful api", "graphql",
        "typescript", "webpack", "babel", "sass", "less", "bootstrap",
        "tailwind", "figma", "photoshop", "illustrator", "sketch",
        "unity", "unreal engine", "android", "ios", "swift", "kotlin",
        "flutter", "react native", "xamarin", "firebase", "supabase",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "tableau", "power bi", "excel", "word", "powerpoint",
        "agile", "scrum", "kanban", "jira", "confluence", "trello"
    ]
    
    for skill in skill_keywords:
        if skill in text:
            requirements["skills"].append(skill)
    
    # Từ khóa kinh nghiệm (cập nhật cho tiếng Việt)
    experience_keywords = [
        "năm kinh nghiệm", "years experience", "kinh nghiệm", "experience",
        "làm việc", "work", "dự án", "project", "thực tập", "internship",
        "part-time", "full-time", "freelance", "tư vấn", "consulting"
    ]
    
    if any(keyword in text for keyword in experience_keywords):
        requirements["experience"].append("Có kinh nghiệm làm việc")
    
    # Từ khóa học vấn (cập nhật cho tiếng Việt)
    education_keywords = [
        "đại học", "university", "bachelor", "thạc sĩ", "master", "tiến sĩ", "phd",
        "cao đẳng", "college", "trung cấp", "diploma", "chứng chỉ", "certificate",
        "bằng cấp", "degree", "học vấn", "education", "tốt nghiệp", "graduate"
    ]
    
    if any(keyword in text for keyword in education_keywords):
        requirements["education"].append("Tốt nghiệp đại học trở lên")
    
    # Từ khóa ngôn ngữ (cập nhật cho tiếng Việt)
    language_keywords = [
        "tiếng anh", "english", "ielts", "toeic", "toefl", "chinese", "tiếng trung",
        "japanese", "tiếng nhật", "korean", "tiếng hàn", "french", "tiếng pháp",
        "german", "tiếng đức", "spanish", "tiếng tây ban nha", "multilingual",
        "bilingual", "đa ngôn ngữ", "song ngữ"
    ]
    
    if any(keyword in text for keyword in language_keywords):
        requirements["languages"].append("Tiếng Anh hoặc ngoại ngữ khác")
    
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
    """Định dạng chuỗi datetime để hiển thị theo định dạng Việt Nam"""
    from datetime import datetime
    
    try:
        # Xử lý các định dạng datetime khác nhau
        if 'T' in datetime_str:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        else:
            # Thử parse với định dạng phổ biến
            try:
                dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except:
                dt = datetime.strptime(datetime_str, "%Y-%m-%d")
        
        # Trả về định dạng Việt Nam
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return datetime_str

def get_file_icon(file_type: str) -> str:
    """Lấy icon phù hợp cho loại file"""
    if file_type == "application/pdf":
        return "📄"
    elif file_type.startswith("image/"):
        return "🖼️"
    elif file_type.startswith("text/"):
        return "📝"
    elif file_type.startswith("application/vnd.ms-excel") or file_type.startswith("application/vnd.openxmlformats-officedocument.spreadsheetml"):
        return "📊"
    elif file_type.startswith("application/msword") or file_type.startswith("application/vnd.openxmlformats-officedocument.wordprocessingml"):
        return "📄"
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

def get_qualification_status_emoji(is_qualified: bool) -> str:
    """Lấy emoji cho trạng thái đạt/không đạt yêu cầu"""
    return "✅ Đạt yêu cầu" if is_qualified else "❌ Không đạt yêu cầu"

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
    # Loại bỏ dấu tiếng Việt để tránh lỗi encoding
    vietnamese_chars = {
        'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a', 'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
        'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
        'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
        'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o', 'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
        'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u', 'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
        'đ': 'd',
        'À': 'A', 'Á': 'A', 'Ạ': 'A', 'Ả': 'A', 'Ã': 'A', 'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ậ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ặ': 'A', 'Ẳ': 'A', 'Ẵ': 'A',
        'È': 'E', 'É': 'E', 'Ẹ': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ệ': 'E', 'Ể': 'E', 'Ễ': 'E',
        'Ì': 'I', 'Í': 'I', 'Ị': 'I', 'Ỉ': 'I', 'Ĩ': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ọ': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ộ': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ợ': 'O', 'Ở': 'O', 'Ỡ': 'O',
        'Ù': 'U', 'Ú': 'U', 'Ụ': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ự': 'U', 'Ử': 'U', 'Ữ': 'U',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỵ': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y',
        'Đ': 'D'
    }
    
    for vietnamese, english in vietnamese_chars.items():
        filename = filename.replace(vietnamese, english)
    
    # Giới hạn độ dài
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
        
    return filename

def log_evaluation_metrics(session_id: str, metrics: Dict):
    """Ghi log các metrics đánh giá"""
    logger.info(f"Phiên {session_id} - Metrics: {metrics}")

def create_error_response(error_message: str) -> Dict:
    """Tạo phản hồi lỗi chuẩn"""
    return {
        "success": False,
        "error": error_message,
        "timestamp": str(uuid.uuid4())
    }

def create_success_response(data: Any, message: str = "Thành công") -> Dict:
    """Tạo phản hồi thành công chuẩn"""
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": str(uuid.uuid4())
    }

def validate_email(email: str) -> bool:
    """Kiểm tra định dạng email hợp lệ"""
    import re
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    return re.match(pattern, email) is not None

def generate_random_password(length: int = 12) -> str:
    """Tạo mật khẩu ngẫu nhiên"""
    import random
    import string
    
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

def calculate_cv_match_percentage(cv_skills: List[str], job_requirements: List[str]) -> float:
    """Tính phần trăm khớp giữa kỹ năng CV và yêu cầu công việc"""
    if not job_requirements:
        return 0.0
    
    cv_skills_lower = [skill.lower().strip() for skill in cv_skills]
    job_requirements_lower = [req.lower().strip() for req in job_requirements]
    
    matches = sum(1 for req in job_requirements_lower if any(req in skill or skill in req for skill in cv_skills_lower))
    
    return (matches / len(job_requirements)) * 100

def extract_years_of_experience(cv_text: str) -> int:
    """Trích xuất số năm kinh nghiệm từ CV"""
    import re
    
    # Các pattern để tìm năm kinh nghiệm
    patterns = [
        r'(\d+)\s*năm\s*kinh\s*nghiệm',
        r'(\d+)\s*years?\s*of?\s*experience',
        r'(\d+)\s*years?\s*experience',
        r'kinh\s*nghiệm\s*(\d+)\s*năm',
        r'experience\s*[:\-]\s*(\d+)\s*years?'
    ]
    
    years = []
    text_lower = cv_text.lower()
    
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        years.extend([int(match) for match in matches])
    
    # Trả về năm kinh nghiệm cao nhất tìm được
    return max(years) if years else 0

def format_currency_vnd(amount: float) -> str:
    """Định dạng tiền tệ VND"""
    if amount >= 1_000_000_000:
        return f"{amount/1_000_000_000:.1f} tỷ VND"
    elif amount >= 1_000_000:
        return f"{amount/1_000_000:.1f} triệu VND"
    else:
        return f"{amount:,.0f} VND"

def get_experience_level(years: int) -> str:
    """Xác định cấp độ kinh nghiệm"""
    if years == 0:
        return "Fresher/Mới tốt nghiệp"
    elif years <= 2:
        return "Junior (1-2 năm)"
    elif years <= 5:
        return "Middle (3-5 năm)"
    elif years <= 10:
        return "Senior (6-10 năm)"
    else:
        return "Expert (10+ năm)"

def create_evaluation_summary(evaluations: List[Dict]) -> Dict:
    """Tạo tóm tắt đánh giá toàn diện"""
    if not evaluations:
        return {
            "message": "Không có dữ liệu đánh giá",
            "stats": {}
        }
    
    stats = create_summary_stats(evaluations)
    
    # Phân tích thêm
    score_ranges = {
        "excellent": sum(1 for e in evaluations if e.get('score', 0) >= 9),
        "good": sum(1 for e in evaluations if 7 <= e.get('score', 0) < 9),
        "average": sum(1 for e in evaluations if 5 <= e.get('score', 0) < 7),
        "poor": sum(1 for e in evaluations if e.get('score', 0) < 5)
    }
    
    # Top skills từ các CV
    all_skills = []
    for eval in evaluations:
        eval_text = eval.get('evaluation_text', '')
        if eval_text:
            try:
                import json
                eval_data = json.loads(eval_text)
                if isinstance(eval_data, dict):
                    strengths = eval_data.get('Điểm mạnh', [])
                    all_skills.extend(strengths)
            except:
                pass
    
    # Đếm skill phổ biến
    from collections import Counter
    skill_counter = Counter(all_skills)
    popular_skills = skill_counter.most_common(10)
    
    return {
        "total_candidates": len(evaluations),
        "qualified_candidates": stats["qualified"],
        "qualification_rate": stats["qualification_rate"],
        "average_score": stats["average_score"],
        "score_distribution": score_ranges,
        "popular_skills": popular_skills,
        "recommendations": generate_hiring_recommendations(evaluations)
    }

def generate_hiring_recommendations(evaluations: List[Dict]) -> List[str]:
    """Tạo khuyến nghị tuyển dụng"""
    recommendations = []
    
    if not evaluations:
        return ["Không có dữ liệu để đưa ra khuyến nghị"]
    
    qualified = [e for e in evaluations if e.get('is_qualified', False)]
    total = len(evaluations)
    qualified_count = len(qualified)
    
    # Khuyến nghị dựa trên tỷ lệ đạt yêu cầu
    if qualified_count == 0:
        recommendations.extend([
            "Không có ứng viên nào đạt yêu cầu hiện tại",
            "Xem xét giảm bớt yêu cầu hoặc mở rộng phạm vi tìm kiếm",
            "Cần đào tạo thêm cho các ứng viên tiềm năng"
        ])
    elif qualified_count / total < 0.2:
        recommendations.extend([
            "Tỷ lệ ứng viên đạt yêu cầu thấp (<20%)",
            "Xem xét điều chỉnh tiêu chí tuyển dụng",
            "Tập trung phỏng vấn những ứng viên có điểm cao nhất"
        ])
    elif qualified_count / total > 0.5:
        recommendations.extend([
            "Có nhiều ứng viên chất lượng (>50% đạt yêu cầu)",
            "Có thể nâng cao tiêu chí để lọc tốt hơn",
            "Xem xét tuyển thêm cho các vị trí tương tự"
        ])
    
    # Khuyến nghị dựa trên điểm số
    scores = [e.get('score', 0) for e in evaluations]
    avg_score = sum(scores) / len(scores)
    
    if avg_score >= 7:
        recommendations.append("Chất lượng ứng viên tổng thể tốt, nên tuyển những người có điểm cao nhất")
    elif avg_score >= 5:
        recommendations.append("Chất lượng ứng viên trung bình, cần phỏng vấn kỹ để đánh giá thêm")
    else:
        recommendations.append("Chất lượng ứng viên chưa cao, cần mở rộng tìm kiếm hoặc đào tạo")
    
    return recommendations

def create_detailed_candidate_report(candidate_data: Dict) -> str:
    """Tạo báo cáo chi tiết cho từng ứng viên"""
    try:
        filename = candidate_data.get('filename', 'Ứng viên')
        score = candidate_data.get('score', 0)
        is_qualified = candidate_data.get('is_qualified', False)
        evaluation_text = candidate_data.get('evaluation_text', '')
        
        report = f"""
        📋 BÁO CÁO CHI TIẾT ỨNG VIÊN
        
        👤 Tên file CV: {filename}
        📊 Điểm tổng: {score:.1f}/10
        ✅ Trạng thái: {get_qualification_status_emoji(is_qualified)}
        
        """
        
        # Phân tích đánh giá nếu có
        if evaluation_text:
            try:
                import json
                eval_data = json.loads(evaluation_text)
                if isinstance(eval_data, dict):
                    report += f"""
        🎯 PHÂN TÍCH CHI TIẾT:
        
        📈 Điểm từng tiêu chí:
        - Phù hợp với công việc: {eval_data.get('Các tiêu chí', {}).get('Điểm phù hợp', 0)}/10
        - Kinh nghiệm: {eval_data.get('Các tiêu chí', {}).get('Điểm kinh nghiệm', 0)}/10
        - Kỹ năng: {eval_data.get('Các tiêu chí', {}).get('Điểm kĩ năng', 0)}/10
        - Học vấn: {eval_data.get('Các tiêu chí', {}).get('Điểm giáo dục', 0)}/10
        
        💪 Điểm mạnh:
        """
                    strengths = eval_data.get('Điểm mạnh', [])
                    for i, strength in enumerate(strengths, 1):
                        report += f"        {i}. {strength}\n"
                    
                    report += f"""
        ⚠️ Điểm cần cải thiện:
        """
                    weaknesses = eval_data.get('Điểm yếu', [])
                    for i, weakness in enumerate(weaknesses, 1):
                        report += f"        {i}. {weakness}\n"
                    
                    report += f"""
        📝 Tổng kết: {eval_data.get('Tổng kết', '')}
        """
            except:
                report += f"\n📄 Đánh giá: {evaluation_text[:500]}..."
        
        report += f"""
        
        ⏰ Thời gian tạo báo cáo: {format_datetime(str(uuid.uuid4()))}
        🎯 Hệ thống: CV Evaluator AI
        """
        
        return report
        
    except Exception as e:
        logger.error(f"Lỗi tạo báo cáo ứng viên: {e}")
        return f"Lỗi tạo báo cáo: {str(e)}"

def generate_session_title(position_title: str, job_description: str) -> str:
    """Tự động tạo title cho session dựa trên vị trí và mô tả công việc"""
    try:
        # Làm sạch position title
        clean_position = position_title.strip() if position_title else ""
        
        # Nếu có position title, sử dụng làm base
        if clean_position:
            base_title = clean_position
        else:
            # Trích xuất vị trí từ job description
            base_title = extract_position_from_jd(job_description)
        
        # Thêm timestamp để đảm bảo unique
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        
        # Tạo title cuối cùng
        if base_title:
            # Giới hạn độ dài position title
            if len(base_title) > 30:
                base_title = base_title[:27] + "..."
            session_title = f"{base_title} - {timestamp}"
        else:
            session_title = f"Tuyển dụng - {timestamp}"
        
        return session_title
        
    except Exception as e:
        logger.error(f"Lỗi tạo session title: {e}")
        # Fallback title
        return f"Phiên tuyển dụng - {datetime.now().strftime('%d/%m %H:%M')}"

def extract_position_from_jd(job_description: str) -> str:
    """Trích xuất tên vị trí từ mô tả công việc"""
    try:
        if not job_description:
            return ""
        
        text = job_description.lower()
        
        # Các pattern để tìm vị trí
        position_patterns = [
            r'vị\s*trí[:\s]+([^.\n]+)',
            r'position[:\s]+([^.\n]+)',
            r'tuyển\s*dụng[:\s]+([^.\n]+)',
            r'hiring[:\s]+([^.\n]+)',
            r'cần\s*tìm[:\s]+([^.\n]+)',
            r'tìm\s*kiếm[:\s]+([^.\n]+)',
        ]
        
        for pattern in position_patterns:
            match = re.search(pattern, text)
            if match:
                position = match.group(1).strip()
                # Làm sạch và chuẩn hóa
                position = re.sub(r'[^\w\s\-]+', '', position)
                if len(position) > 5 and len(position) < 50:
                    return position.title()
        
        # Nếu không tìm thấy pattern, tìm keywords phổ biến
        common_positions = [
            'developer', 'lập trình viên', 'programmer', 'engineer', 'kỹ sư',
            'designer', 'thiết kế', 'manager', 'quản lý', 'leader', 'trưởng',
            'analyst', 'phân tích', 'tester', 'qa', 'kiểm thử',
            'marketer', 'marketing', 'sales', 'bán hàng', 'hr', 'nhân sự',
            'accountant', 'kế toán', 'finance', 'tài chính',
            'product owner', 'scrum master', 'devops', 'fullstack',
            'frontend', 'backend', 'mobile', 'web', 'ai', 'data'
        ]
        
        for position in common_positions:
            if position in text:
                return position.title()
        
        # Nếu vẫn không tìm thấy, trả về empty
        return ""
        
    except Exception as e:
        logger.error(f"Lỗi trích xuất vị trí từ JD: {e}")
        return ""

def generate_smart_session_title(position_title: str, job_description: str, required_candidates: int) -> str:
    """Tạo title thông minh hơn với thêm thông tin"""
    try:
        # Lấy base title
        base_title = generate_session_title(position_title, job_description)
        
        # Thêm thông tin số lượng tuyển dụng
        if required_candidates > 1:
            base_title = f"{base_title} ({required_candidates} người)"
        
        # Thêm keywords nổi bật từ JD
        keywords = extract_key_skills_from_jd(job_description)
        if keywords:
            # Chỉ lấy 2 keywords đầu và giới hạn độ dài
            key_skills = " | ".join(keywords[:2])
            if len(key_skills) < 20:
                base_title = f"{base_title} | {key_skills}"
        
        return base_title
        
    except Exception as e:
        logger.error(f"Lỗi tạo smart session title: {e}")
        return generate_session_title(position_title, job_description)

def extract_key_skills_from_jd(job_description: str) -> List[str]:
    """Trích xuất kỹ năng chính từ JD"""
    try:
        if not job_description:
            return []
        
        text = job_description.lower()
        
        # Kỹ năng tech phổ biến
        tech_skills = [
            'python', 'java', 'javascript', 'react', 'nodejs', 'php',
            'mysql', 'postgresql', 'mongodb', 'docker', 'kubernetes',
            'aws', 'azure', 'git', 'agile', 'scrum', 'devops',
            'html', 'css', 'vue', 'angular', 'laravel', 'django',
            'machine learning', 'ai', 'data science', 'blockchain',
            'flutter', 'react native', 'ios', 'android', 'unity'
        ]
        
        # Kỹ năng soft
        soft_skills = [
            'leadership', 'lãnh đạo', 'communication', 'giao tiếp',
            'teamwork', 'làm việc nhóm', 'problem solving', 'giải quyết vấn đề'
        ]
        
        found_skills = []
        
        # Tìm tech skills trước
        for skill in tech_skills:
            if skill in text and skill not in found_skills:
                found_skills.append(skill.title())
                if len(found_skills) >= 3:
                    break
        
        # Nếu không đủ tech skills, thêm soft skills
        if len(found_skills) < 2:
            for skill in soft_skills:
                if skill in text and skill not in found_skills:
                    found_skills.append(skill.title())
                    if len(found_skills) >= 2:
                        break
        
        return found_skills
        
    except Exception as e:
        logger.error(f"Lỗi trích xuất skills từ JD: {e}")
        return []

def format_session_title_for_display(session_title: str, max_length: int = 50) -> str:
    """Format session title để hiển thị trong UI"""
    try:
        if not session_title:
            return "Phiên không có tên"
        
        # Cắt ngắn nếu quá dài
        if len(session_title) > max_length:
            return session_title[:max_length-3] + "..."
        
        return session_title
        
    except Exception as e:
        logger.error(f"Lỗi format session title: {e}")
        return "Phiên tuyển dụng"

def get_session_display_name(session_data: dict) -> str:
    """Lấy tên hiển thị cho session"""
    try:
        # Ưu tiên session_title nếu có
        if session_data.get('session_title'):
            return format_session_title_for_display(session_data['session_title'])
        
        # Fallback: tạo từ position_title
        if session_data.get('position_title'):
            position = session_data['position_title']
            if len(position) > 30:
                position = position[:27] + "..."
            return f"{position} - {session_data.get('session_id', '')[:8]}"
        
        # Fallback cuối: session_id
        session_id = session_data.get('session_id', '')
        return f"Phiên {session_id[:8]}..." if session_id else "Phiên không xác định"
        
    except Exception as e:
        logger.error(f"Lỗi lấy session display name: {e}")
        return "Phiên tuyển dụng"

# Thêm validation cho session title
def validate_session_title(title: str) -> bool:
    """Kiểm tra tính hợp lệ của session title"""
    try:
        if not title or len(title.strip()) == 0:
            return False
        
        # Kiểm tra độ dài
        if len(title) > 100:
            return False
        
        # Kiểm tra ký tự đặc biệt nguy hiểm
        dangerous_chars = ['<', '>', '"', "'", '&', ';']
        if any(char in title for char in dangerous_chars):
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi validate session title: {e}")
        return False

def create_session_title_suggestions(job_description: str) -> List[str]:
    """Tạo gợi ý title cho session"""
    try:
        suggestions = []
        
        # Gợi ý 1: Từ position trong JD
        position = extract_position_from_jd(job_description)
        if position:
            suggestions.append(f"Tuyển {position}")
        
        # Gợi ý 2: Với skills chính
        skills = extract_key_skills_from_jd(job_description)
        if skills:
            suggestions.append(f"Tuyển {' & '.join(skills[:2])} Developer")
        
        # Gợi ý 3: Generic với timestamp
        timestamp = datetime.now().strftime("%d/%m")
        suggestions.append(f"Tuyển dụng {timestamp}")
        
        # Gợi ý 4: Theo level
        if any(word in job_description.lower() for word in ['senior', 'lead', 'principal', 'trưởng']):
            suggestions.append(f"Tuyển Senior Developer")
        elif any(word in job_description.lower() for word in ['junior', 'fresher', 'intern', 'mới']):
            suggestions.append(f"Tuyển Junior Developer")
        else:
            suggestions.append(f"Tuyển Developer")
        
        return suggestions[:3]  # Chỉ trả về 3 gợi ý đầu
        
    except Exception as e:
        logger.error(f"Lỗi tạo session title suggestions: {e}")
        return ["Tuyển dụng mới", "Phiên tuyển dụng", "Tìm ứng viên"]