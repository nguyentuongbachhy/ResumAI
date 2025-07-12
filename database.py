import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "cv_evaluator.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Khởi tạo database với schema mở rộng - SQLite Compatible"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Bảng sessions (updated)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        session_title TEXT DEFAULT '',
                        job_description TEXT NOT NULL,
                        position_title TEXT DEFAULT '',
                        required_candidates INTEGER NOT NULL,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP NULL
                    )
                ''')
                
                # Bảng files - Quản lý tất cả files được upload (Fixed)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        file_size INTEGER DEFAULT 0,
                        upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processing_status TEXT DEFAULT 'uploaded',
                        extracted_text TEXT NULL,
                        text_extraction_timestamp TIMESTAMP NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                ''')
                
                # Bảng chat_messages - Lưu trữ toàn bộ conversation (Fixed)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        message_type TEXT NOT NULL,
                        message_content TEXT NOT NULL,
                        sender TEXT DEFAULT 'system',
                        timestamp REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                ''')
                
                # Bảng evaluations (updated - Fixed)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS evaluations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        file_id INTEGER NULL,
                        cv_id INTEGER NULL,
                        score REAL NOT NULL,
                        evaluation_json TEXT NOT NULL,
                        evaluation_text TEXT NULL,
                        is_qualified BOOLEAN NOT NULL,
                        is_passed BOOLEAN NULL,
                        evaluation_model TEXT DEFAULT 'gpt-3.5-turbo',
                        evaluation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id),
                        FOREIGN KEY (file_id) REFERENCES files (id)
                    )
                ''')
                
                # Bảng email_logs - Theo dõi việc gửi email (Fixed)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS email_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        file_id INTEGER NULL,
                        email_type TEXT NOT NULL,
                        recipient_email TEXT NOT NULL,
                        email_subject TEXT NOT NULL,
                        email_body TEXT NOT NULL,
                        sent_status TEXT DEFAULT 'pending',
                        sent_timestamp TIMESTAMP NULL,
                        scheduled_timestamp TIMESTAMP NULL,
                        error_message TEXT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id),
                        FOREIGN KEY (file_id) REFERENCES files (id)
                    )
                ''')
                
                # Bảng session_analytics - Thống kê session (Fixed)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS session_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        total_files_uploaded INTEGER DEFAULT 0,
                        total_files_processed INTEGER DEFAULT 0,
                        total_evaluations INTEGER DEFAULT 0,
                        qualified_candidates INTEGER DEFAULT 0,
                        average_score REAL DEFAULT 0,
                        processing_time_seconds INTEGER DEFAULT 0,
                        total_chat_messages INTEGER DEFAULT 0,
                        last_activity_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                ''')
                
                # Tạo indexes riêng biệt (SQLite way)
                self._create_indexes(cursor)
                
                conn.commit()
                logger.info("Database schema created successfully")
                
                # Migrate existing data if needed
                self._migrate_existing_data()
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _create_indexes(self, cursor):
        """Tạo indexes riêng biệt cho tốc độ truy vấn"""
        try:
            indexes = [
                # Files table indexes
                "CREATE INDEX IF NOT EXISTS idx_files_session ON files (session_id)",
                "CREATE INDEX IF NOT EXISTS idx_files_status ON files (processing_status)",
                "CREATE INDEX IF NOT EXISTS idx_files_upload_time ON files (upload_timestamp)",
                
                # Chat messages indexes
                "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages (session_id)",
                "CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_messages (timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_chat_type ON chat_messages (message_type)",
                
                # Evaluations indexes
                "CREATE INDEX IF NOT EXISTS idx_eval_session ON evaluations (session_id)",
                "CREATE INDEX IF NOT EXISTS idx_eval_score ON evaluations (score)",
                "CREATE INDEX IF NOT EXISTS idx_eval_qualified ON evaluations (is_qualified)",
                "CREATE INDEX IF NOT EXISTS idx_eval_file ON evaluations (file_id)",
                
                # Email logs indexes
                "CREATE INDEX IF NOT EXISTS idx_email_session ON email_logs (session_id)",
                "CREATE INDEX IF NOT EXISTS idx_email_status ON email_logs (sent_status)",
                
                # Session analytics indexes
                "CREATE INDEX IF NOT EXISTS idx_analytics_session ON session_analytics (session_id)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_activity ON session_analytics (last_activity_timestamp)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Error creating indexes (non-critical): {e}")
    
    def _migrate_existing_data(self):
        """Migrate data từ schema cũ sang schema mới (Safe)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if old 'cvs' table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cvs'")
                if cursor.fetchone():
                    logger.info("Migrating data from old 'cvs' table to new 'files' table")
                    
                    # Migrate CVs to files table (Safe migration)
                    cursor.execute('''
                        INSERT OR IGNORE INTO files (session_id, filename, file_path, file_type, extracted_text, processing_status)
                        SELECT session_id, filename, file_path, file_type, 
                               extracted_info,
                               CASE 
                                   WHEN extracted_info IS NOT NULL AND extracted_info != '' THEN 'text_extracted'
                                   ELSE 'uploaded'
                               END
                        FROM cvs
                        WHERE NOT EXISTS (
                            SELECT 1 FROM files 
                            WHERE files.session_id = cvs.session_id 
                            AND files.filename = cvs.filename
                        )
                    ''')
                    
                    migrated_files = cursor.rowcount
                    logger.info(f"Migrated {migrated_files} files from cvs table")
                    
                    # Update evaluations to use file_id (Safe update)
                    cursor.execute('''
                        UPDATE evaluations 
                        SET file_id = (
                            SELECT f.id 
                            FROM files f
                            INNER JOIN cvs c ON f.session_id = c.session_id AND f.filename = c.filename
                            WHERE c.id = evaluations.cv_id
                            LIMIT 1
                        ),
                        evaluation_json = COALESCE(evaluation_text, '{}'),
                        is_qualified = COALESCE(is_passed, is_qualified, 0)
                        WHERE file_id IS NULL AND cv_id IS NOT NULL
                    ''')
                    
                    updated_evals = cursor.rowcount
                    logger.info(f"Updated {updated_evals} evaluations with file_id")
                    
                    conn.commit()
                    logger.info("Data migration completed successfully")
                
        except Exception as e:
            logger.warning(f"Data migration failed (this is normal for new installations): {e}")
    
    # === CHAT METHODS ===
    
    def save_chat_message(self, session_id: str, message_type: str, content: str, 
                         sender: str = 'system', metadata: Dict = None) -> bool:
        """Lưu tin nhắn chat vào database"""
        try:
            import time
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO chat_messages (session_id, message_type, message_content, sender, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session_id, 
                    message_type, 
                    content, 
                    sender, 
                    time.time(),
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
                
                # Update session analytics
                self._update_session_analytics(session_id, chat_messages_increment=1)
                
                return True
                
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            return False
    
    def get_chat_history(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Lấy lịch sử chat của session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT message_type, message_content, sender, timestamp, metadata, created_at
                    FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (session_id, limit))
                
                messages = []
                for row in cursor.fetchall():
                    metadata = json.loads(row[4]) if row[4] else {}
                    messages.append({
                        'type': row[0],
                        'message': row[1],
                        'sender': row[2],
                        'timestamp': row[3],
                        'metadata': metadata,
                        'created_at': row[5]
                    })
                
                return messages
                
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
    
    def clear_chat_history(self, session_id: str) -> bool:
        """Xóa lịch sử chat của session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
                conn.commit()
                
                # Reset chat count in analytics
                self._update_session_analytics(session_id, reset_chat_count=True)
                
                return True
                
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return False
    
    # === FILE METHODS ===
    
    def add_file(self, session_id: str, filename: str, file_path: str, 
                file_type: str, file_size: int = 0) -> int:
        """Thêm file vào database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO files (session_id, filename, file_path, file_type, file_size)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, filename, file_path, file_type, file_size))
                conn.commit()
                
                file_id = cursor.lastrowid
                
                # Update session analytics
                self._update_session_analytics(session_id, files_uploaded_increment=1)
                
                return file_id
                
        except Exception as e:
            logger.error(f"Error adding file: {e}")
            return -1
    
    def update_file_extraction(self, file_id: int, extracted_text: str) -> bool:
        """Cập nhật text đã trích xuất cho file"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE files 
                    SET extracted_text = ?, 
                        text_extraction_timestamp = CURRENT_TIMESTAMP,
                        processing_status = 'text_extracted'
                    WHERE id = ?
                ''', (extracted_text, file_id))
                conn.commit()
                
                # Get session_id to update analytics
                cursor.execute('SELECT session_id FROM files WHERE id = ?', (file_id,))
                result = cursor.fetchone()
                if result:
                    self._update_session_analytics(result[0], files_processed_increment=1)
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating file extraction: {e}")
            return False
    
    def get_session_files(self, session_id: str) -> List[Dict]:
        """Lấy danh sách files của session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, filename, file_path, file_type, file_size, 
                           processing_status, upload_timestamp, extracted_text
                    FROM files
                    WHERE session_id = ?
                    ORDER BY upload_timestamp ASC
                ''', (session_id,))
                
                files = []
                for row in cursor.fetchall():
                    files.append({
                        'id': row[0],
                        'filename': row[1],
                        'file_path': row[2],
                        'file_type': row[3],
                        'file_size': row[4],
                        'processing_status': row[5],
                        'upload_timestamp': row[6],
                        'extracted_text': row[7]
                    })
                
                return files
                
        except Exception as e:
            logger.error(f"Error getting session files: {e}")
            return []
    
    # === EVALUATION METHODS (Updated & Compatible) ===
    
    def add_evaluation(self, session_id: str, file_id: int, score: float, 
                      evaluation_json: str, is_qualified: bool, model: str = 'gpt-3.5-turbo') -> bool:
        """Thêm kết quả đánh giá (Compatible với cả cv_id và file_id)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if we're passing cv_id instead of file_id (backward compatibility)
                if isinstance(file_id, int) and file_id > 0:
                    cursor.execute('''
                        INSERT INTO evaluations (session_id, file_id, score, evaluation_json, evaluation_text, is_qualified, is_passed, evaluation_model)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (session_id, file_id, score, evaluation_json, evaluation_json, is_qualified, is_qualified, model))
                else:
                    # Old cv_id format
                    cursor.execute('''
                        INSERT INTO evaluations (session_id, cv_id, score, evaluation_text, is_passed, evaluation_model)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (session_id, file_id, score, evaluation_json, is_qualified, model))
                
                conn.commit()
                
                # Update session analytics
                qualified_increment = 1 if is_qualified else 0
                self._update_session_analytics(
                    session_id, 
                    evaluations_increment=1,
                    qualified_increment=qualified_increment,
                    score_update=score
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error adding evaluation: {e}")
            return False
    
    def get_session_results(self, session_id: str) -> List[Dict]:
        """Lấy kết quả đánh giá của session (Compatible)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Try new schema first
                cursor.execute('''
                    SELECT f.filename, f.file_path, f.extracted_text, 
                           e.score, e.evaluation_json, e.is_qualified, 
                           e.evaluation_timestamp, e.evaluation_model
                    FROM files f
                    JOIN evaluations e ON f.id = e.file_id
                    WHERE f.session_id = ?
                    ORDER BY e.score DESC
                ''', (session_id,))
                
                results = cursor.fetchall()
                
                # If no results and old cvs table exists, try old schema
                if not results:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cvs'")
                    if cursor.fetchone():
                        cursor.execute('''
                            SELECT c.filename, c.file_path, c.extracted_info, 
                                   e.score, e.evaluation_text, e.is_passed, 
                                   e.created_at, 'gpt-3.5-turbo'
                            FROM cvs c
                            JOIN evaluations e ON c.id = e.cv_id
                            WHERE c.session_id = ?
                            ORDER BY e.score DESC
                        ''', (session_id,))
                        results = cursor.fetchall()
                
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'filename': row[0],
                        'file_path': row[1],
                        'extracted_text': row[2] or '',
                        'score': float(row[3]),
                        'evaluation_json': row[4] or '{}',
                        'is_qualified': bool(row[5]),
                        'evaluation_timestamp': row[6],
                        'evaluation_model': row[7] or 'gpt-3.5-turbo'
                    })
                
                return formatted_results
                
        except Exception as e:
            logger.error(f"Error getting session results: {e}")
            return []
    
    # === ANALYTICS METHODS ===
    
    def _update_session_analytics(self, session_id: str, **kwargs):
        """Cập nhật thống kê session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create analytics record if not exists
                cursor.execute('''
                    INSERT OR IGNORE INTO session_analytics (session_id)
                    VALUES (?)
                ''', (session_id,))
                
                # Build update query dynamically
                updates = []
                values = []
                
                if kwargs.get('files_uploaded_increment'):
                    updates.append('total_files_uploaded = total_files_uploaded + ?')
                    values.append(kwargs['files_uploaded_increment'])
                
                if kwargs.get('files_processed_increment'):
                    updates.append('total_files_processed = total_files_processed + ?')
                    values.append(kwargs['files_processed_increment'])
                
                if kwargs.get('evaluations_increment'):
                    updates.append('total_evaluations = total_evaluations + ?')
                    values.append(kwargs['evaluations_increment'])
                
                if kwargs.get('qualified_increment'):
                    updates.append('qualified_candidates = qualified_candidates + ?')
                    values.append(kwargs['qualified_increment'])
                
                if kwargs.get('chat_messages_increment'):
                    updates.append('total_chat_messages = total_chat_messages + ?')
                    values.append(kwargs['chat_messages_increment'])
                
                if kwargs.get('reset_chat_count'):
                    updates.append('total_chat_messages = 0')
                
                if kwargs.get('score_update'):
                    # Calculate new average score
                    updates.append('''
                        average_score = (
                            CASE 
                                WHEN total_evaluations = 1 THEN ?
                                ELSE (average_score * (total_evaluations - 1) + ?) / total_evaluations
                            END
                        )
                    ''')
                    values.extend([kwargs['score_update'], kwargs['score_update']])
                
                # Always update last activity
                updates.append('last_activity_timestamp = CURRENT_TIMESTAMP')
                
                if updates:
                    values.append(session_id)
                    update_query = f'''
                        UPDATE session_analytics 
                        SET {', '.join(updates)}
                        WHERE session_id = ?
                    '''
                    cursor.execute(update_query, values)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating session analytics: {e}")
    
    def get_session_analytics(self, session_id: str) -> Dict:
        """Lấy thống kê session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM session_analytics WHERE session_id = ?
                ''', (session_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'session_id': row[1],
                        'total_files_uploaded': row[2],
                        'total_files_processed': row[3],
                        'total_evaluations': row[4],
                        'qualified_candidates': row[5],
                        'average_score': row[6],
                        'processing_time_seconds': row[7],
                        'total_chat_messages': row[8],
                        'last_activity_timestamp': row[9]
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Error getting session analytics: {e}")
            return {}
    
    # === SESSION METHODS (Updated) ===
    
    def create_session(self, session_id: str, job_description: str, required_candidates: int, 
                  position_title: str = '', session_title: str = '') -> bool:
        """Tạo session mới với session_title"""
        try:
            # Tự động tạo session_title nếu không được cung cấp
            if not session_title:
                from utils import generate_smart_session_title
                session_title = generate_smart_session_title(position_title, job_description, required_candidates)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO sessions 
                    (session_id, session_title, job_description, position_title, required_candidates)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, session_title, job_description, position_title, required_candidates))
                conn.commit()
                
                # Initialize analytics
                self._update_session_analytics(session_id)
                
                logger.info(f"Created session with title: {session_title}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Lấy thông tin session với session_title"""
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
                        'session_title': row[2] if len(row) > 2 else '',  # Backward compatibility
                        'job_description': row[3] if len(row) > 3 else row[2],  # Adjust index based on schema
                        'position_title': row[4] if len(row) > 4 else row[3],
                        'required_candidates': row[5] if len(row) > 5 else row[4],
                        'status': row[6] if len(row) > 6 else row[5],
                        'created_at': row[7] if len(row) > 7 else row[6],
                        'updated_at': row[8] if len(row) > 8 else row[7],
                        'completed_at': row[9] if len(row) > 9 else row[8]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    def get_all_sessions(self) -> List[Dict]:
        """Lấy tất cả sessions với session_title và thống kê tóm tắt"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Kiểm tra xem có cột session_title không
                cursor.execute("PRAGMA table_info(sessions)")
                columns = [column[1] for column in cursor.fetchall()]
                has_session_title = 'session_title' in columns
                
                if has_session_title:
                    cursor.execute('''
                        SELECT s.session_id, s.session_title, s.job_description, s.position_title, 
                            s.required_candidates, s.created_at,
                            COUNT(DISTINCT f.id) as total_cvs,
                            COUNT(DISTINCT e.id) as total_evaluations
                        FROM sessions s
                        LEFT JOIN files f ON s.session_id = f.session_id
                        LEFT JOIN evaluations e ON s.session_id = e.session_id
                        GROUP BY s.session_id, s.session_title, s.job_description, s.position_title, 
                                s.required_candidates, s.created_at
                        ORDER BY s.created_at DESC
                    ''')
                    
                    rows = cursor.fetchall()
                    return [
                        {
                            'session_id': row[0],
                            'session_title': row[1] or 'Phiên không có tên',
                            'job_description': row[2][:100] + '...' if len(row[2]) > 100 else row[2],
                            'position_title': row[3] or 'N/A',
                            'required_candidates': row[4],
                            'created_at': row[5],
                            'total_cvs': row[6],
                            'total_evaluations': row[7]
                        }
                        for row in rows
                    ]
                else:
                    # Fallback cho database cũ
                    cursor.execute('''
                        SELECT s.session_id, s.job_description, s.position_title, s.required_candidates, s.created_at,
                            COUNT(DISTINCT f.id) as total_cvs,
                            COUNT(DISTINCT e.id) as total_evaluations
                        FROM sessions s
                        LEFT JOIN files f ON s.session_id = f.session_id
                        LEFT JOIN evaluations e ON s.session_id = e.session_id
                        GROUP BY s.session_id, s.job_description, s.position_title, s.required_candidates, s.created_at
                        ORDER BY s.created_at DESC
                    ''')
                    
                    rows = cursor.fetchall()
                    return [
                        {
                            'session_id': row[0],
                            'session_title': f"{row[2]} - {row[0][:8]}" if row[2] else f"Phiên {row[0][:8]}",
                            'job_description': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                            'position_title': row[2] or 'N/A',
                            'required_candidates': row[3],
                            'created_at': row[4],
                            'total_cvs': row[5],
                            'total_evaluations': row[6]
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            return []

    def update_session_title(self, session_id: str, new_title: str) -> bool:
        """Cập nhật session title"""
        try:
            from utils import validate_session_title
            
            if not validate_session_title(new_title):
                logger.error(f"Invalid session title: {new_title}")
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions 
                    SET session_title = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (new_title, session_id))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Updated session title to: {new_title}")
                    return True
                else:
                    logger.warning(f"No session found with ID: {session_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating session title: {e}")
            return False

    def search_sessions_by_title(self, search_term: str) -> List[Dict]:
        """Tìm kiếm sessions theo title"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.session_id, s.session_title, s.position_title, s.created_at,
                        COUNT(DISTINCT f.id) as total_cvs,
                        COUNT(DISTINCT e.id) as total_evaluations
                    FROM sessions s
                    LEFT JOIN files f ON s.session_id = f.session_id
                    LEFT JOIN evaluations e ON s.session_id = e.session_id
                    WHERE s.session_title LIKE ? OR s.position_title LIKE ?
                    GROUP BY s.session_id, s.session_title, s.position_title, s.created_at
                    ORDER BY s.created_at DESC
                    LIMIT 20
                ''', (f'%{search_term}%', f'%{search_term}%'))
                
                rows = cursor.fetchall()
                return [
                    {
                        'session_id': row[0],
                        'session_title': row[1] or 'Phiên không có tên',
                        'position_title': row[2] or 'N/A',
                        'created_at': row[3],
                        'total_cvs': row[4],
                        'total_evaluations': row[5]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error searching sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Xóa session và tất cả dữ liệu liên quan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Xóa theo thứ tự đúng (foreign key constraints)
                cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM email_logs WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM session_analytics WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM evaluations WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM files WHERE session_id = ?', (session_id,))
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
                
                cursor.execute('SELECT COUNT(*) FROM files')
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

    # === BACKWARD COMPATIBILITY METHODS ===
    
    def add_cv(self, session_id: str, filename: str, file_path: str, file_type: str, extracted_info: str = None) -> int:
        """Backward compatibility method for add_cv"""
        file_id = self.add_file(session_id, filename, file_path, file_type)
        if file_id > 0 and extracted_info:
            self.update_file_extraction(file_id, extracted_info)
        return file_id
    
    def _update_session_analytics_comprehensive(self, session_id: str) -> None:
        """Cập nhật analytics session dựa trên tất cả dữ liệu hiện tại"""
        try:
            # Lấy tất cả dữ liệu từ database
            all_results = db_manager.get_session_results(session_id)
            all_files = db_manager.get_session_files(session_id)
            chat_messages = db_manager.get_chat_history(session_id)
            
            if all_results:
                # Tính toán lại statistics
                total_evaluations = len(all_results)
                qualified_count = sum(1 for r in all_results if r.get('is_qualified', False))
                total_score = sum(r.get('score', 0) for r in all_results)
                avg_score = total_score / total_evaluations if total_evaluations > 0 else 0
                
                # Update analytics trong database
                with sqlite3.connect(db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE session_analytics 
                        SET total_files_uploaded = ?,
                            total_files_processed = ?,
                            total_evaluations = ?,
                            qualified_candidates = ?,
                            average_score = ?,
                            total_chat_messages = ?,
                            last_activity_timestamp = CURRENT_TIMESTAMP
                        WHERE session_id = ?
                    ''', (
                        len(all_files),
                        len([f for f in all_files if f.get('processing_status') == 'text_extracted']),
                        total_evaluations,
                        qualified_count,
                        avg_score,
                        len(chat_messages),
                        session_id
                    ))
                    conn.commit()
                    
            logger.info(f"Updated comprehensive analytics for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating comprehensive analytics: {e}")

    def update_cv_info(self, cv_id: int, extracted_info: str) -> bool:
        """Backward compatibility method for update_cv_info"""
        return self.update_file_extraction(cv_id, extracted_info)

# Global instance
db_manager = DatabaseManager()