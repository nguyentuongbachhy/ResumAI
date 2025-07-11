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
        """Validate email configuration"""
        if not self.config.email or not self.config.password:
            logger.warning("Email credentials not configured. Email features will be disabled.")
            return False
        return True
    
    def extract_email_from_cv_text(self, cv_text: str) -> Optional[str]:
        """Extract email from CV text using regex"""
        try:
            # Enhanced email regex pattern
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, cv_text)
            
            if emails:
                # Return the first valid email found
                for email in emails:
                    if self._is_valid_email(email):
                        return email.lower()
            
            return None
        except Exception as e:
            logger.error(f"Error extracting email from CV: {e}")
            return None
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return re.match(pattern, email) is not None
    
    def create_interview_invitation_email(self, candidate_name: str, position: str, 
                                        interview_date: str, cv_score: float) -> tuple:
        """Create interview invitation email"""
        subject = f"Mời phỏng vấn vị trí {position} - {self.config.company_name}"
        
        body = f"""
        Kính chào {candidate_name},

        Chúng tôi đã xem xét hồ sơ của bạn và rất ấn tượng với kinh nghiệm cũng như kỹ năng của bạn.
        
        📊 Điểm đánh giá CV: {cv_score:.1f}/10
        
        Chúng tôi muốn mời bạn tham gia buổi phỏng vấn cho vị trí {position} tại {self.config.company_name}.
        
        📅 Thời gian dự kiến: {interview_date}
        📍 Địa điểm: Sẽ thông báo cụ thể sau
        
        Vui lòng phản hồi email này để xác nhận tham gia và chúng tôi sẽ gửi thông tin chi tiết về buổi phỏng vấn.
        
        Nếu có bất kỳ câu hỏi nào, vui lòng liên hệ với chúng tôi qua email này.
        
        Trân trọng,
        Phòng Nhân sự - {self.config.company_name}
        Email: {self.config.company_email}
        
        ---
        Đây là email tự động được gửi từ hệ thống CV Evaluator AI.
        """
        
        return subject, body
    
    def create_rejection_email(self, candidate_name: str, position: str, cv_score: float) -> tuple:
        """Create rejection email"""
        subject = f"Kết quả ứng tuyển vị trí {position} - {self.config.company_name}"
        
        body = f"""
        Kính chào {candidate_name},

        Cảm ơn bạn đã quan tâm và ứng tuyển vào vị trí {position} tại {self.config.company_name}.
        
        Chúng tôi đã xem xét kỹ lưỡng hồ sơ của bạn và đánh giá cao sự nhiệt huyết cũng như thời gian bạn đã dành cho việc ứng tuyển.
        
        📊 Điểm đánh giá CV: {cv_score:.1f}/10
        
        Tuy nhiên, sau khi cân nhắc, chúng tôi quyết định không thể tiếp tục với ứng viên này lần này do hồ sơ chưa phù hợp hoàn toàn với yêu cầu công việc hiện tại.
        
        Chúng tôi sẽ lưu giữ thông tin của bạn và sẽ liên hệ nếu có cơ hội phù hợp trong tương lai.
        
        Chúc bạn thành công trong việc tìm kiếm cơ hội nghề nghiệp khác.
        
        Trân trọng,
        Phòng Nhân sự - {self.config.company_name}
        Email: {self.config.company_email}
        
        ---
        Đây là email tự động được gửi từ hệ thống CV Evaluator AI.
        """
        
        return subject, body
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email"""
        try:
            if not self.validate_config():
                logger.error("Email configuration invalid")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email, self.config.password)
                text = msg.as_string()
                server.sendmail(self.config.email, to_email, text)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def schedule_interview_emails(self, qualified_candidates: List[Dict], position: str):
        """Schedule interview invitation emails for 2 weeks later"""
        try:
            # Calculate interview date (2 weeks from now)
            interview_date = (datetime.now() + timedelta(weeks=2)).strftime("%d/%m/%Y")
            
            def send_delayed_emails():
                # In production, you'd use a proper task queue like Celery
                # For demo, we'll send immediately but log the schedule
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
                            logger.info(f"Interview invitation sent to {email}")
                        else:
                            logger.error(f"Failed to send interview invitation to {email}")
                    else:
                        logger.warning(f"No email found in CV: {candidate['filename']}")
            
            # In production, schedule this for 2 weeks later
            # For demo, we'll run it in a separate thread immediately
            threading.Thread(target=send_delayed_emails, daemon=True).start()
            
            logger.info(f"Scheduled interview emails for {len(qualified_candidates)} candidates")
            
        except Exception as e:
            logger.error(f"Error scheduling interview emails: {e}")
    
    def send_rejection_emails(self, rejected_candidates: List[Dict], position: str):
        """Send rejection emails immediately"""
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
                            logger.info(f"Rejection email sent to {email}")
                        else:
                            logger.error(f"Failed to send rejection email to {email}")
                    else:
                        logger.warning(f"No email found in CV: {candidate['filename']}")
            
            # Send rejection emails in background
            threading.Thread(target=send_rejection_emails_async, daemon=True).start()
            
            logger.info(f"Sending rejection emails for {len(rejected_candidates)} candidates")
            
        except Exception as e:
            logger.error(f"Error sending rejection emails: {e}")
    
    def _extract_name_from_cv(self, cv_text: str) -> str:
        """Extract candidate name from CV text"""
        try:
            # Simple name extraction - look for common patterns
            lines = cv_text.split('\n')
            
            # Check first few lines for name patterns
            for i, line in enumerate(lines[:10]):
                line = line.strip()
                if line and len(line) < 50:  # Names are usually short
                    # Skip common CV keywords
                    skip_keywords = ['cv', 'resume', 'curriculum', 'vitae', 'hồ sơ', 'thông tin', 'liên hệ', 'contact']
                    if not any(keyword in line.lower() for keyword in skip_keywords):
                        # Check if it looks like a name (contains letters and spaces)
                        if re.match(r'^[a-zA-ZÀ-ỹ\s]+$', line) and len(line.split()) >= 2:
                            return line.title()
            
            return "Ứng viên"  # Default if name not found
            
        except Exception as e:
            logger.error(f"Error extracting name from CV: {e}")
            return "Ứng viên"
    
    def test_email_connection(self) -> bool:
        """Test email server connection"""
        try:
            if not self.validate_config():
                return False
                
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email, self.config.password)
                logger.info("Email connection test successful")
                return True
                
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False

# Global email service instance
email_service = EmailService()