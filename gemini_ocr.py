import os
import logging
from PIL import Image
from typing import List, Optional
from google import genai
import fitz
from pathlib import Path

logger = logging.getLogger(__name__)

class GeminiOCR:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Không tìm thấy GOOGLE_API_KEY trong biến môi trường")

        self.model_name = "gemini-2.0-flash-lite"
        self.client = genai.Client(api_key=self.api_key)
        logger.info("Khởi tạo Gemini model thành công")

    def extract_text_from_image(self, image_path: str) -> str:
        """Trích xuất text từ hình ảnh sử dụng Gemini Vision"""
        try:
            image = Image.open(image_path)
            prompt = """
                Bạn là một chuyên gia OCR (Optical Character Recognition) có nhiều năm kinh nghiệm.
                
                Nhiệm vụ: Trích xuất TOÀN BỘ text từ hình ảnh CV/Resume này một cách chính xác nhất.
                
                Yêu cầu cụ thể:
                1. Đọc và trích xuất TẤT CẢ text có trong hình ảnh
                2. Giữ nguyên cấu trúc và định dạng gốc của CV
                3. Bảo toàn thông tin về:
                   - Tên, địa chỉ, thông tin liên lạc
                   - Học vấn và bằng cấp
                   - Kinh nghiệm làm việc
                   - Kỹ năng chuyên môn
                   - Dự án đã tham gia
                   - Chứng chỉ và giải thưởng
                4. Nếu có bảng biểu, hãy chuyển đổi thành format text dễ đọc
                5. Đối với text bị mờ hoặc khó đọc, hãy cố gắng đoán dựa trên ngữ cảnh
                
                LƯU Ý:
                - CHỈ trả về text đã trích xuất, KHÔNG thêm bất kỳ giải thích, nhận xét hay mô tả nào
                - KHÔNG thêm tiêu đề như "Text được trích xuất:", "Nội dung CV:"
                - Giữ nguyên ngôn ngữ gốc (tiếng Việt, tiếng Anh, hoặc hỗn hợp)
                - Nếu không đọc được text nào, trả về: "Không thể đọc được text từ hình ảnh này"
            """

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[image, prompt]
            )

            extracted_text = response.text.strip()
            logger.info(f"Phản hồi OCR từ Gemini: {extracted_text[:200]}...")
            logger.info(f"Trích xuất text từ {Path(image_path).name} thành công")
            return extracted_text
        except Exception as e:
            logger.error(f"Lỗi trích xuất text từ {image_path}: {str(e)}")
            return f"Lỗi trích xuất text từ hình ảnh: {str(e)}"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Trích xuất text từ PDF bằng cách chuyển đổi thành hình ảnh và OCR"""
        extracted_texts = []
        temp_files = []
        
        try:
            doc = fitz.open(pdf_path)
            logger.info(f"Đang xử lý PDF với {len(doc)} trang: {Path(pdf_path).name}")

            for page_num in range(len(doc)):
                logger.info(f"Đang xử lý trang {page_num + 1}/{len(doc)}")
                page = doc.load_page(page_num)

                # Tăng độ phân giải để OCR tốt hơn
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)

                # Tạo thư mục temp
                temp_dir = os.getenv("TEMP_DIR", "./temp")
                os.makedirs(temp_dir, exist_ok=True)
                
                # Lưu hình ảnh tạm thời
                image_path = os.path.join(temp_dir, f"{Path(pdf_path).stem}_trang_{page_num + 1}.jpg")
                pix.save(image_path)
                temp_files.append(image_path)
                
                # Trích xuất text từ hình ảnh
                text = self.extract_text_from_image(image_path)

                if text and not text.startswith("Lỗi") and not text.startswith("Không thể đọc"):
                    extracted_texts.append(f"=== TRANG {page_num + 1} ===\n{text}")
                else:
                    logger.warning(f"Không thể trích xuất text từ trang {page_num + 1}")

            # Ghép tất cả text lại
            if extracted_texts:
                full_text = "\n\n".join(extracted_texts)
                logger.info(f"Trích xuất thành công text từ PDF {Path(pdf_path).name}")
            else:
                full_text = "Không thể trích xuất text từ bất kỳ trang nào của PDF này"
                logger.warning(f"Không thể trích xuất text từ PDF {Path(pdf_path).name}")

            return full_text

        except Exception as e:
            logger.error(f"Lỗi xử lý PDF {pdf_path}: {e}")
            return f"Lỗi trích xuất text từ PDF: {str(e)}"
        
        finally:
            # Dọn dẹp file tạm thời
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.debug(f"Đã xóa file tạm: {temp_file}")
                except Exception as e:
                    logger.warning(f"Không thể xóa file tạm {temp_file}: {e}")

    def extract_text(self, file_path: str) -> str:
        """Trích xuất text từ file (PDF hoặc hình ảnh)"""
        file_ext = Path(file_path).suffix.lower()
        
        logger.info(f"Bắt đầu trích xuất text từ file: {Path(file_path).name}")

        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return self.extract_text_from_image(file_path)
        else:
            error_msg = f"Loại file không được hỗ trợ: {file_ext}. Chỉ hỗ trợ PDF và các file hình ảnh (JPG, PNG, GIF, BMP, TIFF)"
            logger.error(error_msg)
            return error_msg

    def test_connection(self) -> bool:
        """Kiểm tra kết nối với Gemini API"""
        try:
            # Tạo một hình ảnh test đơn giản
            test_image = Image.new('RGB', (100, 50), color='white')
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[test_image, "Đây là test kết nối"]
            )
            
            logger.info("Kiểm tra kết nối Gemini API thành công")
            return True
            
        except Exception as e:
            logger.error(f"Kiểm tra kết nối Gemini API thất bại: {e}")
            return False

# Instance toàn cục
gemini_ocr = GeminiOCR()