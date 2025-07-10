import os
import logging
import json
from typing import Optional, Dict, Any
from openai import OpenAI
from textwrap import dedent

logger = logging.getLogger(__name__)

class GPTEvaluator:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.model_name = "gpt-3.5-turbo"
        
        logger.info("GPT-3.5-turbo evaluator initialized successfully")

    def _create_evaluation_prompt(self, job_description: str, cv_text: str) -> str:
        """Create evaluation prompt for GPT"""
        prompt = dedent(f"""
        Bạn là một chuyên gia tuyển dụng có kinh nghiệm 10+ năm. Hãy đánh giá CV sau đây dựa trên yêu cầu công việc và trả về kết quả theo định dạng JSON chính xác.

        YÊU CẦU CÔNG VIỆC:
        {job_description}

        THÔNG TIN CV:
        {cv_text}

        Hãy đánh giá CV theo các tiêu chí sau với trọng số:
        1. Phù hợp với yêu cầu công việc (40%)
        2. Kinh nghiệm làm việc (30%) 
        3. Kỹ năng chuyên môn (20%)
        4. Học vấn và chứng chỉ (10%)

        Trả lời CHÍNH XÁC theo định dạng JSON sau, không thêm text khác:
        {{
            "Điểm tổng": [điểm từ 0-10, số thập phân],
            "Phù hợp": [phù hợp/không phù hợp],
            "Các tiêu chí": {{
                "Điểm phù hợp": [điểm 0-10],
                "Điểm kinh nghiệm": [điểm 0-10],
                "Điểm kĩ năng": [điểm 0-10],
                "Điểm giáo dục": [điểm 0-10]
            }},
            "Điểm mạnh": ["điểm mạnh cụ thể 1", "điểm mạnh cụ thể 2", "điểm mạnh cụ thể 3"],
            "Điểm yếu": ["điểm yếu cụ thể 1", "điểm yếu cụ thể 2"],
            "Tổng kết": "tóm tắt đánh giá chi tiết và chuyên nghiệp"
        }}

        Lưu ý:
        - Chỉ trả về JSON hợp lệ, không có text bổ sung
        - Đánh giá công bằng và khách quan
        - Điểm số phải phản ánh chính xác mức độ phù hợp
        - Điểm mạnh và điểm yếu phải cụ thể và có căn cứ
        - Trả về tiếng việt
        - Không được bịa ra, chỉ dựa vào dữ liệu thực tế để trả lời
        """)
        
        return prompt

    def evaluate_cv(self, job_description: str, cv_text: str) -> str:
        """Evaluate CV using GPT-3.5-turbo"""
        try:
            prompt = self._create_evaluation_prompt(job_description, cv_text)
            
            messages = [
                {
                    "role": "system", 
                    "content": "Bạn là một chuyên gia tuyển dụng chuyên nghiệp. Bạn luôn trả về kết quả đánh giá dưới dạng JSON chính xác và không thêm bất kỳ text nào khác."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1500,
                temperature=0.3,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Validate JSON response
            try:
                json.loads(result)
                logger.info("Successfully evaluated CV with GPT-3.5-turbo")
                return result
            except json.JSONDecodeError:
                logger.warning("GPT response was not valid JSON, attempting to extract JSON")
                return self._extract_json_from_text(result)
                
        except Exception as e:
            logger.error(f"Error evaluating CV with GPT: {e}")
            return self._create_fallback_evaluation(str(e))

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text if it's embedded in other content"""
        try:
            # Find JSON block
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                # Validate extracted JSON
                json.loads(json_str)
                return json_str
            
            # If no valid JSON found, create fallback
            return self._create_fallback_evaluation("Could not extract valid JSON from response")
            
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            return self._create_fallback_evaluation(str(e))

    def _create_fallback_evaluation(self, error_msg: str) -> str:
        """Create fallback evaluation when GPT fails"""
        fallback = {
            "Điểm tổng": 0,
            "Phù hợp": "không phù hợp",
            "Các tiêu chí": {
                "Điểm phù hợp": 0,
                "Điểm kinh nghiệm": 0,
                "Điểm kĩ năng": 0,
                "Điểm giáo dục": 0
            },
            "Điểm mạnh": ["Cần đánh giá thêm"],
            "Điểm yếu": ["Không thể phân tích chi tiết"],
            "Tổng kết": f"Có lỗi xảy ra trong quá trình đánh giá: {error_msg}"
        }
        
        return json.dumps(fallback, ensure_ascii=False, indent=2)

    def extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from model response"""
        try:
            # First try to parse the response directly
            return json.loads(response)
            
        except json.JSONDecodeError:
            try:
                # Try to extract JSON from text
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    return json.loads(json_str)
                
                logger.warning("No JSON found in response, creating default evaluation")
                return {
                    "Điểm tổng": 0,
                    "Phù hợp": "không phù hợp",
                    "Các tiêu chí": {
                        "Điểm phù hợp": 0,
                        "Điểm kinh nghiệm": 0,
                        "Điểm kĩ năng": 0,
                        "Điểm giáo dục": 0
                    },
                    "Điểm mạnh": ["Cần đánh giá thêm"],
                    "Điểm yếu": ["Không thể phân tích chi tiết"],
                    "Tổng kết": "Không thể phân tích JSON từ phản hồi của model"
                }
                
            except Exception as e:
                logger.error(f"Error extracting JSON: {e}")
                return None

    def batch_evaluate_cvs(self, job_description: str, cv_texts: list) -> list:
        """Evaluate multiple CVs in batch for better efficiency"""
        results = []
        
        for i, cv_text in enumerate(cv_texts):
            logger.info(f"Evaluating CV {i+1}/{len(cv_texts)}")
            
            try:
                result = self.evaluate_cv(job_description, cv_text)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error evaluating CV {i+1}: {e}")
                results.append(self._create_fallback_evaluation(str(e)))
        
        return results

    def test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            logger.info("OpenAI API connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"OpenAI API connection test failed: {e}")
            return False

# Global instance
_gpt_evaluator = None

def get_gpt_evaluator():
    """Get GPT evaluator instance (singleton)"""
    global _gpt_evaluator
    if _gpt_evaluator is None:
        _gpt_evaluator = GPTEvaluator()
    return _gpt_evaluator