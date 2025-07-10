import os
import json
import logging
from typing import Dict, List, TypedDict, Any, Iterator
from pathlib import Path
from langgraph.graph import StateGraph, END
from gemini_ocr import gemini_ocr
from vietnamese_llama import get_vietnamese_llama
from database import db_manager
from openai import OpenAI

logger = logging.getLogger(__name__)

class CVEvaluationState(TypedDict):
    """State for CV evaluation workflow"""
    session_id: str
    job_description: str
    required_candidates: int
    uploaded_files: List[Dict[str, Any]]
    extracted_texts: List[Dict[str, Any]]
    llama_evaluations: List[Dict[str, Any]]
    final_results: Dict[str, Any]
    error: str

class CVEvaluationWorkflow:
    def __init__(self):
        self.graph = self._create_graph()
        self.openai_client = self._init_openai_client()

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

    def _create_graph(self) -> StateGraph:
        """Create the workflow graph"""
        workflow = StateGraph(CVEvaluationState)

        # Add nodes
        workflow.add_node("process_files", self._process_files)
        workflow.add_node("extract_text", self._extract_text_with_gemini)
        workflow.add_node("evaluate_with_llama", self._evaluate_with_vietnamese_llama)
        workflow.add_node("finalize_results", self._finalize_results)

        # Add edges
        workflow.set_entry_point("process_files")
        workflow.add_edge("process_files", "extract_text")
        workflow.add_edge("extract_text", "evaluate_with_llama")
        workflow.add_edge("evaluate_with_llama", "finalize_results")
        workflow.add_edge("finalize_results", END)

        return workflow.compile()

    def _process_files(self, state: CVEvaluationState) -> CVEvaluationState:
        """Process uploaded files and save to database"""
        logger.info("Processing uploaded files...")

        try:
            # Create session in database
            db_manager.create_session(
                state["session_id"],
                state["job_description"],
                state["required_candidates"]
            )

            # Add files to database
            for file_info in state["uploaded_files"]:
                cv_id = db_manager.add_cv(
                    state["session_id"],
                    file_info["filename"],
                    file_info["path"],
                    file_info["type"]
                )
                file_info["cv_id"] = cv_id

            logger.info(f"Processed {len(state['uploaded_files'])} files")

        except Exception as e:
            logger.error(f"Error processing files: {e}")
            state["error"] = f"Error processing files: {str(e)}"

        return state

    def _extract_text_with_gemini(self, state: CVEvaluationState) -> CVEvaluationState:
        """Extract text from files using Gemini OCR"""
        logger.info("Extracting text with Gemini OCR...")
        extracted_texts = []

        try:
            for file_info in state["uploaded_files"]:
                logger.info(f"Extracting text from {file_info['filename']}")

                extracted_text = gemini_ocr.extract_text(file_info["path"])

                text_data = {
                    "cv_id": file_info["cv_id"],
                    "filename": file_info["filename"],
                    "extracted_text": extracted_text
                }

                extracted_texts.append(text_data)

                db_manager.update_cv_info(file_info["cv_id"], extracted_text)

                logger.info(f"Extracted text from {file_info['filename']}")

            state["extracted_texts"] = extracted_texts
            logger.info(f"Successfully extracted text from {len(extracted_texts)} files")

        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            state["error"] = f"Error extracting text: {str(e)}"

        return state

    def _evaluate_with_vietnamese_llama(self, state: CVEvaluationState) -> CVEvaluationState:
        """Evaluate CVs using Vietnamese LLaMA"""
        logger.info("Evaluating CVs with Vietnamese LLaMA...")
        evaluations = []

        try:
            llama_model = get_vietnamese_llama()

            for text_data in state["extracted_texts"]:
                logger.info(f"Evaluating {text_data['filename']} with Vietnamese LLaMA")

                extracted_text = text_data.get('extracted_text', '')
                if not extracted_text or extracted_text.startswith('Error'):
                    evaluation_data = {
                        "cv_id": text_data["cv_id"],
                        "filename": text_data["filename"],
                        "llama_response": "Không thể trích xuất text từ CV",
                        "parsed_evaluation": None
                    }
                    evaluations.append(evaluation_data)
                    continue

                llama_response = llama_model.evaluate_cv(
                    state["job_description"],
                    extracted_text
                )

                parsed_evaluation = llama_model.extract_json_from_response(llama_response)

                evaluation_data = {
                    "cv_id": text_data["cv_id"],
                    "filename": text_data["filename"],
                    "llama_response": llama_response,
                    "parsed_evaluation": parsed_evaluation
                }

                evaluations.append(evaluation_data)
                logger.info(f"Evaluated {text_data['filename']} with LLaMA")

            state["llama_evaluations"] = evaluations
            logger.info(f"Completed LLaMA evaluation for {len(evaluations)} CVs")

        except Exception as e:
            logger.error(f"Error evaluating with LLaMA: {e}")
            state["error"] = f"Error evaluating with LLaMA: {str(e)}"

        return state

    def _finalize_results(self, state: CVEvaluationState) -> CVEvaluationState:
        """Finalize results and save to database"""
        logger.info("Finalizing results...")

        try:
            final_evaluations = []

            for evaluation in state["llama_evaluations"]:
                parsed_eval = evaluation.get("parsed_evaluation")

                if parsed_eval:
                    score = parsed_eval.get("overall_score", 0)
                    is_qualified = parsed_eval.get("is_qualified", False)
                    evaluation_text = json.dumps(parsed_eval, ensure_ascii=False, indent=2)
                else:
                    score = 5.0
                    is_qualified = False
                    evaluation_text = evaluation["llama_response"]

                final_evaluation = {
                    "cv_id": evaluation["cv_id"],
                    "filename": evaluation["filename"],
                    "score": score,
                    "is_qualified": is_qualified,
                    "evaluation_text": evaluation_text,
                    "llama_response": evaluation["llama_response"]
                }

                final_evaluations.append(final_evaluation)

                db_manager.add_evaluation(
                    state["session_id"],
                    evaluation["cv_id"],
                    score,
                    evaluation_text,
                    is_qualified
                )

            final_evaluations.sort(key=lambda x: x["score"], reverse=True)

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
                }
            }

            state["final_results"] = final_results
            logger.info(f"Finalized results: {qualified_cvs}/{total_cvs} qualified, avg score: {avg_score:.2f}")

        except Exception as e:
            logger.error(f"Error finalizing results: {e}")
            state["error"] = f"Error finalizing results: {str(e)}"

        return state

    def run_evaluation(self, session_id: str, job_description: str, required_candidates: int, uploaded_files: List[Dict]) -> Dict:
        """Run the complete evaluation workflow"""
        try:
            initial_state = CVEvaluationState(
                session_id=session_id,
                job_description=job_description,
                required_candidates=required_candidates,
                uploaded_files=uploaded_files,
                extracted_texts=[],
                llama_evaluations=[],
                final_results={},
                error=""
            )

            result = self.graph.invoke(initial_state)

            if result.get("error"):
                return {"success": False, "error": result["error"]}

            return {
                "success": True,
                "results": result["final_results"],
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Error running evaluation workflow: {e}")
            return {"success": False, "error": str(e)}

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
                "top_candidates": evaluation_results.get("top_candidates", [])[:3]  # Top 3 only
            }

            prompt = f"""
                Bạn là một chuyên gia tuyển dụng. Dựa trên kết quả đánh giá CV, hãy tạo một báo cáo tóm tắt chuyên nghiệp.

                THÔNG TIN TUYỂN DỤNG:
                {job_description}

                KẾT QUẢ ĐÁNH GIÁ:
                - Tổng số CV: {summary_data['total_cvs']}
                - Số CV đạt yêu cầu: {summary_data['qualified_count']}
                - Điểm trung bình: {summary_data['average_score']}/10
                - Tỷ lệ đạt yêu cầu: {evaluation_results.get('summary', {}).get('qualification_rate', 0)}%

                TOP ỨNG VIÊN:
                {json.dumps(summary_data['top_candidates'], ensure_ascii=False, indent=2)}

                Hãy viết một báo cáo tóm tắt bao gồm:
                1. Nhận xét chung về chất lượng ứng viên
                2. Phân tích điểm mạnh/yếu của pool ứng viên
                3. Khuyến nghị cho quá trình tuyển dụng
                4. Đánh giá chi tiết top 3 ứng viên

                Viết một cách chuyên nghiệp, rõ ràng và hữu ích cho nhà tuyển dụng.
            """

            messages = [
                {"role": "system", "content": "Bạn là một chuyên gia tuyển dụng chuyên nghiệp, có kinh nghiệm sâu về đánh giá và tuyển chọn nhân tài."},
                {"role": "user", "content": prompt}
            ]

            stream = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=2000,
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

cv_workflow = CVEvaluationWorkflow()