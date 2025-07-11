import os
import smtplib
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    smtp_server: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email: str = os.getenv("SMTP_EMAIL", os.getenv("SMTP_USER", ""))
    password: str = os.getenv("SMTP_PASSWORD", os.getenv("SMTP_PASS", ""))
    company_name: str = os.getenv("COMPANY_NAME", "Công ty ABC")
    company_email: str = os.getenv("COMPANY_EMAIL", os.getenv("SMTP_USER", "hr@company.com"))

class EmailService:
    def __init__(self):
        self.config = EmailConfig()
        self.validate_config()
        
    def validate_config(self):
        """Xác thực cấu hình email"""
        if not self.config.email or not self.config.password:
            logger.warning("Thông tin đăng nhập email chưa được cấu hình. Tính năng email sẽ bị vô hiệu hóa.")
            return False
        return True
    
    def extract_email_from_cv_text(self, cv_text: str) -> Optional[str]:
        """Trích xuất email từ văn bản CV sử dụng regex"""
        try:
            # Pattern regex email nâng cao
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, cv_text)
            
            if emails:
                # Trả về email hợp lệ đầu tiên được tìm thấy
                for email in emails:
                    if self._is_valid_email(email):
                        return email.lower()
            
            return None
        except Exception as e:
            logger.error(f"Lỗi trích xuất email từ CV: {e}")
            return None
    
    def _is_valid_email(self, email: str) -> bool:
        """Xác thực định dạng email"""
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return re.match(pattern, email) is not None
    
    def create_interview_invitation_email(self, candidate_name: str, position: str, 
                                        interview_date: str, cv_score: float) -> tuple:
        """Tạo email mời phỏng vấn bằng tiếng Việt"""
        subject = f"Thư mời phỏng vấn vị trí {position} - {self.config.company_name}"
        
        body = f"""
        Kính chào {candidate_name},

        Chúng tôi đã xem xét hồ sơ ứng tuyển của bạn và rất ấn tượng với kinh nghiệm cũng như kỹ năng mà bạn thể hiện trong CV.
        
        📊 Kết quả đánh giá CV: {cv_score:.1f}/10 điểm
        
        Với niềm vui, chúng tôi xin được mời bạn tham gia buổi phỏng vấn cho vị trí {position} tại {self.config.company_name}.
        
        📅 Thời gian dự kiến phỏng vấn: {interview_date}
        📍 Địa điểm: Sẽ được thông báo chi tiết sau khi bạn xác nhận
        ⏰ Thời lượng: Khoảng 60-90 phút
        
        🔄 CÁCH THỨC PHỎNG VẤN:
        - Phỏng vấn trực tiếp hoặc online (sẽ thông báo cụ thể)
        - Bao gồm: Phỏng vấn kỹ thuật + Phỏng vấn HR
        - Mang theo: CV gốc, bằng cấp, chứng chỉ liên quan
        
        📋 CHUẨN BỊ:
        - Tìm hiểu về công ty và vị trí ứng tuyển
        - Chuẩn bị câu trả lời cho các câu hỏi về kinh nghiệm làm việc
        - Chuẩn bị câu hỏi muốn tìm hiểu về công ty/vị trí
        
        Vui lòng phản hồi email này trước ngày {(datetime.now() + timedelta(days=3)).strftime('%d/%m/%Y')} để xác nhận tham gia phỏng vấn. Nếu thời gian không phù hợp, xin vui lòng đề xuất thời gian khác.
        
        Nếu có bất kỳ câu hỏi nào, đừng ngần ngại liên hệ với chúng tôi qua:
        📧 Email: {self.config.company_email}
        📞 Hotline: [Số điện thoại của công ty]
        
        Chúng tôi rất mong được gặp bạn!
        
        Trân trọng,
        Phòng Nhân sự
        {self.config.company_name}
        
        ---
        💡 Lưu ý: Đây là email tự động được gửi từ Hệ thống Đánh giá CV AI.
        Nếu bạn nhận nhầm email này, vui lòng bỏ qua hoặc thông báo cho chúng tôi.
        """
        
        return subject, body
    
    def create_rejection_email(self, candidate_name: str, position: str, cv_score: float) -> tuple:
        """Tạo email từ chối bằng tiếng Việt"""
        subject = f"Kết quả ứng tuyển vị trí {position} - {self.config.company_name}"
        
        body = f"""
        Kính chào {candidate_name},

        Trước tiên, chúng tôi xin chân thành cảm ơn bạn đã dành thời gian quan tâm và ứng tuyển vào vị trí {position} tại {self.config.company_name}.
        
        Chúng tôi đã xem xét kỹ lưỡng hồ sơ của bạn và đánh giá cao sự nhiệt huyết cũng như nỗ lực mà bạn đã thể hiện trong quá trình ứng tuyển.
        
        📊 Kết quả đánh giá CV: {cv_score:.1f}/10 điểm
        
        Tuy nhiên, sau khi cân nhắc cẩn thận và so sánh với các ứng viên khác, chúng tôi quyết định không thể tiếp tục với hồ sơ của bạn cho vị trí này lần này do:
        
        🔍 PHÂN TÍCH:
        - Hồ sơ của bạn chưa phù hợp hoàn toàn với yêu cầu cụ thể của vị trí hiện tại
        - Chúng tôi đang tìm kiếm ứng viên có kinh nghiệm/kỹ năng chuyên biệt hơn cho vai trò này
        - Số lượng ứng viên chất lượng cao vượt quá số vị trí tuyển dụng
        
        💼 GỢI Ý PHÁT TRIỂN:
        - Tiếp tục nâng cao kỹ năng chuyên môn trong lĩnh vực bạn quan tâm
        - Tích lũy thêm kinh nghiệm thực tế qua các dự án/công việc liên quan
        - Cập nhật CV với những thành tựu và kỹ năng mới nhất
        
        🌟 CƠHỘI TƯƠNG LAI:
        Chúng tôi sẽ lưu giữ thông tin của bạn trong hệ thống và sẽ liên hệ khi có cơ hội phù hợp hơn với kinh nghiệm của bạn trong tương lai.
        
        Bạn cũng có thể theo dõi trang tuyển dụng của chúng tôi để cập nhật các vị trí mở mới:
        🌐 Website: [Website công ty]
        📱 LinkedIn: [LinkedIn công ty]
        
        Một lần nữa, chúng tôi xin cảm ơn sự quan tâm của bạn và chúc bạn thành công trong việc tìm kiếm cơ hội nghề nghiệp phù hợp.
        
        Trân trọng,
        Phòng Nhân sự
        {self.config.company_name}
        Email: {self.config.company_email}
        
        ---
        💡 Lưu ý: Đây là email tự động được gửi từ Hệ thống Đánh giá CV AI.
        """
        
        return subject, body
    
    def create_follow_up_email(self, candidate_name: str, position: str, status: str) -> tuple:
        """Tạo email theo dõi bằng tiếng Việt"""
        subject = f"Cập nhật tiến trình ứng tuyển vị trí {position} - {self.config.company_name}"
        
        if status == "under_review":
            body = f"""
            Kính chào {candidate_name},
            
            Chúng tôi xin thông báo về tình trạng hồ sơ ứng tuyển của bạn cho vị trí {position}.
            
            📋 TÌNH TRẠNG HIỆN TẠI: Đang xem xét
            
            Hồ sơ của bạn hiện đang được xem xét bởi đội ngũ tuyển dụng. Chúng tôi dự kiến sẽ có kết quả trong vòng 5-7 ngày làm việc tới.
            
            Chúng tôi sẽ liên hệ với bạn ngay khi có kết quả cụ thể.
            
            Cảm ơn sự kiên nhẫn của bạn!
            
            Trân trọng,
            Phòng Nhân sự - {self.config.company_name}
            """
        elif status == "next_round":
            body = f"""
            Kính chào {candidate_name},
            
            Chúc mừng! Bạn đã vượt qua vòng đánh giá CV và được mời tham gia vòng tiếp theo.
            
            🎉 CHÚC MỪNG: Vượt qua vòng sơ tuyển
            📅 VÒNG TIẾP THEO: Sẽ được thông báo chi tiết trong email riêng
            
            Chúng tôi sẽ gửi thông tin chi tiết về vòng tiếp theo trong email khác.
            
            Trân trọng,
            Phòng Nhân sự - {self.config.company_name}
            """
        else:
            body = f"""
            Kính chào {candidate_name},
            
            Cảm ơn bạn đã ứng tuyển vị trí {position} tại {self.config.company_name}.
            
            Chúng tôi sẽ cập nhật thông tin về tiến trình tuyển dụng sớm nhất có thể.
            
            Trân trọng,
            Phòng Nhân sự - {self.config.company_name}
            """
        
        return subject, body
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Gửi email"""
        try:
            if not self.validate_config():
                logger.error("Cấu hình email không hợp lệ")
                return False
            
            # Tạo thông điệp
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.config.company_name} <{self.config.email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Reply-To'] = self.config.company_email
            
            # Thêm nội dung
            text_part = MIMEText(body, 'plain', 'utf-8')
            
            # Tạo phiên bản HTML đơn giản
            html_body = body.replace('\n', '<br>\n')
            html_body = f"""
            <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                        .content {{ padding: 20px; }}
                        .footer {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-top: 20px; font-size: 0.9em; }}
                    </style>
                </head>
                <body>
                    <div class="content">
                        {html_body}
                    </div>
                </body>
            </html>
            """
            
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Gửi email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email, self.config.password)
                text = msg.as_string()
                server.sendmail(self.config.email, to_email, text)
            
            logger.info(f"Email đã gửi thành công đến {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi gửi email đến {to_email}: {e}")
            return False
    
    def schedule_interview_emails(self, qualified_candidates: List[Dict], position: str):
        """Lên lịch email mời phỏng vấn sau 2 tuần"""
        try:
            # Tính ngày phỏng vấn (2 tuần từ bây giờ)
            interview_date = (datetime.now() + timedelta(weeks=2)).strftime("%d/%m/%Y")
            
            def send_delayed_emails():
                # Trong production, bạn sẽ sử dụng task queue thích hợp như Celery
                # Để demo, chúng ta sẽ gửi ngay nhưng log lịch trình
                for candidate in qualified_candidates:
                    cv_text = candidate.get('extracted_text', '')
                    email = self.extract_email_from_cv_text(cv_text)
                    
                    if email:
                        candidate_name = self._extract_name_from_cv(cv_text)
                        subject, body = self.create_interview_invitation_email(
                            candidate_name, position, interview_date, candidate['score']
                        )
                        
                        success = self.send_email(email, subject, body)
                        if success:
                            logger.info(f"Email mời phỏng vấn đã gửi đến {email}")
                        else:
                            logger.error(f"Gửi email mời phỏng vấn thất bại đến {email}")
                    else:
                        logger.warning(f"Không tìm thấy email trong CV: {candidate['filename']}")
            
            # Trong production, lên lịch điều này sau 2 tuần
            # Để demo, chúng ta sẽ chạy nó trong thread riêng ngay lập tức
            threading.Thread(target=send_delayed_emails, daemon=True).start()
            
            logger.info(f"Đã lên lịch email phỏng vấn cho {len(qualified_candidates)} ứng viên")
            
        except Exception as e:
            logger.error(f"Lỗi lên lịch email phỏng vấn: {e}")
    
    def send_rejection_emails(self, rejected_candidates: List[Dict], position: str):
        """Gửi email từ chối ngay lập tức"""
        try:
            def send_rejection_emails_async():
                for candidate in rejected_candidates:
                    cv_text = candidate.get('extracted_text', '')
                    email = self.extract_email_from_cv_text(cv_text)
                    
                    if email:
                        candidate_name = self._extract_name_from_cv(cv_text)
                        subject, body = self.create_rejection_email(
                            candidate_name, position, candidate['score']
                        )
                        
                        success = self.send_email(email, subject, body)
                        if success:
                            logger.info(f"Email từ chối đã gửi đến {email}")
                        else:
                            logger.error(f"Gửi email từ chối thất bại đến {email}")
                    else:
                        logger.warning(f"Không tìm thấy email trong CV: {candidate['filename']}")
            
            # Gửi email từ chối ở background
            threading.Thread(target=send_rejection_emails_async, daemon=True).start()
            
            logger.info(f"Đang gửi email từ chối cho {len(rejected_candidates)} ứng viên")
            
        except Exception as e:
            logger.error(f"Lỗi gửi email từ chối: {e}")
    
    def send_follow_up_emails(self, candidates: List[Dict], position: str, status: str):
        """Gửi email theo dõi"""
        try:
            def send_follow_up_emails_async():
                for candidate in candidates:
                    cv_text = candidate.get('extracted_text', '')
                    email = self.extract_email_from_cv_text(cv_text)
                    
                    if email:
                        candidate_name = self._extract_name_from_cv(cv_text)
                        subject, body = self.create_follow_up_email(
                            candidate_name, position, status
                        )
                        
                        success = self.send_email(email, subject, body)
                        if success:
                            logger.info(f"Email theo dõi đã gửi đến {email}")
                        else:
                            logger.error(f"Gửi email theo dõi thất bại đến {email}")
                    else:
                        logger.warning(f"Không tìm thấy email trong CV: {candidate['filename']}")
            
            threading.Thread(target=send_follow_up_emails_async, daemon=True).start()
            
            logger.info(f"Đang gửi email theo dõi cho {len(candidates)} ứng viên")
            
        except Exception as e:
            logger.error(f"Lỗi gửi email theo dõi: {e}")
    
    def _extract_name_from_cv(self, cv_text: str) -> str:
        """Trích xuất tên ứng viên từ văn bản CV"""
        try:
            # Trích xuất tên đơn giản - tìm kiếm các pattern phổ biến
            lines = cv_text.split('\n')
            
            # Kiểm tra vài dòng đầu cho pattern tên
            for i, line in enumerate(lines[:15]):  # Tăng lên 15 dòng để tìm tốt hơn
                line = line.strip()
                if line and len(line) < 60:  # Tên thường ngắn
                    # Bỏ qua các từ khóa CV phổ biến
                    skip_keywords = [
                        'cv', 'resume', 'curriculum', 'vitae', 'hồ sơ', 'thông tin', 'liên hệ', 'contact',
                        'email', 'phone', 'address', 'địa chỉ', 'điện thoại', 'sinh năm', 'born',
                        'experience', 'kinh nghiệm', 'education', 'học vấn', 'skills', 'kỹ năng',
                        'objective', 'mục tiêu', 'summary', 'tóm tắt', 'profile', 'giới thiệu'
                    ]
                    
                    # Kiểm tra xem dòng có chứa từ khóa cần bỏ qua không
                    line_lower = line.lower()
                    has_skip_keyword = any(keyword in line_lower for keyword in skip_keywords)
                    
                    if not has_skip_keyword:
                        # Kiểm tra xem có giống tên không (chỉ chứa chữ cái, khoảng trắng và một số ký tự tiếng Việt)
                        if re.match(r'^[a-zA-ZÀ-ỹĂăÂâĐđĨĩŨũƠơƯưÁáÀàẢảÃãẠạÂâẤấẦầẨẩẪẫẬậĂăẮắẰằẲẳẴẵẶặÉéÈèẺẻẼẽẸẹÊêẾếỀềỂểỄễỆệÍíÌìỈỉĨĩỊịÓóÒòỎỏÕõỌọÔôỐốỒồỔổỖỗỘộƠơỚớỜờỞởỠỡỢợÚúÙùỦủŨũỤụƯưỨứỪừỬửỮữỰựÝýỲỳỶỷỸỹỴỵ\s\.-]+$', line):
                            words = line.split()
                            # Tên thường có 2-4 từ
                            if 2 <= len(words) <= 4:
                                # Kiểm tra xem có phải số điện thoại hoặc email không
                                if not re.search(r'[\d@]', line):
                                    return line.title()
            
            # Nếu không tìm thấy tên, thử tìm trong format "Họ tên:" hoặc "Name:"
            for line in lines[:20]:
                line = line.strip()
                # Tìm pattern "Họ tên: Nguyễn Văn A"
                name_patterns = [
                    r'họ\s*tên\s*[:\-]\s*([a-zA-ZÀ-ỹĂăÂâĐđĨĩŨũƠơƯưÁáÀàẢảÃãẠạÂâẤấẦầẨẩẪẫẬậĂăẮắẰằẲẳẴẵẶặÉéÈèẺẻẼẽẸẹÊêẾếỀềỂểỄễỆệÍíÌìỈỉĨĩỊịÓóÒòỎỏÕõỌọÔôỐốỒồỔổỖỗỘộƠơỚớỜờỞởỠỡỢợÚúÙùỦủŨũỤụƯưỨứỪừỬửỮữỰựÝýỲỳỶỷỸỹỴỵ\s]+)',
                    r'name\s*[:\-]\s*([a-zA-ZÀ-ỹĂăÂâĐđĨĩŨũƠơƯưÁáÀàẢảÃãẠạÂâẤấẦầẨẩẪẫẬậĂăẮắẰằẲẳẴẵẶặÉéÈèẺẻẼẽẸẹÊêẾếỀềỂểỄễỆệÍíÌìỈỉĨĩỊịÓóÒòỎỏÕõỌọÔôỐốỒồỔổỖỗỘộƠơỚớỜờỞởỠỡỢợÚúÙùỦủŨũỤụƯưỨứỪừỬửỮữỰựÝýỲỳỶỷỸỹỴỵ\s]+)'
                ]
                
                for pattern in name_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        return match.group(1).strip().title()
            
            return "Ứng viên"  # Mặc định nếu không tìm thấy tên
            
        except Exception as e:
            logger.error(f"Lỗi trích xuất tên từ CV: {e}")
            return "Ứng viên"
    
    def test_email_connection(self) -> bool:
        """Kiểm tra kết nối máy chủ email"""
        try:
            if not self.validate_config():
                return False
                
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email, self.config.password)
                logger.info("Kiểm tra kết nối email thành công")
                return True
                
        except Exception as e:
            logger.error(f"Kiểm tra kết nối email thất bại: {e}")
            return False

    def send_test_email(self, to_email: str) -> bool:
        """Gửi email test"""
        try:
            subject = f"Email Test - Hệ thống Đánh giá CV AI"
            body = f"""
            Kính chào,
            
            Đây là email test từ Hệ thống Đánh giá CV AI của {self.config.company_name}.
            
            Nếu bạn nhận được email này, nghĩa là hệ thống email đang hoạt động bình thường.
            
            🎯 Hệ thống: CV Evaluator AI
            📅 Thời gian test: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            🏢 Công ty: {self.config.company_name}
            
            Trân trọng,
            Hệ thống Đánh giá CV AI
            """
            
            return self.send_email(to_email, subject, body)
            
        except Exception as e:
            logger.error(f"Lỗi gửi email test: {e}")
            return False

    def create_bulk_email_report(self, sent_results: List[Dict]) -> str:
        """Tạo báo cáo gửi email hàng loạt"""
        try:
            total = len(sent_results)
            successful = sum(1 for result in sent_results if result.get('success', False))
            failed = total - successful
            
            report = f"""
            📊 BÁO CÁO GỬI EMAIL HÀNG LOẠT
            
            📈 THỐNG KÊ TỔNG QUAN:
            - Tổng số email: {total}
            - Gửi thành công: {successful} ({(successful/total*100):.1f}%)
            - Gửi thất bại: {failed} ({(failed/total*100):.1f}%)
            
            📧 CHI TIẾT KẾT QUẢ:
            """
            
            for i, result in enumerate(sent_results, 1):
                status = "✅ Thành công" if result.get('success', False) else "❌ Thất bại"
                email = result.get('email', 'N/A')
                candidate = result.get('candidate_name', 'N/A')
                error = result.get('error', '')
                
                report += f"\n{i}. {candidate} ({email}) - {status}"
                if error:
                    report += f" - Lỗi: {error}"
            
            report += f"""
            
            ⏰ Thời gian tạo báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            🎯 Hệ thống: CV Evaluator AI
            """
            
            return report
            
        except Exception as e:
            logger.error(f"Lỗi tạo báo cáo email: {e}")
            return f"Lỗi tạo báo cáo: {str(e)}"

# Instance toàn cục
email_service = EmailService()