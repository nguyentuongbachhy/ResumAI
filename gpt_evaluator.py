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
            raise ValueError("Không tìm thấy OPENAI_API_KEY trong biến môi trường")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.model_name = "gpt-3.5-turbo"
        
        # Ngưỡng điểm đậu được giảm xuống 6.5
        self.PASS_THRESHOLD = 6.5
        
        logger.info("Khởi tạo GPT-3.5-turbo evaluator thành công với ngưỡng đậu: 6.5 điểm")

    def _create_evaluation_prompt(self, job_description: str, cv_text: str) -> str:
        """Tạo prompt đánh giá cho GPT bằng tiếng Việt với ngưỡng 6.5 điểm"""
        prompt = dedent(f"""
        Bạn là một chuyên gia tuyển dụng có kinh nghiệm 10+ năm tại Việt Nam. Hãy đánh giá CV sau đây dựa trên yêu cầu công việc và trả về kết quả theo định dạng JSON chính xác bằng tiếng Việt.

        YÊU CẦU CÔNG VIỆC:
        {job_description}

        THÔNG TIN CV:
        {cv_text}

        Hãy đánh giá CV theo các tiêu chí sau với trọng số:
        1. Mức độ phù hợp với yêu cầu công việc (40%)
        2. Kinh nghiệm làm việc và dự án (30%) 
        3. Kỹ năng chuyên môn và công nghệ (20%)
        4. Học vấn và chứng chỉ (10%)

        QUAN TRỌNG: Ngưỡng đậu là 6.5 điểm. Ứng viên đạt từ 6.5 điểm trở lên được coi là "phù hợp", dưới 6.5 điểm là "không phù hợp".

        Trả lời CHÍNH XÁC theo định dạng JSON sau, không thêm text khác:
        {{
            "Điểm tổng": điểm từ 0-10 (số thập phân, VD: 7.5),
            "Phù hợp": "phù hợp" hoặc "không phù hợp" (dựa trên ngưỡng 6.5 điểm),
            "Các tiêu chí": {{
                "Điểm phù hợp": [điểm 0-10],
                "Điểm kinh nghiệm": [điểm 0-10],
                "Điểm kĩ năng": [điểm 0-10],
                "Điểm giáo dục": [điểm 0-10]
            }},
            "Điểm mạnh": ["điểm mạnh cụ thể 1", "điểm mạnh cụ thể 2", "điểm mạnh cụ thể 3"],
            "Điểm yếu": ["điểm yếu cụ thể 1", "điểm yếu cụ thể 2"],
            "Tổng kết": "tóm tắt đánh giá chi tiết và chuyên nghiệp trong 2-3 câu bằng tiếng Việt"
        }}

        Lưu ý quan trọng:
        - CHỈ trả về JSON hợp lệ, không có text bổ sung trước hoặc sau
        - Đánh giá công bằng, khách quan dựa trên dữ liệu thực tế
        - Điểm số phải phản ánh chính xác mức độ phù hợp với yêu cầu
        - Từ 6.5 điểm trở lên = "phù hợp", dưới 6.5 điểm = "không phù hợp"
        - Điểm mạnh và điểm yếu phải cụ thể và có căn cứ từ CV
        - Tổng kết phải súc tích, chuyên nghiệp bằng tiếng Việt
        - Trả lời bằng tiếng Việt
        - KHÔNG được bịa đặt thông tin không có trong CV
        - Nếu CV bằng tiếng Anh, hãy đánh giá và trả lời bằng tiếng Việt
        - Luôn sử dụng tiếng Việt trong tất cả các phần của JSON
        - Hãy linh hoạt với ngưỡng 6.5 - ưu tiên những ứng viên có tiềm năng phát triển
        """)
        
        return prompt

    def evaluate_cv(self, job_description: str, cv_text: str) -> str:
        """Đánh giá CV sử dụng GPT-3.5-turbo với ngưỡng 6.5 điểm"""
        try:
            prompt = self._create_evaluation_prompt(job_description, cv_text)
            
            messages = [
                {
                    "role": "system", 
                    "content": f"Bạn là một chuyên gia tuyển dụng chuyên nghiệp tại Việt Nam với 10+ năm kinh nghiệm. Bạn luôn trả về kết quả đánh giá dưới dạng JSON chính xác bằng tiếng Việt, không thêm bất kỳ text nào khác. Bạn đánh giá khách quan, công bằng và chỉ dựa trên thông tin thực tế có trong CV. Ngưỡng đậu là {self.PASS_THRESHOLD} điểm. Luôn sử dụng tiếng Việt cho tất cả nội dung trong JSON."
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
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"Phản hồi từ GPT: {result}")
            
            # Kiểm tra định dạng JSON và xử lý logic đậu/rớt
            try:
                parsed_result = json.loads(result)
                
                # Double-check logic đậu/rớt dựa trên ngưỡng 6.5
                score = parsed_result.get("Điểm tổng", 0)
                is_qualified = score >= self.PASS_THRESHOLD
                
                # Cập nhật trường "Phù hợp" dựa trên logic mới
                parsed_result["Phù hợp"] = "phù hợp" if is_qualified else "không phù hợp"
                
                # Trả về JSON đã được điều chỉnh
                final_result = json.dumps(parsed_result, ensure_ascii=False, indent=2)
                
                logger.info(f"Đánh giá CV thành công với GPT-3.5-turbo. Điểm: {score}, Ngưỡng: {self.PASS_THRESHOLD}, Kết quả: {'Đậu' if is_qualified else 'Rớt'}")
                return final_result
                
            except json.JSONDecodeError:
                logger.warning("Phản hồi GPT không phải JSON hợp lệ, đang cố gắng trích xuất JSON")
                return self._extract_json_from_text(result)
                
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá CV với GPT: {e}")
            return self._create_fallback_evaluation(str(e))

    def _extract_json_from_text(self, text: str) -> str:
        """Trích xuất JSON từ text nếu nó được nhúng trong nội dung khác"""
        try:
            # Tìm khối JSON
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                parsed_json = json.loads(json_str)
                
                # Áp dụng logic ngưỡng 6.5
                score = parsed_json.get("Điểm tổng", 0)
                is_qualified = score >= self.PASS_THRESHOLD
                parsed_json["Phù hợp"] = "phù hợp" if is_qualified else "không phù hợp"
                
                return json.dumps(parsed_json, ensure_ascii=False, indent=2)
            
            # Nếu không tìm thấy JSON hợp lệ, tạo đánh giá dự phòng
            return self._create_fallback_evaluation("Không thể trích xuất JSON hợp lệ từ phản hồi")
            
        except Exception as e:
            logger.error(f"Lỗi trích xuất JSON: {e}")
            return self._create_fallback_evaluation(str(e))

    def _create_fallback_evaluation(self, error_msg: str) -> str:
        """Tạo đánh giá dự phòng khi GPT thất bại - bằng tiếng Việt với ngưỡng 6.5"""
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
            "Điểm yếu": ["Không thể phân tích chi tiết do lỗi hệ thống"],
            "Tổng kết": f"Có lỗi xảy ra trong quá trình đánh giá: {error_msg}. Vui lòng thử lại. (Ngưỡng đậu: {self.PASS_THRESHOLD} điểm)"
        }
        
        return json.dumps(fallback, ensure_ascii=False, indent=2)

    def extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Trích xuất JSON từ phản hồi của model với logic ngưỡng 6.5"""
        try:
            # Thử phân tích phản hồi trực tiếp
            parsed_result = json.loads(response)
            
            # Áp dụng logic ngưỡng 6.5
            score = parsed_result.get("Điểm tổng", 0)
            is_qualified = score >= self.PASS_THRESHOLD
            parsed_result["Phù hợp"] = "phù hợp" if is_qualified else "không phù hợp"
            
            return parsed_result
            
        except json.JSONDecodeError:
            try:
                # Thử trích xuất JSON từ text
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    parsed_result = json.loads(json_str)
                    
                    # Áp dụng logic ngưỡng 6.5
                    score = parsed_result.get("Điểm tổng", 0)
                    is_qualified = score >= self.PASS_THRESHOLD
                    parsed_result["Phù hợp"] = "phù hợp" if is_qualified else "không phù hợp"
                    
                    return parsed_result
                
                logger.warning("Không tìm thấy JSON trong phản hồi, tạo đánh giá mặc định")
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
                    "Tổng kết": f"Không thể phân tích JSON từ phản hồi của model (Ngưỡng đậu: {self.PASS_THRESHOLD} điểm)"
                }
                
            except Exception as e:
                logger.error(f"Lỗi trích xuất JSON: {e}")
                return None

    def batch_evaluate_cvs(self, job_description: str, cv_texts: list) -> list:
        """Đánh giá nhiều CV theo lô để tăng hiệu quả"""
        results = []
        
        logger.info(f"Bắt đầu đánh giá batch với {len(cv_texts)} CV - Ngưỡng đậu: {self.PASS_THRESHOLD} điểm")
        
        for i, cv_text in enumerate(cv_texts):
            logger.info(f"Đang đánh giá CV {i+1}/{len(cv_texts)}")
            
            try:
                result = self.evaluate_cv(job_description, cv_text)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Lỗi đánh giá CV {i+1}: {e}")
                results.append(self._create_fallback_evaluation(str(e)))
        
        # Thống kê kết quả batch
        qualified_count = 0
        total_score = 0
        
        for result in results:
            try:
                parsed = json.loads(result)
                score = parsed.get("Điểm tổng", 0)
                total_score += score
                if score >= self.PASS_THRESHOLD:
                    qualified_count += 1
            except:
                pass
        
        avg_score = total_score / len(results) if results else 0
        logger.info(f"Kết quả batch: {qualified_count}/{len(results)} đậu (ngưỡng {self.PASS_THRESHOLD}), điểm TB: {avg_score:.2f}")
        
        return results

    def test_connection(self) -> bool:
        """Kiểm tra kết nối với OpenAI API"""
        try:
            test_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": f"Bạn là trợ lý AI hữu ích với ngưỡng đánh giá {self.PASS_THRESHOLD} điểm."},
                    {"role": "user", "content": "Xin chào! Đây là test kết nối."}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            logger.info(f"Kiểm tra kết nối OpenAI API thành công - Ngưỡng đậu: {self.PASS_THRESHOLD}")
            return True
            
        except Exception as e:
            logger.error(f"Kiểm tra kết nối OpenAI API thất bại: {e}")
            return False

    def create_detailed_prompt(self, job_description: str, cv_text: str, focus_areas: list = None) -> str:
        """Tạo prompt chi tiết với các khu vực tập trung cụ thể và ngưỡng 6.5"""
        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nKhu vực cần chú ý đặc biệt: {', '.join(focus_areas)}"
        
        detailed_prompt = dedent(f"""
        Bạn là chuyên gia tuyển dụng hàng đầu tại Việt Nam với chuyên môn sâu về đánh giá ứng viên.
        
        NGƯỠNG ĐÁNH GIÁ: {self.PASS_THRESHOLD} điểm trở lên = ĐẬU, dưới {self.PASS_THRESHOLD} điểm = RỚT
        
        YÊU CẦU CÔNG VIỆC CHI TIẾT:
        {job_description}{focus_text}
        
        THÔNG TIN CV ỨNG VIÊN:
        {cv_text}
        
        Hãy thực hiện đánh giá toàn diện và trả về kết quả JSON chi tiết bao gồm:
        
        1. PHÂN TÍCH KỸ NĂNG CHUYÊN MÔN
        2. ĐÁNH GIÁ KINH NGHIỆM THỰC TẾ  
        3. PHÂN TÍCH MỨC ĐỘ PHÙ HỢP VỚI VĂN HÓA CÔNG TY
        4. DỰ ĐOÁN HIỆU SUẤT CÔNG VIỆC
        5. KHUYẾN NGHỊ PHỎNG VẤN
        
        Định dạng JSON trả về (bằng tiếng Việt):
        {{
            "Điểm tổng": [0-10],
            "Phù hợp": "phù hợp/không phù hợp" (dựa trên ngưỡng {self.PASS_THRESHOLD} điểm),
            "Phân tích chi tiết": {{
                "Kỹ năng chuyên môn": {{
                    "Điểm": [0-10],
                    "Nhận xét": "nhận xét chi tiết",
                    "Kỹ năng nổi bật": ["kỹ năng 1", "kỹ năng 2"],
                    "Kỹ năng còn thiếu": ["thiếu 1", "thiếu 2"]
                }},
                "Kinh nghiệm": {{
                    "Điểm": [0-10],
                    "Năm kinh nghiệm": số năm,
                    "Dự án nổi bật": ["dự án 1", "dự án 2"],
                    "Mức độ phù hợp": "thấp/trung bình/cao"
                }},
                "Học vấn": {{
                    "Điểm": [0-10],
                    "Trình độ": "mô tả trình độ",
                    "Chứng chỉ": ["chứng chỉ 1", "chứng chỉ 2"]
                }}
            }},
            "Điểm mạnh": ["điểm mạnh 1", "điểm mạnh 2", "điểm mạnh 3"],
            "Điểm yếu": ["điểm yếu 1", "điểm yếu 2"],
            "Khuyến nghị": {{
                "Nên phỏng vấn": true/false (dựa trên ngưỡng {self.PASS_THRESHOLD}),
                "Vị trí phù hợp": "tên vị trí phù hợp",
                "Mức lương đề xuất": "khoảng lương",
                "Câu hỏi phỏng vấn đề xuất": ["câu hỏi 1", "câu hỏi 2", "câu hỏi 3"]
            }},
            "Tổng kết": "tóm tắt chi tiết bằng tiếng Việt với đề cập đến ngưỡng {self.PASS_THRESHOLD} điểm"
        }}
        
        LƯU Ý: 
        - Chỉ trả về JSON hợp lệ, sử dụng tiếng Việt cho toàn bộ nội dung
        - Từ {self.PASS_THRESHOLD} điểm trở lên = "phù hợp", dưới {self.PASS_THRESHOLD} = "không phù hợp"
        - Hãy linh hoạt và ưu tiên tiềm năng phát triển của ứng viên
        """)
        
        return detailed_prompt

    def evaluate_cv_detailed(self, job_description: str, cv_text: str, focus_areas: list = None) -> str:
        """Đánh giá CV chi tiết với ngưỡng 6.5 điểm"""
        try:
            prompt = self.create_detailed_prompt(job_description, cv_text, focus_areas)
            
            messages = [
                {
                    "role": "system",
                    "content": f"Bạn là chuyên gia tuyển dụng hàng đầu tại Việt Nam. Cung cấp đánh giá CV chi tiết, chuyên nghiệp và khách quan bằng tiếng Việt. Luôn trả về JSON hợp lệ. Ngưỡng đậu là {self.PASS_THRESHOLD} điểm."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=2000,
                temperature=0.2
            )
            
            result = response.choices[0].message.content.strip()
            
            # Kiểm tra và áp dụng logic ngưỡng 6.5
            try:
                parsed_result = json.loads(result)
                score = parsed_result.get("Điểm tổng", 0)
                is_qualified = score >= self.PASS_THRESHOLD
                
                # Cập nhật các trường liên quan
                parsed_result["Phù hợp"] = "phù hợp" if is_qualified else "không phù hợp"
                
                if "Khuyến nghị" in parsed_result:
                    parsed_result["Khuyến nghị"]["Nên phỏng vấn"] = is_qualified
                
                return json.dumps(parsed_result, ensure_ascii=False, indent=2)
                
            except json.JSONDecodeError:
                return self._extract_json_from_text(result)
                
        except Exception as e:
            logger.error(f"Lỗi đánh giá CV chi tiết: {e}")
            return self._create_fallback_evaluation(str(e))

    def get_pass_threshold(self) -> float:
        """Lấy ngưỡng điểm đậu hiện tại"""
        return self.PASS_THRESHOLD

    def set_pass_threshold(self, new_threshold: float) -> bool:
        """Đặt ngưỡng điểm đậu mới"""
        try:
            if 0 <= new_threshold <= 10:
                old_threshold = self.PASS_THRESHOLD
                self.PASS_THRESHOLD = new_threshold
                logger.info(f"Đã thay đổi ngưỡng đậu từ {old_threshold} thành {self.PASS_THRESHOLD}")
                return True
            else:
                logger.error(f"Ngưỡng không hợp lệ: {new_threshold}. Phải từ 0-10")
                return False
        except Exception as e:
            logger.error(f"Lỗi đặt ngưỡng mới: {e}")
            return False

# Instance toàn cục
_gpt_evaluator = None

def get_gpt_evaluator():
    """Lấy instance GPT evaluator (singleton)"""
    global _gpt_evaluator
    if _gpt_evaluator is None:
        _gpt_evaluator = GPTEvaluator()
    return _gpt_evaluator