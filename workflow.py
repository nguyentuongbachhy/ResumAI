import os
import json
import logging
from typing import Dict, List, Optional
import time

from gemini_ocr import gemini_ocr
from gpt_evaluator import get_gpt_evaluator
from database import db_manager
from openai import OpenAI
from textwrap import dedent

logger = logging.getLogger(__name__)

class CVEvaluationWorkflow:
    """Quy trình đánh giá CV đã cập nhật với tích hợp cơ sở dữ liệu"""
    
    def __init__(self):
        self.openai_client = self._init_openai_client()
        logger.info("Quy trình đánh giá CV đã khởi tạo với tích hợp cơ sở dữ liệu")
        
    def _init_openai_client(self):
        """Khởi tạo OpenAI client"""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("Không tìm thấy khóa API OpenAI")
                return None

            client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client đã được khởi tạo")
            return client

        except Exception as e:
            logger.error(f"Lỗi khởi tạo OpenAI: {e}")
            return None

    def _add_chat_message(self, session_id: str, message_type: str, content: str, sender: str = 'system'):
        """Helper để thêm tin nhắn chat vào cả session state và cơ sở dữ liệu"""
        try:
            # Lưu vào cơ sở dữ liệu
            db_manager.save_chat_message(session_id, message_type, content, sender)
            
            # Cũng trả về tin nhắn để sử dụng ngay lập tức
            return {
                "type": message_type,
                "message": content,
                "sender": sender,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Lỗi thêm tin nhắn chat: {e}")
            return None

    def _init_session(self, session_id: str, job_description: str, required_candidates: int, position_title: str = '') -> Dict:
        """Khởi tạo phiên với cơ sở dữ liệu và tự động tạo session_title"""
        logger.info(f"Đang khởi tạo phiên: {session_id}")
        
        try:
            # Tự động tạo session_title thông minh
            from utils import generate_smart_session_title
            session_title = generate_smart_session_title(position_title, job_description, required_candidates)
            
            # Tạo phiên trong cơ sở dữ liệu với session_title
            success = db_manager.create_session(
                session_id, 
                job_description, 
                required_candidates, 
                position_title,
                session_title  # Thêm session_title
            )
            
            if not success:
                raise Exception("Không thể tạo phiên trong cơ sở dữ liệu")
            
            # Thêm tin nhắn chat ban đầu với session_title
            self._add_chat_message(
                session_id, 
                'system', 
                f"🎯 Đã tạo phiên: **{session_title}**"
            )
            
            return {
                "session_id": session_id,
                "session_title": session_title,
                "status": "đã khởi tạo",
                "message": f"Phiên '{session_title}' đã được khởi tạo thành công"
            }
            
        except Exception as e:
            logger.error(f"Lỗi khởi tạo phiên: {e}")
            return {
                "session_id": session_id,
                "status": "lỗi",
                "error": str(e)
            }

    def _process_files(self, session_id: str, uploaded_files: List[Dict]) -> Dict:
        """Xử lý các file đã tải lên với lưu trữ cơ sở dữ liệu"""
        logger.info("Đang xử lý các file đã tải lên...")
        
        try:
            self._add_chat_message(
                session_id, 
                'system', 
                f"📁 Đang xử lý {len(uploaded_files)} file đã tải lên..."
            )

            file_ids = []
            
            for file_info in uploaded_files:
                # Thêm file vào cơ sở dữ liệu
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
                    
                    logger.info(f"Đã thêm file {file_info['filename']} với ID {file_id}")
                else:
                    logger.error(f"Không thể thêm file {file_info['filename']} vào cơ sở dữ liệu")

            self._add_chat_message(
                session_id, 
                'system', 
                f"✅ Đã xử lý thành công {len(file_ids)} file"
            )

            return {
                "status": "đã xử lý file",
                "file_ids": file_ids,
                "processed_count": len(file_ids)
            }

        except Exception as e:
            logger.error(f"Lỗi xử lý file: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Lỗi xử lý file: {str(e)}")
            return {"status": "lỗi", "error": str(e)}

    def _extract_text_with_gemini(self, session_id: str, uploaded_files: List[Dict]) -> Dict:
        """Trích xuất văn bản với cập nhật cơ sở dữ liệu"""
        logger.info("Đang trích xuất văn bản với Gemini OCR...")
        
        try:
            self._add_chat_message(
                session_id, 
                'system', 
                "🔍 Bắt đầu trích xuất văn bản với Gemini OCR..."
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
                    f"🔍 [{i}/{total_files}] Đang trích xuất văn bản từ {filename}..."
                )

                # Trích xuất văn bản bằng Gemini
                extracted_text = gemini_ocr.extract_text(file_path)

                if extracted_text and not extracted_text.startswith('Lỗi'):
                    # Cập nhật cơ sở dữ liệu với văn bản đã trích xuất
                    if file_id:
                        db_manager.update_file_extraction(file_id, extracted_text)
                    
                    extracted_data.append({
                        "file_id": file_id,
                        "filename": filename,
                        "extracted_text": extracted_text
                    })
                    
                    logger.info(f"Đã trích xuất thành công văn bản từ {filename}")
                else:
                    logger.warning(f"Không thể trích xuất văn bản từ {filename}")
                    self._add_chat_message(
                        session_id, 
                        'error', 
                        f"❌ Không thể trích xuất văn bản từ {filename}"
                    )

            self._add_chat_message(
                session_id, 
                'system', 
                f"✅ Hoàn thành trích xuất văn bản cho {len(extracted_data)}/{total_files} file"
            )

            return {
                "status": "đã trích xuất văn bản",
                "extracted_data": extracted_data,
                "success_count": len(extracted_data)
            }

        except Exception as e:
            logger.error(f"Lỗi trích xuất văn bản: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Trích xuất văn bản thất bại: {str(e)}")
            return {"status": "lỗi", "error": str(e)}

    def _evaluate_with_gpt(self, session_id: str, job_description: str, extracted_data: List[Dict]) -> Dict:
        """Đánh giá CV với GPT và lưu vào cơ sở dữ liệu"""
        logger.info("Đang đánh giá CV với GPT-3.5-turbo...")
        
        try:
            self._add_chat_message(
                session_id, 
                'system', 
                "🤖 Bắt đầu đánh giá AI với GPT-3.5-turbo..."
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
                    f"🤖 [{i}/{total_cvs}] Đang đánh giá {filename}..."
                )

                # Đánh giá với GPT
                gpt_response = gpt_evaluator.evaluate_cv(job_description, extracted_text)
                parsed_evaluation = gpt_evaluator.extract_json_from_response(gpt_response)

                if parsed_evaluation:
                    score = parsed_evaluation.get("Điểm tổng", 0)
                    is_qualified = parsed_evaluation.get("Phù hợp", "không phù hợp") == "phù hợp"
                    
                    # Lưu đánh giá vào cơ sở dữ liệu
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
                    
                    # Hiển thị kết quả từng cá nhân
                    status = "✅ Đạt yêu cầu" if is_qualified else "❌ Không đạt yêu cầu"
                    self._add_chat_message(
                        session_id, 
                        'result', 
                        f"📊 {filename}: {score:.1f}/10 - {status}"
                    )
                    
                else:
                    logger.warning(f"Không thể phân tích đánh giá cho {filename}")
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
                f"✅ Hoàn thành đánh giá AI cho {len(evaluations)} CV"
            )

            return {
                "status": "đã đánh giá cv",
                "evaluations": evaluations,
                "total_evaluated": len(evaluations)
            }

        except Exception as e:
            logger.error(f"Lỗi đánh giá với GPT: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Đánh giá AI thất bại: {str(e)}")
            return {"status": "lỗi", "error": str(e)}

    def _finalize_results(self, session_id: str, evaluations: List[Dict], required_candidates: int) -> Dict:
        """Hoàn thiện kết quả với tóm tắt cơ sở dữ liệu - FIXED để merge tất cả evaluations"""
        logger.info("Đang hoàn thiện kết quả đánh giá...")

        try:
            # **FIX: Lấy TẤT CẢ evaluations trong session từ database**
            all_session_results = db_manager.get_session_results(session_id)
            
            # Convert database results to evaluation format
            all_evaluations = []
            for result in all_session_results:
                evaluation = {
                    "filename": result.get('filename', ''),
                    "score": result.get('score', 0),
                    "is_qualified": result.get('is_qualified', False),
                    "evaluation_text": result.get('evaluation_json', ''),
                    "extracted_text": result.get('extracted_text', ''),
                    "file_path": result.get('file_path', ''),
                    "evaluation_timestamp": result.get('evaluation_timestamp', '')
                }
                all_evaluations.append(evaluation)
            
            # **FIX: Nếu không có evaluations từ database, sử dụng evaluations hiện tại**
            if not all_evaluations:
                all_evaluations = evaluations
            
            # Sắp xếp đánh giá theo điểm
            sorted_evaluations = sorted(all_evaluations, key=lambda x: x["score"], reverse=True)
            
            # Tính toán thống kê cho TẤT CẢ evaluations
            total_cvs = len(sorted_evaluations)
            qualified_count = sum(1 for e in sorted_evaluations if e["is_qualified"])
            avg_score = sum(e["score"] for e in sorted_evaluations) / total_cvs if total_cvs > 0 else 0
            
            # Tạo cấu trúc kết quả cuối cùng
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

            # Thêm tin nhắn tóm tắt với số liệu chính xác
            self._add_chat_message(
                session_id, 
                'summary', 
                f"📊 Hoàn thành đánh giá: {qualified_count}/{total_cvs} đạt yêu cầu (Trung bình: {avg_score:.1f}/10)"
            )

            logger.info(f"Finalized results: {total_cvs} total CVs, {qualified_count} qualified")

            return {
                "status": "đã hoàn thiện kết quả",
                "final_results": final_results
            }

        except Exception as e:
            logger.error(f"Lỗi hoàn thiện kết quả: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Không thể hoàn thiện kết quả: {str(e)}")
            return {"status": "lỗi", "error": str(e)}

    def run_evaluation(self, session_id: str, job_description: str, required_candidates: int, 
                  uploaded_files: List[Dict], position_title: str = None) -> Dict:
        """Chạy quy trình đánh giá hoàn chỉnh với tích hợp cơ sở dữ liệu - FIXED"""
        try:
            logger.info(f"Bắt đầu quy trình đánh giá cho phiên {session_id}")
            
            # Bước 1: Khởi tạo phiên (chỉ khi chưa tồn tại)
            existing_session = db_manager.get_session(session_id)
            if not existing_session:
                init_result = self._init_session(session_id, job_description, required_candidates, position_title)
                if init_result["status"] == "lỗi":
                    return {"success": False, "error": init_result["error"]}
            
            # Bước 2: Xử lý file
            process_result = self._process_files(session_id, uploaded_files)
            if process_result["status"] == "lỗi":
                return {"success": False, "error": process_result["error"]}
            
            # Bước 3: Trích xuất văn bản
            extract_result = self._extract_text_with_gemini(session_id, uploaded_files)
            if extract_result["status"] == "lỗi":
                return {"success": False, "error": extract_result["error"]}
            
            # Bước 4: Đánh giá với GPT
            eval_result = self._evaluate_with_gpt(session_id, job_description, extract_result["extracted_data"])
            if eval_result["status"] == "lỗi":
                return {"success": False, "error": eval_result["error"]}
            
            # Bước 5: Hoàn thiện kết quả (FIXED - sẽ merge với evaluations có sẵn)
            final_result = self._finalize_results(session_id, eval_result["evaluations"], required_candidates)
            if final_result["status"] == "lỗi":
                return {"success": False, "error": final_result["error"]}

            db_manager._update_session_analytics_comprehensive(session_id)

            # Lấy lịch sử chat từ cơ sở dữ liệu
            chat_history = db_manager.get_chat_history(session_id)

            return {
                "success": True,
                "session_id": session_id,
                "results": final_result["final_results"],
                "chat_history": chat_history,
                "status": "hoàn thành"
            }

        except Exception as e:
            logger.error(f"Lỗi chạy quy trình đánh giá: {e}")
            self._add_chat_message(session_id, 'error', f"❌ Quy trình thất bại: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """Lấy trạng thái phiên từ cơ sở dữ liệu với session_title"""
        try:
            # Lấy thông tin phiên
            session_info = db_manager.get_session(session_id)
            if not session_info:
                return None
            
            # Lấy lịch sử chat
            chat_history = db_manager.get_chat_history(session_id)
            
            # Lấy kết quả đánh giá
            results = db_manager.get_session_results(session_id)
            
            # Lấy phân tích phiên
            analytics = db_manager.get_session_analytics(session_id)
            
            # Chuyển đổi kết quả sang định dạng mong đợi
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
                "session_title": session_info.get('session_title', ''),  # Thêm session_title
                "job_description": session_info.get('job_description', ''),
                "position_title": session_info.get('position_title', ''),
                "required_candidates": session_info.get('required_candidates', 3),
                "final_results": final_results,
                "chat_history": chat_history,
                "processing_status": session_info.get('status', 'đang hoạt động'),
                "analytics": analytics
            }
            
        except Exception as e:
            logger.error(f"Lỗi lấy trạng thái phiên: {e}")
            return None

    def update_session_title(self, session_id: str, new_title: str) -> bool:
        """Cập nhật session title"""
        try:
            success = db_manager.update_session_title(session_id, new_title)
            if success:
                self._add_chat_message(
                    session_id,
                    'system',
                    f"📝 Đã đổi tên phiên thành: **{new_title}**"
                )
            return success
        except Exception as e:
            logger.error(f"Lỗi cập nhật session title: {e}")
            return False

    def get_session_display_info(self, session_id: str) -> Dict:
        """Lấy thông tin hiển thị cho session"""
        try:
            session_state = self.get_session_state(session_id)
            if not session_state:
                return {
                    "display_name": f"Phiên {session_id[:8]}...",
                    "session_title": "",
                    "position_title": "",
                    "created_at": "",
                    "status": "unknown"
                }
            
            # Tạo display name từ session_title hoặc fallback
            session_title = session_state.get('session_title', '')
            position_title = session_state.get('position_title', '')
            
            if session_title:
                display_name = session_title
            elif position_title:
                display_name = f"{position_title} - {session_id[:8]}"
            else:
                display_name = f"Phiên {session_id[:8]}..."
            
            return {
                "display_name": display_name,
                "session_title": session_title,
                "position_title": position_title,
                "created_at": session_state.get('analytics', {}).get('last_activity_timestamp', ''),
                "status": session_state.get('processing_status', 'active'),
                "total_cvs": session_state.get('final_results', {}).get('total_cvs', 0),
                "qualified_count": session_state.get('final_results', {}).get('qualified_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Lỗi lấy session display info: {e}")
            return {
                "display_name": f"Phiên {session_id[:8]}...",
                "session_title": "",
                "position_title": "",
                "created_at": "",
                "status": "error"
            }

    def generate_session_title_suggestions(self, job_description: str, position_title: str = '') -> List[str]:
        """Tạo gợi ý title cho session"""
        try:
            from utils import create_session_title_suggestions
            return create_session_title_suggestions(job_description)
        except Exception as e:
            logger.error(f"Lỗi tạo session title suggestions: {e}")
            return ["Tuyển dụng mới", "Phiên tuyển dụng", "Tìm ứng viên"]

    def search_sessions(self, search_term: str) -> List[Dict]:
        """Tìm kiếm sessions theo title và position"""
        try:
            return db_manager.search_sessions_by_title(search_term)
        except Exception as e:
            logger.error(f"Lỗi tìm kiếm sessions: {e}")
            return []

    def add_chat_message_to_session(self, session_id: str, message_type: str, content: str, sender: str = 'user'):
        """Thêm tin nhắn chat vào phiên (để sử dụng từ bên ngoài)"""
        return self._add_chat_message(session_id, message_type, content, sender)

    def get_session_chat_history(self, session_id: str) -> List[Dict]:
        """Lấy lịch sử chat cho phiên"""
        return db_manager.get_chat_history(session_id)

    def clear_session_chat(self, session_id: str) -> bool:
        """Xóa lịch sử chat cho phiên"""
        return db_manager.clear_chat_history(session_id)

    def generate_comprehensive_report(self, session_id: str) -> str:
        """Tạo báo cáo toàn diện cho phiên"""
        try:
            session_state = self.get_session_state(session_id)
            if not session_state:
                return "Không thể tạo báo cáo: Không tìm thấy phiên"
            
            results = session_state.get('final_results', {})
            if not results:
                return "Không thể tạo báo cáo: Chưa có kết quả đánh giá"
            
            # Tạo báo cáo chi tiết
            report = dedent(f"""\
                📊 BÁO CÁO ĐÁNH GIÁ CV TOÀN DIỆN
                ═══════════════════════════════════════════

                🎯 THÔNG TIN PHIÊN
                • ID Phiên: {session_id}
                • Vị trí tuyển dụng: {session_state.get('position_title', 'N/A')}
                • Số ứng viên cần tuyển: {session_state.get('required_candidates', 'N/A')}
                • Trạng thái: {session_state.get('processing_status', 'N/A')}

                📈 THỐNG KÊ TỔNG QUAN
                • Tổng số CV: {results.get('total_cvs', 0)}
                • Ứng viên đạt yêu cầu: {results.get('qualified_count', 0)}
                • Tỷ lệ đạt yêu cầu: {results.get('summary', {}).get('qualification_rate', 0)}%
                • Điểm trung bình: {results.get('average_score', 0):.2f}/10
                • Điểm cao nhất: {results.get('summary', {}).get('best_score', 0):.2f}/10
                • Điểm thấp nhất: {results.get('summary', {}).get('worst_score', 0):.2f}/10

                🏆 TOP ỨNG VIÊN
            """)
            
            top_candidates = results.get('top_candidates', [])
            for i, candidate in enumerate(top_candidates[:5], 1):
                status = "✅ Đạt" if candidate.get('is_qualified', False) else "❌ Không đạt"
                report += f"{i}. {candidate.get('filename', 'N/A')} - {candidate.get('score', 0):.1f}/10 ({status})\n"
            
            report += dedent(f"""\
                ✅ ỨNG VIÊN ĐẠT YÊU CẦU ({results.get('qualified_count', 0)} người)
            """)
            qualified = results.get('qualified_candidates', [])
            for i, candidate in enumerate(qualified, 1):
                report += f"{i}. {candidate.get('filename', 'N/A')} - {candidate.get('score', 0):.1f}/10\n"
            
            report += dedent(f"""\
                ❌ ỨNG VIÊN KHÔNG ĐẠT YÊU CẦU ({len(results.get('rejected_candidates', []))} người)
            """)
            rejected = results.get('rejected_candidates', [])
            for i, candidate in enumerate(rejected[:10], 1):  # Giới hạn 10 người đầu
                report += f"{i}. {candidate.get('filename', 'N/A')} - {candidate.get('score', 0):.1f}/10\n"
            
            if len(rejected) > 10:
                report += f"... và {len(rejected) - 10} ứng viên khác\n"
            
            # Thêm phân tích từ analytics nếu có
            analytics = session_state.get('analytics', {})
            if analytics:
                report += dedent(f"""\
                    📊 PHÂN TÍCH CHI TIẾT
                    • Tổng file đã tải: {analytics.get('total_files_uploaded', 0)}
                    • File đã xử lý: {analytics.get('total_files_processed', 0)}
                    • Tin nhắn chat: {analytics.get('total_chat_messages', 0)}
                    • Hoạt động cuối: {analytics.get('last_activity_timestamp', 'N/A')}
                """)

            report += dedent(f"""\
                💡 KHUYẾN NGHỊ TUYỂN DỤNG
            """)
            # Tạo khuyến nghị dựa trên dữ liệu
            qualified_rate = results.get('summary', {}).get('qualification_rate', 0)
            avg_score = results.get('average_score', 0)
            
            if qualified_rate >= 50:
                report += "• Chất lượng ứng viên tốt, có nhiều lựa chọn phù hợp\n"
                report += "• Có thể nâng cao tiêu chí để lọc tốt hơn\n"
            elif qualified_rate >= 20:
                report += "• Chất lượng ứng viên trung bình, cần phỏng vấn kỹ\n"
                report += "• Tập trung vào những ứng viên có điểm cao nhất\n"
            else:
                report += "• Ít ứng viên đạt yêu cầu, cần xem xét giảm tiêu chí\n"
                report += "• Mở rộng phạm vi tìm kiếm ứng viên\n"
            
            if avg_score >= 7:
                report += "• Chất lượng ứng viên tổng thể tốt\n"
            elif avg_score >= 5:
                report += "• Chất lượng ứng viên ở mức trung bình\n"
            else:
                report += "• Cần cải thiện nguồn ứng viên\n"
            
            report += dedent(f"""\
                ═══════════════════════════════════════════
                🎯 Báo cáo được tạo bởi CV Evaluator AI
                ⏰ Thời gian: {time.strftime('%d/%m/%Y %H:%M:%S')}
            """)
            
            return report
            
        except Exception as e:
            logger.error(f"Lỗi tạo báo cáo toàn diện: {e}")
            return f"Lỗi tạo báo cáo: {str(e)}"

    def export_session_data(self, session_id: str) -> Dict:
        """Xuất dữ liệu phiên để backup hoặc di chuyển"""
        try:
            session_state = self.get_session_state(session_id)
            if not session_state:
                return {"success": False, "error": "Không tìm thấy phiên"}
            
            # Lấy tất cả dữ liệu liên quan
            files = db_manager.get_session_files(session_id)
            chat_history = db_manager.get_chat_history(session_id)
            analytics = db_manager.get_session_analytics(session_id)
            
            export_data = {
                "session_info": session_state,
                "files": files,
                "chat_history": chat_history,
                "analytics": analytics,
                "export_timestamp": time.time(),
                "export_version": "1.0"
            }
            
            return {"success": True, "data": export_data}
            
        except Exception as e:
            logger.error(f"Lỗi xuất dữ liệu phiên: {e}")
            return {"success": False, "error": str(e)}

    def get_session_statistics(self) -> Dict:
        """Lấy thống kê tổng quan của tất cả phiên"""
        try:
            stats = db_manager.get_database_stats()
            sessions = db_manager.get_all_sessions()
            
            # Tính toán thêm
            active_sessions = len([s for s in sessions if 'completed' not in s.get('status', '')])
            
            return {
                "total_sessions": stats.get('total_sessions', 0),
                "active_sessions": active_sessions,
                "total_cvs_processed": stats.get('total_cvs', 0),
                "total_evaluations": stats.get('total_evaluations', 0),
                "global_average_score": stats.get('average_score', 0),
                "recent_sessions": sessions[:10]  # 10 phiên gần nhất
            }
            
        except Exception as e:
            logger.error(f"Lỗi lấy thống kê phiên: {e}")
            return {"error": str(e)}

# Instance toàn cục
_cv_workflow = None

def get_cv_workflow():
    """Lấy workflow instance (singleton)"""
    global _cv_workflow
    if _cv_workflow is None:
        _cv_workflow = CVEvaluationWorkflow()
    return _cv_workflow

cv_workflow = get_cv_workflow()