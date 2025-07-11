import os
import json
import logging
from typing import Dict, List, Optional
import time

from gemini_ocr import gemini_ocr
from gpt_evaluator import get_gpt_evaluator
from database import db_manager
from openai import OpenAI

logger = logging.getLogger(__name__)

class CVEvaluationWorkflow:
    """Updated workflow with database integration"""
    
    def __init__(self):
        self.openai_client = self._init_openai_client()
        logger.info("CV Evaluation Workflow initialized with database integration")
        
    def _init_openai_client(self):
        """Initialize OpenAI client"""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("OpenAI API key not found")
                return None

            client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized")
            return client

        except Exception as e:
            logger.error(f"Error initializing OpenAI: {e}")
            return None

    def _add_chat_message(self, session_id: str, message_type: str, content: str, sender: str = 'system'):
        """Helper to add chat message to both session state and database"""
        try:
            # Save to database
            db_manager.save_chat_message(session_id, message_type, content, sender)
            
            # Also return the message for immediate use
            return {
                "type": message_type,
                "message": content,
                "sender": sender,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error adding chat message: {e}")
            return None

    def _init_session(self, session_id: str, job_description: str, required_candidates: int, position_title: str = '') -> Dict:
        """Initialize session with database"""
        logger.info(f"Initializing session: {session_id}")
        
        try:
            # Create session in database
            success = db_manager.create_session(
                session_id, 
                job_description, 
                required_candidates, 
                position_title
            )
            
            if not success:
                raise Exception("Failed to create session in database")
            
            # Add initial chat message
            self._add_chat_message(
                session_id, 
                'system', 
                f"🎯 Session created for position: {position_title or 'New Position'}"
            )
            
            return {
                "session_id": session_id,
                "status": "initialized",
                "message": "Session initialized successfully"
            }
            
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            return {
                "session_id": session_id,
                "status": "error",
                "error": str(e)
            }

    def _process_files(self, session_id: str, uploaded_files: List[Dict]) -> Dict:
        """Process uploaded files with database storage"""
        logger.info("Processing uploaded files...")
        
        try:
            self._add_chat_message(
                session_id, 
                'system', 
                f"📁 Processing {len(uploaded_files)} uploaded files..."
            )

            file_ids = []
            
            for file_info in uploaded_files:
                # Add file to database
                file_id = db_manager.add_file(
                    session_id,
                    file_info["filename"],
                    file_info["path"],
                    file_info["type"],
                    file_info.get("size", 0)
                )
                
                if file_id > 0:
                    file_info["file_id"] = file_id
                    file_ids.append(file_id)
                    
                    logger.info(f"Added file {file_info['filename']} with ID {file_id}")
                else:
                    logger.error(f"Failed to add file {file_info['filename']} to database")

            self._add_chat_message(
                session_id, 
                'system', 
                f"✅ Successfully processed {len(file_ids)} files"
            )

            return {
                "status": "files_processed",
                "file_ids": file_ids,
                "processed_count": len(file_ids)
            }

        except Exception as e:
            logger.error(f"Error processing files: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Error processing files: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _extract_text_with_gemini(self, session_id: str, uploaded_files: List[Dict]) -> Dict:
        """Extract text with database updates"""
        logger.info("Extracting text with Gemini OCR...")
        
        try:
            self._add_chat_message(
                session_id, 
                'system', 
                "🔍 Starting text extraction with Gemini OCR..."
            )

            extracted_data = []
            total_files = len(uploaded_files)
            
            for i, file_info in enumerate(uploaded_files, 1):
                filename = file_info["filename"]
                file_path = file_info["path"]
                file_id = file_info.get("file_id")
                
                self._add_chat_message(
                    session_id, 
                    'system', 
                    f"🔍 [{i}/{total_files}] Extracting text from {filename}..."
                )

                # Extract text using Gemini
                extracted_text = gemini_ocr.extract_text(file_path)

                if extracted_text and not extracted_text.startswith('Error'):
                    # Update database with extracted text
                    if file_id:
                        db_manager.update_file_extraction(file_id, extracted_text)
                    
                    extracted_data.append({
                        "file_id": file_id,
                        "filename": filename,
                        "extracted_text": extracted_text
                    })
                    
                    logger.info(f"Successfully extracted text from {filename}")
                else:
                    logger.warning(f"Failed to extract text from {filename}")
                    self._add_chat_message(
                        session_id, 
                        'error', 
                        f"❌ Failed to extract text from {filename}"
                    )

            self._add_chat_message(
                session_id, 
                'system', 
                f"✅ Text extraction completed for {len(extracted_data)}/{total_files} files"
            )

            return {
                "status": "text_extracted",
                "extracted_data": extracted_data,
                "success_count": len(extracted_data)
            }

        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Text extraction failed: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _evaluate_with_gpt(self, session_id: str, job_description: str, extracted_data: List[Dict]) -> Dict:
        """Evaluate CVs with GPT and save to database"""
        logger.info("Evaluating CVs with GPT-3.5-turbo...")
        
        try:
            self._add_chat_message(
                session_id, 
                'system', 
                "🤖 Starting AI evaluation with GPT-3.5-turbo..."
            )

            gpt_evaluator = get_gpt_evaluator()
            evaluations = []
            total_cvs = len(extracted_data)
            
            for i, data in enumerate(extracted_data, 1):
                filename = data["filename"]
                extracted_text = data["extracted_text"]
                file_id = data["file_id"]
                
                self._add_chat_message(
                    session_id, 
                    'system', 
                    f"🤖 [{i}/{total_cvs}] Evaluating {filename}..."
                )

                # Evaluate with GPT
                gpt_response = gpt_evaluator.evaluate_cv(job_description, extracted_text)
                parsed_evaluation = gpt_evaluator.extract_json_from_response(gpt_response)

                if parsed_evaluation:
                    score = parsed_evaluation.get("Điểm tổng", 0)
                    is_qualified = parsed_evaluation.get("Phù hợp", "không phù hợp") == "phù hợp"
                    
                    # Save evaluation to database
                    db_manager.add_evaluation(
                        session_id,
                        file_id,
                        score,
                        json.dumps(parsed_evaluation, ensure_ascii=False),
                        is_qualified
                    )
                    
                    evaluation_result = {
                        "file_id": file_id,
                        "filename": filename,
                        "score": score,
                        "is_qualified": is_qualified,
                        "evaluation_data": parsed_evaluation,
                        "extracted_text": extracted_text
                    }
                    
                    evaluations.append(evaluation_result)
                    
                    # Show individual result
                    status = "✅ Qualified" if is_qualified else "❌ Not Qualified"
                    self._add_chat_message(
                        session_id, 
                        'result', 
                        f"📊 {filename}: {score:.1f}/10 - {status}"
                    )
                    
                else:
                    logger.warning(f"Failed to parse evaluation for {filename}")
                    evaluations.append({
                        "file_id": file_id,
                        "filename": filename,
                        "score": 0,
                        "is_qualified": False,
                        "evaluation_data": None,
                        "extracted_text": extracted_text
                    })

            self._add_chat_message(
                session_id, 
                'system', 
                f"✅ AI evaluation completed for {len(evaluations)} CVs"
            )

            return {
                "status": "cvs_evaluated",
                "evaluations": evaluations,
                "total_evaluated": len(evaluations)
            }

        except Exception as e:
            logger.error(f"Error evaluating with GPT: {e}")
            self._add_chat_message(session_id, 'error', f"❌ AI evaluation failed: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _finalize_results(self, session_id: str, evaluations: List[Dict], required_candidates: int) -> Dict:
        """Finalize results with database summary"""
        logger.info("Finalizing evaluation results...")

        try:
            # Sort evaluations by score
            sorted_evaluations = sorted(evaluations, key=lambda x: x["score"], reverse=True)
            
            # Calculate statistics
            total_cvs = len(sorted_evaluations)
            qualified_count = sum(1 for e in sorted_evaluations if e["is_qualified"])
            avg_score = sum(e["score"] for e in sorted_evaluations) / total_cvs if total_cvs > 0 else 0
            
            # Create final results structure
            final_results = {
                "total_cvs": total_cvs,
                "qualified_count": qualified_count,
                "average_score": round(avg_score, 2),
                "top_candidates": sorted_evaluations[:required_candidates],
                "all_evaluations": sorted_evaluations,
                "summary": {
                    "best_score": sorted_evaluations[0]["score"] if sorted_evaluations else 0,
                    "worst_score": sorted_evaluations[-1]["score"] if sorted_evaluations else 0,
                    "qualification_rate": round(qualified_count / total_cvs * 100, 1) if total_cvs > 0 else 0
                },
                "qualified_candidates": [e for e in sorted_evaluations if e["is_qualified"]],
                "rejected_candidates": [e for e in sorted_evaluations if not e["is_qualified"]]
            }

            # Add summary message
            self._add_chat_message(
                session_id, 
                'summary', 
                f"📊 Evaluation completed: {qualified_count}/{total_cvs} qualified (Avg: {avg_score:.1f}/10)"
            )

            return {
                "status": "results_finalized",
                "final_results": final_results
            }

        except Exception as e:
            logger.error(f"Error finalizing results: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Failed to finalize results: {str(e)}")
            return {"status": "error", "error": str(e)}

    def run_evaluation(self, session_id: str, job_description: str, required_candidates: int, 
                      uploaded_files: List[Dict], position_title: str = None) -> Dict:
        """Run complete evaluation workflow with database integration"""
        try:
            logger.info(f"Starting evaluation workflow for session {session_id}")
            
            # Step 1: Initialize session
            init_result = self._init_session(session_id, job_description, required_candidates, position_title)
            if init_result["status"] == "error":
                return {"success": False, "error": init_result["error"]}
            
            # Step 2: Process files
            process_result = self._process_files(session_id, uploaded_files)
            if process_result["status"] == "error":
                return {"success": False, "error": process_result["error"]}
            
            # Step 3: Extract text
            extract_result = self._extract_text_with_gemini(session_id, uploaded_files)
            if extract_result["status"] == "error":
                return {"success": False, "error": extract_result["error"]}
            
            # Step 4: Evaluate with GPT
            eval_result = self._evaluate_with_gpt(session_id, job_description, extract_result["extracted_data"])
            if eval_result["status"] == "error":
                return {"success": False, "error": eval_result["error"]}
            
            # Step 5: Finalize results
            final_result = self._finalize_results(session_id, eval_result["evaluations"], required_candidates)
            if final_result["status"] == "error":
                return {"success": False, "error": final_result["error"]}

            # Get chat history from database
            chat_history = db_manager.get_chat_history(session_id)

            return {
                "success": True,
                "session_id": session_id,
                "results": final_result["final_results"],
                "chat_history": chat_history,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Error running evaluation workflow: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Workflow failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """Get session state from database"""
        try:
            # Get session info
            session_info = db_manager.get_session(session_id)
            if not session_info:
                return None
            
            # Get chat history
            chat_history = db_manager.get_chat_history(session_id)
            
            # Get evaluation results
            results = db_manager.get_session_results(session_id)
            
            # Get session analytics
            analytics = db_manager.get_session_analytics(session_id)
            
            # Convert results to expected format
            if results:
                # Sort by score
                sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
                
                total_cvs = len(sorted_results)
                qualified_count = sum(1 for r in sorted_results if r.get('is_qualified', False))
                avg_score = sum(r.get('score', 0) for r in sorted_results) / total_cvs if total_cvs > 0 else 0
                
                # Convert to expected format
                converted_evaluations = []
                for result in sorted_results:
                    converted_evaluations.append({
                        "filename": result.get('filename', ''),
                        "score": result.get('score', 0),
                        "is_qualified": result.get('is_qualified', False),
                        "evaluation_text": result.get('evaluation_json', ''),
                        "extracted_text": result.get('extracted_text', '')
                    })
                
                final_results = {
                    "total_cvs": total_cvs,
                    "qualified_count": qualified_count,
                    "average_score": round(avg_score, 2),
                    "all_evaluations": converted_evaluations,
                    "top_candidates": converted_evaluations[:session_info.get('required_candidates', 3)],
                    "summary": {
                        "best_score": sorted_results[0].get('score', 0) if sorted_results else 0,
                        "worst_score": sorted_results[-1].get('score', 0) if sorted_results else 0,
                        "qualification_rate": round(qualified_count / total_cvs * 100, 1) if total_cvs > 0 else 0
                    },
                    "qualified_candidates": [r for r in converted_evaluations if r["is_qualified"]],
                    "rejected_candidates": [r for r in converted_evaluations if not r["is_qualified"]]
                }
            else:
                final_results = {}
            
            return {
                "session_id": session_id,
                "job_description": session_info.get('job_description', ''),
                "position_title": session_info.get('position_title', ''),
                "required_candidates": session_info.get('required_candidates', 3),
                "final_results": final_results,
                "chat_history": chat_history,
                "processing_status": session_info.get('status', 'active'),
                "analytics": analytics
            }
            
        except Exception as e:
            logger.error(f"Error getting session state: {e}")
            return None

    def add_chat_message_to_session(self, session_id: str, message_type: str, content: str, sender: str = 'user'):
        """Add a chat message to session (for external use)"""
        return self._add_chat_message(session_id, message_type, content, sender)

    def get_session_chat_history(self, session_id: str) -> List[Dict]:
        """Get chat history for session"""
        return db_manager.get_chat_history(session_id)

    def clear_session_chat(self, session_id: str) -> bool:
        """Clear chat history for session"""
        return db_manager.clear_chat_history(session_id)

# Global instance
_cv_workflow = None

def get_cv_workflow():
    """Get workflow instance (singleton)"""
    global _cv_workflow
    if _cv_workflow is None:
        _cv_workflow = CVEvaluationWorkflow()
    return _cv_workflow

cv_workflow = get_cv_workflow()