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
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sessions table
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
                
                # CVs table
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
                
                # Evaluations table
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
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def create_session(self, session_id: str, job_description: str, required_candidates: int) -> bool:
        """Create a new evaluation session"""
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
            logger.error(f"Error creating session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
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
            logger.error(f"Error getting session: {e}")
            return None
    
    def add_cv(self, session_id: str, filename: str, file_path: str, file_type: str, extracted_info: str = None) -> int:
        """Add a CV to the database"""
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
            logger.error(f"Error adding CV: {e}")
            return -1
    
    def update_cv_info(self, cv_id: int, extracted_info: str) -> bool:
        """Update CV extracted information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE cvs SET extracted_info = ? WHERE id = ?
                ''', (extracted_info, cv_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating CV info: {e}")
            return False
    
    def add_evaluation(self, session_id: str, cv_id: int, score: float, evaluation_text: str, is_passed: bool) -> bool:
        """Add evaluation result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO evaluations (session_id, cv_id, score, evaluation_text, is_passed)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, cv_id, score, evaluation_text, is_passed))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding evaluation: {e}")
            return False
    
    def get_session_results(self, session_id: str) -> List[Dict]:
        """Get all evaluation results for a session"""
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
                        'score': row[2],
                        'evaluation_text': row[3],
                        'is_passed': row[4],
                        'created_at': row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting session results: {e}")
            return []
    
    def get_all_sessions(self) -> List[Dict]:
        """Get all sessions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Fixed: Qualify column names to avoid ambiguity
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
            logger.error(f"Error getting all sessions: {e}")
            return []

# Global database instance
db_manager = DatabaseManager()