import os
import json
import logging
from typing import Dict, List, TypedDict, Any, Iterator, Optional
from pathlib import Path
import threading
import time
from datetime import datetime

# Simplified workflow without LangGraph checkpointing
from gemini_ocr import gemini_ocr
from gpt_evaluator import get_gpt_evaluator
from database import db_manager
from email_service import email_service
from openai import OpenAI

logger = logging.getLogger(__name__)

class CVEvaluationState(TypedDict):
    """Simplified state for CV evaluation workflow"""
    session_id: str
    job_description: str
    required_candidates: int
    position_title: str
    uploaded_files: List[Dict[str, Any]]
    extracted_texts: List[Dict[str, Any]]
    gpt_evaluations: List[Dict[str, Any]]
    final_results: Dict[str, Any]
    chat_history: List[Dict[str, Any]]
    processing_status: str
    error: str
    email_status: Dict[str, Any]
    total_processed: int
    current_batch: int

class CVEvaluationWorkflow:
    """Simplified workflow without LangGraph checkpointing"""
    
    def __init__(self):
        self.openai_client = self._init_openai_client()
        # In-memory session storage instead of complex checkpointing
        self.session_states = {}
        logger.info("Simplified CV Evaluation Workflow initialized")
        
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

    def _init_session(self, state: CVEvaluationState) -> CVEvaluationState:
        """Initialize session state"""
        logger.info(f"Initializing session: {state['session_id']}")
        
        try:
            # Initialize default values
            if "chat_history" not in state:
                state["chat_history"] = []
            if "processing_status" not in state:
                state["processing_status"] = "initialized"
            if "email_status" not in state:
                state["email_status"] = {"sent": False, "scheduled": False}
            if "total_processed" not in state:
                state["total_processed"] = 0
            if "current_batch" not in state:
                state["current_batch"] = 0
            
            # Add to chat history
            state["chat_history"].append({
                "type": "system",
                "message": f"Session khởi tạo cho vị trí: {state.get('position_title', 'N/A')}",
                "timestamp": time.time()
            })
            
            state["processing_status"] = "ready"
            
            # Store in memory
            self.session_states[state["session_id"]] = state
            
            logger.info("Session initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            state["error"] = f"Error initializing session: {str(e)}"
            
        return state

    def _process_files(self, state: CVEvaluationState) -> CVEvaluationState:
        """Process uploaded files"""
        logger.info("Processing uploaded files...")
        
        try:
            state["processing_status"] = "processing_files"
            
            # Update chat history
            state["chat_history"].append({
                "type": "system", 
                "message": f"Đang xử lý {len(state['uploaded_files'])} file CV...",
                "timestamp": time.time()
            })

            # Create or update session in database
            db_manager.create_session(
                state["session_id"],
                state["job_description"],
                state["required_candidates"]
            )

            # Add files to database
            processed_count = 0
            for file_info in state["uploaded_files"]:
                cv_id = db_manager.add_cv(
                    state["session_id"],
                    file_info["filename"],
                    file_info["path"],
                    file_info["type"]
                )
                file_info["cv_id"] = cv_id
                processed_count += 1
                
                # Update progress in chat
                if processed_count % 5 == 0:
                    state["chat_history"].append({
                        "type": "system",
                        "message": f"Đã xử lý {processed_count}/{len(state['uploaded_files'])} file",
                        "timestamp": time.time()
                    })

            state["total_processed"] = processed_count
            state["processing_status"] = "files_processed"
            
            state["chat_history"].append({
                "type": "system",
                "message": f"✅ Hoàn thành xử lý {processed_count} file CV",
                "timestamp": time.time()
            })

            # Update session state in memory
            self.session_states[state["session_id"]] = state

            logger.info(f"Processed {len(state['uploaded_files'])} files")

        except Exception as e:
            logger.error(f"Error processing files: {e}")
            state["error"] = f"Error processing files: {str(e)}"
            state["chat_history"].append({
                "type": "error",
                "message": f"❌ Lỗi xử lý file: {str(e)}",
                "timestamp": time.time()
            })

        return state

    def _extract_text_with_gemini(self, state: CVEvaluationState) -> CVEvaluationState:
        """Extract text from files using Gemini OCR"""
        logger.info("Extracting text with Gemini OCR...")
        extracted_texts = []

        try:
            state["processing_status"] = "extracting_text"
            
            state["chat_history"].append({
                "type": "system",
                "message": "🔍 Bắt đầu trích xuất text với Gemini OCR...",
                "timestamp": time.time()
            })

            total_files = len(state["uploaded_files"])
            for i, file_info in enumerate(state["uploaded_files"], 1):
                logger.info(f"Extracting text from {file_info['filename']} ({i}/{total_files})")

                # Update progress
                if i % 3 == 0 or i == total_files:
                    state["chat_history"].append({
                        "type": "system",
                        "message": f"🔍 Đang trích xuất text: {i}/{total_files} file",
                        "timestamp": time.time()
                    })

                extracted_text = gemini_ocr.extract_text(file_info["path"])

                text_data = {
                    "cv_id": file_info["cv_id"],
                    "filename": file_info["filename"],
                    "extracted_text": extracted_text
                }

                extracted_texts.append(text_data)
                db_manager.update_cv_info(file_info["cv_id"], extracted_text)

            state["extracted_texts"] = extracted_texts
            state["processing_status"] = "text_extracted"
            
            state["chat_history"].append({
                "type": "system",
                "message": f"✅ Hoàn thành trích xuất text từ {len(extracted_texts)} file",
                "timestamp": time.time()
            })

            # Update session state
            self.session_states[state["session_id"]] = state

            logger.info(f"Successfully extracted text from {len(extracted_texts)} files")

        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            state["error"] = f"Error extracting text: {str(e)}"
            state["chat_history"].append({
                "type": "error",
                "message": f"❌ Lỗi trích xuất text: {str(e)}",
                "timestamp": time.time()
            })

        return state

    def _evaluate_with_gpt(self, state: CVEvaluationState) -> CVEvaluationState:
        """Evaluate CVs using GPT-3.5-turbo"""
        logger.info("Evaluating CVs with GPT-3.5-turbo...")
        evaluations = []

        try:
            state["processing_status"] = "evaluating_cvs"
            
            state["chat_history"].append({
                "type": "system",
                "message": "🤖 Bắt đầu đánh giá CV với GPT-3.5-turbo...",
                "timestamp": time.time()
            })

            gpt_evaluator = get_gpt_evaluator()
            total_texts = len(state["extracted_texts"])
            
            for i, text_data in enumerate(state["extracted_texts"], 1):
                logger.info(f"Evaluating {text_data['filename']} with GPT-3.5-turbo ({i}/{total_texts})")

                # Update progress
                state["chat_history"].append({
                    "type": "system",
                    "message": f"🤖 Đánh giá CV: {text_data['filename']} ({i}/{total_texts})",
                    "timestamp": time.time()
                })

                extracted_text = text_data.get('extracted_text', '')
                if not extracted_text or extracted_text.startswith('Error'):
                    evaluation_data = {
                        "cv_id": text_data["cv_id"],
                        "filename": text_data["filename"],
                        "gpt_response": "Không thể trích xuất text từ CV",
                        "parsed_evaluation": None
                    }
                    evaluations.append(evaluation_data)
                    continue

                # Use GPT to evaluate CV
                gpt_response = gpt_evaluator.evaluate_cv(
                    state["job_description"],
                    extracted_text
                )

                # Parse the evaluation result
                parsed_evaluation = gpt_evaluator.extract_json_from_response(gpt_response)

                evaluation_data = {
                    "cv_id": text_data["cv_id"],
                    "filename": text_data["filename"],
                    "gpt_response": gpt_response,
                    "parsed_evaluation": parsed_evaluation,
                    "extracted_text": extracted_text
                }

                evaluations.append(evaluation_data)
                
                # Show individual result
                if parsed_evaluation:
                    score = parsed_evaluation.get("Điểm tổng", 0)
                    is_qualified = parsed_evaluation.get("Phù hợp", "không phù hợp") == "phù hợp"
                    state["chat_history"].append({
                        "type": "result",
                        "message": f"✅ {text_data['filename']}: {score:.1f}/10 {'✅ Đạt' if is_qualified else '❌ Không đạt'}",
                        "timestamp": time.time()
                    })

            state["gpt_evaluations"] = evaluations
            state["processing_status"] = "cvs_evaluated"
            
            state["chat_history"].append({
                "type": "system",
                "message": f"✅ Hoàn thành đánh giá {len(evaluations)} CV với GPT-3.5-turbo",
                "timestamp": time.time()
            })

            # Update session state
            self.session_states[state["session_id"]] = state

            logger.info(f"Completed GPT evaluation for {len(evaluations)} CVs")

        except Exception as e:
            logger.error(f"Error evaluating with GPT: {e}")
            state["error"] = f"Error evaluating with GPT: {str(e)}"
            state["chat_history"].append({
                "type": "error", 
                "message": f"❌ Lỗi đánh giá GPT: {str(e)}",
                "timestamp": time.time()
            })

        return state

    def _finalize_results(self, state: CVEvaluationState) -> CVEvaluationState:
        """Finalize results and generate summary"""
        logger.info("Finalizing results...")

        try:
            state["processing_status"] = "finalizing_results"
            
            final_evaluations = []

            for evaluation in state["gpt_evaluations"]:
                parsed_eval = evaluation.get("parsed_evaluation")

                if parsed_eval:
                    score = parsed_eval.get("Điểm tổng", 0)
                    is_qualified = parsed_eval.get("Phù hợp", "không phù hợp") == "phù hợp"
                    evaluation_text = json.dumps(parsed_eval, ensure_ascii=False, indent=2)
                else:
                    score = 0
                    is_qualified = False
                    evaluation_text = evaluation["gpt_response"]

                final_evaluation = {
                    "cv_id": evaluation["cv_id"],
                    "filename": evaluation["filename"],
                    "score": score,
                    "is_qualified": is_qualified,
                    "evaluation_text": evaluation_text,
                    "gpt_response": evaluation["gpt_response"],
                    "extracted_text": evaluation.get("extracted_text", "")
                }

                final_evaluations.append(final_evaluation)

                # Save to database
                db_manager.add_evaluation(
                    state["session_id"],
                    evaluation["cv_id"],
                    score,
                    evaluation_text,
                    is_qualified
                )

            # Sort by score (highest first)
            final_evaluations.sort(key=lambda x: x["score"], reverse=True)

            # Calculate statistics
            total_cvs = len(final_evaluations)
            qualified_cvs = sum(1 for e in final_evaluations if e["is_qualified"])
            avg_score = sum(e["score"] for e in final_evaluations) / total_cvs if total_cvs > 0 else 0

            required_count = state["required_candidates"]
            top_candidates = final_evaluations[:required_count]

            final_results = {
                "total_cvs": total_cvs,
                "qualified_count": qualified_cvs,
                "average_score": round(avg_score, 2),
                "top_candidates": top_candidates,
                "all_evaluations": final_evaluations,
                "summary": {
                    "best_score": final_evaluations[0]["score"] if final_evaluations else 0,
                    "worst_score": final_evaluations[-1]["score"] if final_evaluations else 0,
                    "qualification_rate": round(qualified_cvs / total_cvs * 100, 1) if total_cvs > 0 else 0
                },
                "qualified_candidates": [e for e in final_evaluations if e["is_qualified"]],
                "rejected_candidates": [e for e in final_evaluations if not e["is_qualified"]]
            }

            state["final_results"] = final_results
            state["processing_status"] = "results_finalized"
            
            # Add summary to chat
            state["chat_history"].append({
                "type": "summary",
                "message": f"📊 Kết quả: {qualified_cvs}/{total_cvs} CV đạt yêu cầu (Điểm TB: {avg_score:.1f}/10)",
                "timestamp": time.time()
            })

            # Update session state
            self.session_states[state["session_id"]] = state

            logger.info(f"Finalized results: {qualified_cvs}/{total_cvs} qualified, avg score: {avg_score:.2f}")

        except Exception as e:
            logger.error(f"Error finalizing results: {e}")
            state["error"] = f"Error finalizing results: {str(e)}"
            state["chat_history"].append({
                "type": "error",
                "message": f"❌ Lỗi tổng hợp kết quả: {str(e)}",
                "timestamp": time.time()
            })

        return state

    def _send_emails(self, state: CVEvaluationState) -> CVEvaluationState:
        """Send emails to candidates"""
        logger.info("Processing email notifications...")
        
        try:
            state["processing_status"] = "sending_emails"
            
            if not state.get("final_results"):
                logger.warning("No final results available for email sending")
                return state
            
            final_results = state["final_results"]
            position_title = state.get("position_title", "Vị trí ứng tuyển")
            
            qualified_candidates = final_results.get("qualified_candidates", [])
            rejected_candidates = final_results.get("rejected_candidates", [])
            
            # Send rejection emails immediately
            if rejected_candidates:
                state["chat_history"].append({
                    "type": "system",
                    "message": f"📧 Đang gửi email từ chối cho {len(rejected_candidates)} ứng viên...",
                    "timestamp": time.time()
                })
                
                email_service.send_rejection_emails(rejected_candidates, position_title)
            
            # Schedule interview emails for 2 weeks later
            if qualified_candidates:
                state["chat_history"].append({
                    "type": "system", 
                    "message": f"⏰ Lên lịch email mời phỏng vấn cho {len(qualified_candidates)} ứng viên (sau 2 tuần)...",
                    "timestamp": time.time()
                })
                
                email_service.schedule_interview_emails(qualified_candidates, position_title)
            
            # Update email status
            state["email_status"] = {
                "sent": True,
                "scheduled": len(qualified_candidates) > 0,
                "rejection_count": len(rejected_candidates),
                "interview_count": len(qualified_candidates),
                "timestamp": time.time()
            }
            
            state["chat_history"].append({
                "type": "system",
                "message": f"✅ Email hoàn thành: {len(rejected_candidates)} từ chối, {len(qualified_candidates)} mời PV",
                "timestamp": time.time()
            })
            
            state["processing_status"] = "completed"
            
            # Update session state
            self.session_states[state["session_id"]] = state
            
        except Exception as e:
            logger.error(f"Error sending emails: {e}")
            state["error"] = f"Error sending emails: {str(e)}"
            state["chat_history"].append({
                "type": "error",
                "message": f"❌ Lỗi gửi email: {str(e)}",
                "timestamp": time.time()
            })
        
        return state

    def run_evaluation(self, session_id: str, job_description: str, required_candidates: int, 
                      uploaded_files: List[Dict], position_title: str = None) -> Dict:
        """Run the complete evaluation workflow"""
        try:
            # Create initial state
            initial_state = CVEvaluationState(
                session_id=session_id,
                job_description=job_description,
                required_candidates=required_candidates,
                position_title=position_title or "Vị trí tuyển dụng",
                uploaded_files=uploaded_files,
                extracted_texts=[],
                gpt_evaluations=[],
                final_results={},
                chat_history=[],
                processing_status="initialized",
                error="",
                email_status={"sent": False, "scheduled": False},
                total_processed=0,
                current_batch=0
            )

            # Run workflow steps sequentially
            logger.info("Starting evaluation workflow...")
            
            # Step 1: Initialize session
            state = self._init_session(initial_state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            # Step 2: Process files
            state = self._process_files(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            # Step 3: Extract text
            state = self._extract_text_with_gemini(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            # Step 4: Evaluate with GPT
            state = self._evaluate_with_gpt(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            # Step 5: Finalize results
            state = self._finalize_results(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}
            
            # Step 6: Send emails
            state = self._send_emails(state)
            if state.get("error"):
                return {"success": False, "error": state["error"]}

            return {
                "success": True,
                "results": state["final_results"],
                "session_id": session_id,
                "chat_history": state.get("chat_history", []),
                "status": state.get("processing_status", "completed"),
                "email_status": state.get("email_status", {})
            }

        except Exception as e:
            logger.error(f"Error running evaluation workflow: {e}")
            return {"success": False, "error": str(e)}

    def get_session_state(self, session_id: str) -> Optional[CVEvaluationState]:
        """Get current session state"""
        try:
            # First try in-memory storage
            if session_id in self.session_states:
                return self.session_states[session_id]
            
            # If not found in memory, check database
            session_info = db_manager.get_session(session_id)
            if session_info:
                # Create basic state from database
                results = db_manager.get_session_results(session_id)
                
                # Convert to expected format
                final_results = self._convert_db_results_to_format(results)
                
                return {
                    "session_id": session_id,
                    "job_description": session_info['job_description'],
                    "required_candidates": session_info['required_candidates'],
                    "position_title": "Đã lưu",
                    "final_results": final_results,
                    "chat_history": [
                        {
                            "type": "system",
                            "message": "Session được khôi phục từ database",
                            "timestamp": time.time()
                        }
                    ],
                    "processing_status": "completed",
                    "email_status": {"sent": False, "scheduled": False}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session state: {e}")
            return None

    def _convert_db_results_to_format(self, db_results: List[Dict]) -> Dict:
        """Convert database results to expected format"""
        if not db_results:
            return {
                "total_cvs": 0,
                "qualified_count": 0,
                "average_score": 0,
                "top_candidates": [],
                "all_evaluations": [],
                "summary": {"best_score": 0, "worst_score": 0, "qualification_rate": 0},
                "qualified_candidates": [],
                "rejected_candidates": []
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
                "cv_id": result.get('filename', ''),
                "filename": result.get('filename', ''),
                "score": result.get('score', 0),
                "is_qualified": result.get('is_passed', False),
                "evaluation_text": result.get('evaluation_text', ''),
                "extracted_text": result.get('extracted_info', '')
            }
            converted_results.append(converted_result)
        
        return {
            "total_cvs": total_cvs,
            "qualified_count": qualified_cvs,
            "average_score": round(avg_score, 2),
            "top_candidates": converted_results[:3],
            "all_evaluations": converted_results,
            "summary": {
                "best_score": sorted_results[0].get('score', 0) if sorted_results else 0,
                "worst_score": sorted_results[-1].get('score', 0) if sorted_results else 0,
                "qualification_rate": round(qualified_cvs / total_cvs * 100, 1) if total_cvs > 0 else 0
            },
            "qualified_candidates": [r for r in converted_results if r["is_qualified"]],
            "rejected_candidates": [r for r in converted_results if not r["is_qualified"]]
        }

    def generate_final_response_stream(self, evaluation_results: Dict, job_description: str) -> Iterator[str]:
        """Generate final response using GPT with streaming"""
        try:
            if not self.openai_client:
                yield "Error: OpenAI client not available"
                return

            summary_data = {
                "job_description": job_description,
                "total_cvs": evaluation_results.get("total_cvs", 0),
                "qualified_count": evaluation_results.get("qualified_count", 0),
                "average_score": evaluation_results.get("average_score", 0),
                "top_candidates": evaluation_results.get("top_candidates", [])[:3]
            }

            prompt = f"""
                Bạn là một chuyên gia tuyển dụng có kinh nghiệm 10+ năm. Dựa trên kết quả đánh giá CV từ GPT-3.5-turbo, hãy tạo một báo cáo tóm tắt chuyên nghiệp và chi tiết.

                THÔNG TIN TUYỂN DỤNG:
                {job_description}

                KẾT QUẢ ĐÁNH GIÁ:
                - Tổng số CV: {summary_data['total_cvs']}
                - Số CV đạt yêu cầu: {summary_data['qualified_count']}
                - Điểm trung bình: {summary_data['average_score']}/10
                - Tỷ lệ đạt yêu cầu: {evaluation_results.get('summary', {}).get('qualification_rate', 0)}%

                TOP ỨNG VIÊN:
                {json.dumps(summary_data['top_candidates'], ensure_ascii=False, indent=2)}

                Hãy viết một báo cáo tóm tắt chi tiết bao gồm:
                1. **Tóm tắt tổng quan**: Nhận xét chung về chất lượng pool ứng viên
                2. **Phân tích chi tiết**: 
                   - Điểm mạnh của pool ứng viên
                   - Điểm yếu cần chú ý
                   - Xu hướng chung về kỹ năng và kinh nghiệm
                3. **Đánh giá top ứng viên**: Phân tích chi tiết từng ứng viên hàng đầu
                4. **Khuyến nghị tuyển dụng**: 
                   - Ứng viên nên mời phỏng vấn
                   - Câu hỏi phỏng vấn được đề xuất
                   - Lưu ý đặc biệt cho từng ứng viên
                5. **Email Marketing**: Đã gửi email từ chối và lên lịch email mời phỏng vấn
                6. **Kết luận và bước tiếp theo**

                Viết một cách chuyên nghiệp, có cấu trúc rõ ràng, và cung cấp thông tin hữu ích để hỗ trợ quyết định tuyển dụng.
                Sử dụng emoji phù hợp để làm báo cáo sinh động và dễ đọc.
            """

            messages = [
                {"role": "system", "content": "Bạn là một chuyên gia tuyển dụng hàng đầu với kinh nghiệm sâu rộng về đánh giá và tuyển chọn nhân tài. Bạn viết báo cáo một cách chuyên nghiệp, có cấu trúc và đầy đủ thông tin."},
                {"role": "user", "content": prompt}
            ]

            stream = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=2500,
                temperature=0.7,
                stream=True
            )

            for chunk in stream:
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content

        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            yield f"Error generating final response: {str(e)}"

# Create global instance with singleton pattern
_cv_workflow = None

def get_cv_workflow():
    """Get workflow instance (singleton)"""
    global _cv_workflow
    if _cv_workflow is None:
        _cv_workflow = CVEvaluationWorkflow()
    return _cv_workflow

# For backward compatibility
cv_workflow = get_cv_workflow()