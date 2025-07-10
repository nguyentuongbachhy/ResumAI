import os
import json
import logging
from typing import Dict, List, TypedDict, Any
from pathlib import Path
import fitz
from langgraph.graph import StateGraph, END
from vintern_api import vintern_processor
from database import db_manager

logger = logging.getLogger(__name__)

class CVEvaluationState(TypedDict):
    """State for CV evaluation workflow"""
    session_id: str
    job_description: str
    required_candidates: int
    uploaded_files: List[Dict[str, Any]]
    processed_files: List[Dict[str, Any]]
    extracted_cvs: List[Dict[str, Any]]
    evaluations: List[Dict[str, Any]]
    final_results: Dict[str, Any]
    error: str

class CVEvaluationWorkflow:
    def __init__(self):
        self.graph = self._create_graph()
        self.openai_client = None
        self._init_openai_client()
    
    def _init_openai_client(self):
        """Initialize OpenAI client"""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("OpenAI API key not found in environment variables")
                return
            
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
    
    def _create_graph(self) -> StateGraph:
        """Create the workflow graph"""
        workflow = StateGraph(CVEvaluationState)
        
        # Add nodes
        workflow.add_node("process_files", self._process_files)
        workflow.add_node("extract_cv_info", self._extract_cv_info)
        workflow.add_node("evaluate_cvs", self._evaluate_cvs)
        workflow.add_node("finalize_results", self._finalize_results)
        
        # Add edges
        workflow.set_entry_point("process_files")
        workflow.add_edge("process_files", "extract_cv_info")
        workflow.add_edge("extract_cv_info", "evaluate_cvs")
        workflow.add_edge("evaluate_cvs", "finalize_results")
        workflow.add_edge("finalize_results", END)
        
        return workflow.compile()
    
    def _process_files(self, state: CVEvaluationState) -> CVEvaluationState:
        """Process uploaded files (convert PDF to images)"""
        logger.info("Processing uploaded files...")
        processed_files = []
        
        try:
            for file_info in state["uploaded_files"]:
                file_path = file_info["path"]
                file_type = file_info["type"]
                filename = file_info["filename"]
                
                logger.info(f"Processing file: {filename} ({file_type})")
                
                if file_type == "application/pdf":
                    # Convert PDF to images
                    try:
                        images = self._pdf_to_images(file_path)
                        for i, image_path in enumerate(images):
                            processed_files.append({
                                "filename": f"{Path(filename).stem}_page_{i+1}.jpg",
                                "path": image_path,
                                "type": "image/jpeg",
                                "original_filename": filename,
                                "page": i + 1
                            })
                            
                            # Add to database
                            cv_id = db_manager.add_cv(
                                state["session_id"],
                                f"{Path(filename).stem}_page_{i+1}.jpg",
                                image_path,
                                "image/jpeg"
                            )
                            processed_files[-1]["cv_id"] = cv_id
                    except Exception as e:
                        logger.error(f"Error processing PDF {filename}: {e}")
                        # Still add the original file for processing
                        processed_files.append({
                            "filename": filename,
                            "path": file_path,
                            "type": file_type,
                            "original_filename": filename,
                            "page": 1,
                            "error": f"PDF processing failed: {str(e)}"
                        })
                        
                        cv_id = db_manager.add_cv(
                            state["session_id"],
                            filename,
                            file_path,
                            file_type
                        )
                        processed_files[-1]["cv_id"] = cv_id
                        
                elif file_type.startswith("image/"):
                    # Direct image file
                    processed_files.append({
                        "filename": filename,
                        "path": file_path,
                        "type": file_type,
                        "original_filename": filename,
                        "page": 1
                    })
                    
                    # Add to database
                    cv_id = db_manager.add_cv(
                        state["session_id"],
                        filename,
                        file_path,
                        file_type
                    )
                    processed_files[-1]["cv_id"] = cv_id
                else:
                    logger.warning(f"Unsupported file type: {file_type} for {filename}")
            
            state["processed_files"] = processed_files
            logger.info(f"Processed {len(processed_files)} files")
            
        except Exception as e:
            logger.error(f"Error processing files: {e}")
            state["error"] = f"Error processing files: {str(e)}"
            
        return state
    
    def _extract_cv_info(self, state: CVEvaluationState) -> CVEvaluationState:
        """Extract information from CV images using Vintern API"""
        logger.info("Extracting CV information...")
        extracted_cvs = []
        
        try:
            # Prepare question for extraction
            question = """Trích xuất thông tin chi tiết từ CV này bao gồm:
            1. Thông tin cá nhân (tên, email, số điện thoại, địa chỉ)
            2. Kinh nghiệm làm việc (công ty, vị trí, thời gian, mô tả công việc)
            3. Kỹ năng và chuyên môn
            4. Học vấn và bằng cấp
            5. Chứng chỉ và khóa học
            6. Dự án đã thực hiện
            7. Ngôn ngữ lập trình (nếu có)
            8. Các thông tin khác liên quan
            
            Trả lời bằng tiếng Việt, định dạng rõ ràng và chi tiết."""
            
            # Filter out files with errors
            valid_files = [f for f in state["processed_files"] if "error" not in f]
            error_files = [f for f in state["processed_files"] if "error" in f]
            
            # Handle error files
            for file_info in error_files:
                cv_data = {
                    "cv_id": file_info["cv_id"],
                    "filename": file_info["filename"],
                    "original_filename": file_info["original_filename"],
                    "page": file_info["page"],
                    "extracted_info": f"Error: {file_info.get('error', 'Unknown error')}"
                }
                extracted_cvs.append(cv_data)
                
                # Update database
                db_manager.update_cv_info(file_info["cv_id"], cv_data["extracted_info"])
            
            if not valid_files:
                state["extracted_cvs"] = extracted_cvs
                logger.warning("No valid files to process")
                return state
            
            # Try batch processing first (more efficient) but only for images
            image_files = [f for f in valid_files if f["type"].startswith("image/")]
            
            if len(image_files) > 1:
                logger.info(f"Attempting batch processing for {len(image_files)} image files")
                try:
                    file_paths = [file_info["path"] for file_info in image_files]
                    batch_results = vintern_processor.batch_extract(file_paths, question)
                    
                    if batch_results and isinstance(batch_results, dict):
                        # Process batch results
                        batch_processed = set()
                        
                        for file_info in image_files:
                            filename = file_info["filename"]
                            file_path = file_info["path"]
                            
                            # Try multiple ways to match the result
                            extracted_info = None
                            
                            # 1. Try exact filename match
                            if filename in batch_results:
                                extracted_info = batch_results[filename]
                            # 2. Try path basename match
                            elif Path(file_path).name in batch_results:
                                extracted_info = batch_results[Path(file_path).name]
                            # 3. Try original filename variations
                            elif file_info["original_filename"] in batch_results:
                                extracted_info = batch_results[file_info["original_filename"]]
                            # 4. Try finding by partial match
                            else:
                                for key, value in batch_results.items():
                                    if filename in key or key in filename:
                                        extracted_info = value
                                        break
                            
                            if extracted_info and not extracted_info.startswith('Error:'):
                                cv_data = {
                                    "cv_id": file_info["cv_id"],
                                    "filename": filename,
                                    "original_filename": file_info["original_filename"],
                                    "page": file_info["page"],
                                    "extracted_info": extracted_info
                                }
                                
                                extracted_cvs.append(cv_data)
                                batch_processed.add(filename)
                                
                                # Update database
                                db_manager.update_cv_info(file_info["cv_id"], extracted_info)
                                
                                logger.info(f"Batch extracted info for {filename}")
                            else:
                                logger.warning(f"No valid batch result found for {filename}")
                        
                        # Remove successfully processed files from the list for individual processing
                        valid_files = [f for f in valid_files if f["filename"] not in batch_processed]
                        
                        logger.info(f"Batch processing completed for {len(batch_processed)} files")
                        
                except Exception as e:
                    logger.warning(f"Batch processing error: {e}, falling back to individual processing")
            
            # Individual processing (fallback or for remaining files)
            if valid_files:
                logger.info(f"Individual processing for {len(valid_files)} files")
                
                for file_info in valid_files:
                    logger.info(f"Individual processing {file_info['filename']}")
                    
                    try:
                        extracted_info = vintern_processor.extract_info(
                            file_info["path"],
                            question=question
                        )
                        
                        logger.debug(f"Extracted info for {file_info['filename']}: {extracted_info[:200]}...")
                        
                        cv_data = {
                            "cv_id": file_info["cv_id"],
                            "filename": file_info["filename"],
                            "original_filename": file_info["original_filename"],
                            "page": file_info["page"],
                            "extracted_info": extracted_info
                        }
                        
                        extracted_cvs.append(cv_data)
                        
                        # Update database
                        db_manager.update_cv_info(file_info["cv_id"], extracted_info)
                        
                        logger.info(f"Individual extracted info for {file_info['filename']}")
                        
                    except Exception as e:
                        logger.error(f"Error extracting info from {file_info['filename']}: {e}")
                        
                        error_info = f"Error: Failed to extract info - {str(e)}"
                        cv_data = {
                            "cv_id": file_info["cv_id"],
                            "filename": file_info["filename"],
                            "original_filename": file_info["original_filename"],
                            "page": file_info["page"],
                            "extracted_info": error_info
                        }
                        
                        extracted_cvs.append(cv_data)
                        
                        # Update database
                        db_manager.update_cv_info(file_info["cv_id"], error_info)
            
            state["extracted_cvs"] = extracted_cvs
            logger.info(f"Successfully extracted information from {len(extracted_cvs)} CVs")
            
        except Exception as e:
            logger.error(f"Error extracting CV info: {e}")
            state["error"] = f"Error extracting CV info: {str(e)}"
            
        return state
    
    def _stream_openai_response(self, messages: List[Dict], model: str = "gpt-4") -> str:
        """Generate streaming response from OpenAI"""
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            
            logger.info(f"Starting streaming response with model: {model}")
            
            # Create streaming response
            stream = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500,
                temperature=0.3,
                stream=True
            )
            
            # Collect streamed response
            full_response = ""
            for chunk in stream:
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        full_response += delta.content
                        # Optional: log progress for debugging
                        # logger.debug(f"Received chunk: {delta.content}")
            
            logger.info(f"Streaming completed. Total length: {len(full_response)} characters")
            return full_response.strip()
            
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            raise
    
    def _evaluate_cvs(self, state: CVEvaluationState) -> CVEvaluationState:
        """Evaluate CVs using OpenAI with streaming"""
        logger.info("Evaluating CVs with OpenAI streaming...")
        evaluations = []
        
        try:
            # Check if OpenAI client is available
            if not self.openai_client:
                logger.error("OpenAI client not initialized")
                state["error"] = "OpenAI client not configured"
                return state
            
            for cv_data in state["extracted_cvs"]:
                logger.info(f"Evaluating {cv_data['filename']}")
                
                # Skip if no extracted info or error in extraction
                extracted_info = cv_data.get('extracted_info', '')
                if not extracted_info or extracted_info.startswith('Error:') or extracted_info == "No content extracted":
                    logger.warning(f"Skipping {cv_data['filename']} - no valid extracted info: {extracted_info}")
                    
                    evaluation_data = {
                        "cv_id": cv_data["cv_id"],
                        "filename": cv_data["filename"],
                        "score": 0.0,
                        "evaluation_text": "Không thể trích xuất thông tin từ CV hoặc có lỗi xảy ra",
                        "is_passed": False
                    }
                    
                    evaluations.append(evaluation_data)
                    
                    # Save to database
                    db_manager.add_evaluation(
                        state["session_id"],
                        cv_data["cv_id"],
                        0.0,
                        "Không thể trích xuất thông tin từ CV hoặc có lỗi xảy ra",
                        False
                    )
                    continue
                
                # Create evaluation prompt
                prompt = f"""
                Bạn là một chuyên gia tuyển dụng. Hãy đánh giá CV sau đây dựa trên yêu cầu công việc.

                YÊU CẦU CÔNG VIỆC:
                {state['job_description']}

                THÔNG TIN CV:
                {extracted_info}

                Hãy đánh giá CV này theo các tiêu chí:
                1. Phù hợp với yêu cầu công việc (40%)
                2. Kinh nghiệm làm việc (30%)
                3. Kỹ năng chuyên môn (20%)
                4. Học vấn và chứng chỉ (10%)

                Trả lời theo định dạng JSON:
                {{
                    "score": [điểm từ 0-10],
                    "is_passed": [true/false],
                    "evaluation": {{
                        "strengths": ["điểm mạnh 1", "điểm mạnh 2", ...],
                        "weaknesses": ["điểm yếu 1", "điểm yếu 2", ...],
                        "job_fit": "mức độ phù hợp với công việc",
                        "recommendation": "khuyến nghị"
                    }},
                    "detailed_analysis": "phân tích chi tiết"
                }}
                """
                
                # Prepare messages for streaming
                messages = [
                    {
                        "role": "system", 
                        "content": "Bạn là một chuyên gia tuyển dụng chuyên nghiệp. Hãy trả lời chính xác theo định dạng JSON được yêu cầu."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
                
                try:
                    # Use streaming response
                    response_content = self._stream_openai_response(messages, model="gpt-4")
                    
                    logger.debug(f"Streaming response for {cv_data['filename']}: {response_content[:200]}...")
                    
                    try:
                        # Try to extract JSON from response
                        if response_content.startswith('```json'):
                            json_start = response_content.find('{')
                            json_end = response_content.rfind('}') + 1
                            json_content = response_content[json_start:json_end]
                        else:
                            json_content = response_content
                        
                        evaluation_result = json.loads(json_content)
                        score = float(evaluation_result.get("score", 0))
                        is_passed = bool(evaluation_result.get("is_passed", False))
                        evaluation_text = json.dumps(evaluation_result, ensure_ascii=False, indent=2)
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Failed to parse JSON response for {cv_data['filename']}: {e}")
                        # Fallback evaluation
                        evaluation_text = response_content
                        score = 5.0  # Default score
                        is_passed = False
                    
                except Exception as e:
                    logger.error(f"Error calling OpenAI API for {cv_data['filename']}: {e}")
                    evaluation_text = f"Lỗi khi đánh giá: {str(e)}"
                    score = 0.0
                    is_passed = False
                
                evaluation_data = {
                    "cv_id": cv_data["cv_id"],
                    "filename": cv_data["filename"],
                    "score": score,
                    "evaluation_text": evaluation_text,
                    "is_passed": is_passed
                }
                
                evaluations.append(evaluation_data)
                
                # Save to database
                db_manager.add_evaluation(
                    state["session_id"],
                    cv_data["cv_id"],
                    score,
                    evaluation_text,
                    is_passed
                )
                
                logger.info(f"Evaluated {cv_data['filename']} - Score: {score}")
            
            state["evaluations"] = evaluations
            logger.info(f"Evaluated {len(evaluations)} CVs using streaming")
            
        except Exception as e:
            logger.error(f"Error evaluating CVs: {e}")
            state["error"] = f"Error evaluating CVs: {str(e)}"
            
        return state
    
    def _finalize_results(self, state: CVEvaluationState) -> CVEvaluationState:
        """Finalize and summarize results"""
        logger.info("Finalizing results...")
        
        try:
            evaluations = state.get("evaluations", [])
            
            # Sort by score
            evaluations.sort(key=lambda x: x["score"], reverse=True)
            
            # Calculate statistics
            total_cvs = len(evaluations)
            passed_cvs = [e for e in evaluations if e["is_passed"]]
            passed_count = len(passed_cvs)
            
            avg_score = sum(e["score"] for e in evaluations) / total_cvs if total_cvs > 0 else 0
            
            # Get top candidates
            required_count = state["required_candidates"]
            top_candidates = evaluations[:required_count]
            
            final_results = {
                "total_cvs": total_cvs,
                "passed_count": passed_count,
                "average_score": round(avg_score, 2),
                "top_candidates": top_candidates,
                "all_evaluations": evaluations,
                "summary": {
                    "best_score": evaluations[0]["score"] if evaluations else 0,
                    "worst_score": evaluations[-1]["score"] if evaluations else 0,
                    "pass_rate": round(passed_count / total_cvs * 100, 1) if total_cvs > 0 else 0
                }
            }
            
            state["final_results"] = final_results
            logger.info(f"Finalized results: {passed_count}/{total_cvs} passed, avg score: {avg_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error finalizing results: {e}")
            state["error"] = f"Error finalizing results: {str(e)}"
            
        return state
    
    def _pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF to images"""
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert to image
                mat = fitz.Matrix(2, 2)  # 2x zoom
                pix = page.get_pixmap(matrix=mat)
                
                # Save as image
                image_path = f"{pdf_path}_page_{page_num + 1}.jpg"
                pix.save(image_path)
                images.append(image_path)
                
                logger.debug(f"Converted page {page_num + 1} of {pdf_path} to {image_path}")
                
            doc.close()
            logger.info(f"Successfully converted PDF {pdf_path} to {len(images)} images")
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise
            
        return images
    
    def run_evaluation(self, session_id: str, job_description: str, required_candidates: int, uploaded_files: List[Dict]) -> Dict:
        """Run the complete evaluation workflow"""
        try:
            # Create session in database
            db_manager.create_session(session_id, job_description, required_candidates)
            
            # Initial state
            initial_state = CVEvaluationState(
                session_id=session_id,
                job_description=job_description,
                required_candidates=required_candidates,
                uploaded_files=uploaded_files,
                processed_files=[],
                extracted_cvs=[],
                evaluations=[],
                final_results={},
                error=""
            )
            
            # Run workflow
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

# Global workflow instance
cv_workflow = CVEvaluationWorkflow()