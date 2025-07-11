import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "cv_evaluator.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Khởi tạo database với các bảng cần thiết"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Bảng sessions
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        job_description TEXT NOT NULL,
                        required_candidates INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Bảng CVs
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cvs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        extracted_info TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                ''')
                
                # Bảng evaluations
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS evaluations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        cv_id INTEGER NOT NULL,
                        score REAL NOT NULL,
                        evaluation_text TEXT NOT NULL,
                        is_passed BOOLEAN NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id),
                        FOREIGN KEY (cv_id) REFERENCES cvs (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Khởi tạo database thành công")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo database: {e}")
            raise
    
    def create_session(self, session_id: str, job_description: str, required_candidates: int) -> bool:
        """Tạo session đánh giá mới"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO sessions (session_id, job_description, required_candidates)
                    VALUES (?, ?, ?)
                ''', (session_id, job_description, required_candidates))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Lỗi tạo session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Lấy thông tin session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM sessions WHERE session_id = ?
                ''', (session_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'session_id': row[1],
                        'job_description': row[2],
                        'required_candidates': row[3],
                        'created_at': row[4],
                        'updated_at': row[5]
                    }
                return None
        except Exception as e:
            logger.error(f"Lỗi lấy session: {e}")
            return None
    
    def add_cv(self, session_id: str, filename: str, file_path: str, file_type: str, extracted_info: str = None) -> int:
        """Thêm CV vào database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO cvs (session_id, filename, file_path, file_type, extracted_info)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, filename, file_path, file_type, extracted_info))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Lỗi thêm CV: {e}")
            return -1
    
    def update_cv_info(self, cv_id: int, extracted_info: str) -> bool:
        """Cập nhật thông tin trích xuất CV"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE cvs SET extracted_info = ? WHERE id = ?
                ''', (extracted_info, cv_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Lỗi cập nhật thông tin CV: {e}")
            return False
    
    def add_evaluation(self, session_id: str, cv_id: int, score: float, evaluation_text: str, is_passed: bool) -> bool:
        """Thêm kết quả đánh giá"""
        try:
            # Đảm bảo các tham số có đúng kiểu dữ liệu
            session_id = str(session_id)
            cv_id = int(cv_id)
            score = float(score)
            evaluation_text = str(evaluation_text)
            is_passed = bool(is_passed)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO evaluations (session_id, cv_id, score, evaluation_text, is_passed)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, cv_id, score, evaluation_text, is_passed))
                conn.commit()
                logger.info(f"Đã thêm đánh giá cho CV {cv_id} với điểm {score}")
                return True
        except Exception as e:
            logger.error(f"Lỗi thêm đánh giá: {e}")
            logger.error(f"Parameters: session_id={session_id}, cv_id={cv_id}, score={score}, is_passed={is_passed}")
            return False
    
    def get_session_results(self, session_id: str) -> List[Dict]:
        """Lấy tất cả kết quả đánh giá cho một session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.filename, c.extracted_info, e.score, e.evaluation_text, e.is_passed, e.created_at
                    FROM cvs c
                    JOIN evaluations e ON c.id = e.cv_id
                    WHERE c.session_id = ?
                    ORDER BY e.score DESC
                ''', (session_id,))
                rows = cursor.fetchall()
                return [
                    {
                        'filename': row[0],
                        'extracted_info': row[1],
                        'score': float(row[2]),  # Đảm bảo score là float
                        'evaluation_text': row[3],
                        'is_passed': bool(row[4]),  # Đảm bảo is_passed là boolean
                        'created_at': row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Lỗi lấy kết quả session: {e}")
            return []
    
    def get_all_sessions(self) -> List[Dict]:
        """Lấy tất cả sessions với thống kê tóm tắt"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Sửa lỗi: Qualify column names để tránh ambiguity
                cursor.execute('''
                    SELECT s.session_id, s.job_description, s.required_candidates, s.created_at,
                           COUNT(DISTINCT c.id) as total_cvs,
                           COUNT(DISTINCT e.id) as total_evaluations
                    FROM sessions s
                    LEFT JOIN cvs c ON s.session_id = c.session_id
                    LEFT JOIN evaluations e ON s.session_id = e.session_id
                    GROUP BY s.session_id, s.job_description, s.required_candidates, s.created_at
                    ORDER BY s.created_at DESC
                ''')
                rows = cursor.fetchall()
                return [
                    {
                        'session_id': row[0],
                        'job_description': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                        'required_candidates': row[2],
                        'created_at': row[3],
                        'total_cvs': row[4],
                        'total_evaluations': row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Lỗi lấy tất cả sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Xóa session và tất cả dữ liệu liên quan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Xóa evaluations trước (foreign key constraint)
                cursor.execute('DELETE FROM evaluations WHERE session_id = ?', (session_id,))
                
                # Xóa CVs
                cursor.execute('DELETE FROM cvs WHERE session_id = ?', (session_id,))
                
                # Xóa session
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                
                conn.commit()
                logger.info(f"Đã xóa session {session_id} và tất cả dữ liệu liên quan")
                return True
        except Exception as e:
            logger.error(f"Lỗi xóa session: {e}")
            return False

    def get_database_stats(self) -> Dict:
        """Lấy thống kê database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Lấy tổng số
                cursor.execute('SELECT COUNT(*) FROM sessions')
                total_sessions = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM cvs')
                total_cvs = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM evaluations')
                total_evaluations = cursor.fetchone()[0]
                
                # Lấy điểm trung bình
                cursor.execute('SELECT AVG(score) FROM evaluations')
                avg_score = cursor.fetchone()[0] or 0
                
                return {
                    'total_sessions': total_sessions,
                    'total_cvs': total_cvs,
                    'total_evaluations': total_evaluations,
                    'average_score': round(float(avg_score), 2)
                }
        except Exception as e:
            logger.error(f"Lỗi lấy thống kê database: {e}")
            return {
                'total_sessions': 0,
                'total_cvs': 0,
                'total_evaluations': 0,
                'average_score': 0
            }

# Instance toàn cục
db_manager = DatabaseManager()