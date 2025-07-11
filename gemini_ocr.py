import os
import logging
from PIL import Image
from typing import List, Dict
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
                Bạn là một chuyên gia OCR (Nhận dạng ký tự quang học) có nhiều năm kinh nghiệm trong việc xử lý CV và hồ sơ ứng tuyển.
                
                NHIỆM VỤ: Trích xuất TOÀN BỘ văn bản từ hình ảnh CV/Resume này một cách chính xác và chi tiết nhất.
                
                YÊU CẦU CỤ THỂ:
                1. Đọc và trích xuất TẤT CẢ văn bản có trong hình ảnh
                2. Giữ nguyên cấu trúc và định dạng gốc của CV
                3. Bảo toàn đầy đủ thông tin về:
                   - Họ tên, thông tin liên hệ (email, số điện thoại, địa chỉ)
                   - Mục tiêu nghề nghiệp và tóm tắt bản thân
                   - Học vấn và bằng cấp (tên trường, chuyên ngành, năm tốt nghiệp, GPA/điểm)
                   - Kinh nghiệm làm việc (công ty, vị trí, thời gian, mô tả công việc)
                   - Kỹ năng chuyên môn và kỹ năng mềm
                   - Dự án đã tham gia (tên dự án, vai trò, công nghệ sử dụng)
                   - Chứng chỉ, giải thưởng và thành tích
                   - Hoạt động ngoại khóa và sở thích
                   - Người giới thiệu (nếu có)
                4. Nếu có bảng biểu hoặc danh sách, hãy chuyển đổi thành định dạng văn bản có cấu trúc
                5. Đối với văn bản bị mờ hoặc khó đọc, hãy cố gắng đoán dựa trên ngữ cảnh và kinh nghiệm
                6. Chú ý đặc biệt đến:
                   - Tên công ty, tổ chức
                   - Vị trí công việc và chức danh
                   - Kỹ năng công nghệ và ngôn ngữ lập trình
                   - Thời gian làm việc (tháng/năm)
                   - Điểm số và thành tích học tập
                
                LƯU Ý QUAN TRỌNG:
                - CHỈ trả về văn bản đã trích xuất, KHÔNG thêm bất kỳ giải thích, nhận xét hay mô tả nào
                - KHÔNG thêm tiêu đề như "Văn bản được trích xuất:", "Nội dung CV:", "Kết quả OCR:"
                - Giữ nguyên ngôn ngữ gốc (tiếng Việt, tiếng Anh, hoặc hỗn hợp)
                - Bảo toàn dấu câu, số liệu và định dạng đặc biệt
                - Nếu có nhiều cột, hãy đọc theo thứ tự logic từ trái sang phải, từ trên xuống dưới
                - Nếu hoàn toàn không đọc được văn bản nào, chỉ trả về: "Không thể đọc được văn bản từ hình ảnh này"
                
                HÃY BẮT ĐẦU TRÍCH XUẤT:
            """

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[image, prompt]
            )

            extracted_text = response.text.strip()
            
            # Log phản hồi để debug
            logger.info(f"Phản hồi OCR từ Gemini cho {Path(image_path).name}: {len(extracted_text)} ký tự")
            if len(extracted_text) > 200:
                logger.debug(f"Nội dung trích xuất: {extracted_text[:200]}...")
            else:
                logger.debug(f"Nội dung trích xuất: {extracted_text}")
            
            # Kiểm tra chất lượng kết quả
            if not extracted_text or len(extracted_text.strip()) < 10:
                logger.warning(f"Kết quả OCR cho {Path(image_path).name} có vẻ quá ngắn")
                return "Không thể đọc được đủ thông tin từ hình ảnh này"
            
            logger.info(f"Trích xuất văn bản từ {Path(image_path).name} thành công")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Lỗi trích xuất văn bản từ {image_path}: {str(e)}")
            return f"Lỗi trích xuất văn bản từ hình ảnh: {str(e)}"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Trích xuất văn bản từ PDF bằng cách chuyển đổi thành hình ảnh và OCR"""
        extracted_texts = []
        temp_files = []
        
        try:
            doc = fitz.open(pdf_path)
            logger.info(f"Đang xử lý PDF với {len(doc)} trang: {Path(pdf_path).name}")

            for page_num in range(len(doc)):
                logger.info(f"Đang xử lý trang {page_num + 1}/{len(doc)} của {Path(pdf_path).name}")
                page = doc.load_page(page_num)

                # Tăng độ phân giải để OCR tốt hơn (zoom 2x)
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)

                # Tạo thư mục temp
                temp_dir = os.getenv("TEMP_DIR", "./temp")
                os.makedirs(temp_dir, exist_ok=True)
                
                # Lưu hình ảnh tạm thời với chất lượng cao
                image_path = os.path.join(temp_dir, f"{Path(pdf_path).stem}_trang_{page_num + 1}.jpg")
                pix.save(image_path, quality=95)  # Chất lượng cao
                temp_files.append(image_path)
                
                # Trích xuất văn bản từ hình ảnh
                logger.info(f"Đang OCR trang {page_num + 1}...")
                text = self.extract_text_from_image(image_path)

                if text and not text.startswith("Lỗi") and not text.startswith("Không thể đọc"):
                    extracted_texts.append(f"=== TRANG {page_num + 1} ===\n{text}")
                    logger.info(f"Trích xuất thành công trang {page_num + 1} - {len(text)} ký tự")
                else:
                    logger.warning(f"Không thể trích xuất văn bản từ trang {page_num + 1}")
                    # Vẫn thêm thông tin trang để tránh mất thứ tự
                    extracted_texts.append(f"=== TRANG {page_num + 1} ===\n[Không đọc được nội dung trang này]")

            # Đóng document
            doc.close()

            # Ghép tất cả văn bản lại
            if extracted_texts:
                full_text = "\n\n".join(extracted_texts)
                
                # Kiểm tra chất lượng kết quả tổng thể
                useful_content = [t for t in extracted_texts if not "[Không đọc được" in t]
                if useful_content:
                    logger.info(f"Trích xuất thành công văn bản từ PDF {Path(pdf_path).name} - {len(useful_content)}/{len(extracted_texts)} trang")
                else:
                    logger.warning(f"Không thể trích xuất văn bản hữu ích từ bất kỳ trang nào của PDF {Path(pdf_path).name}")
                    full_text = f"Không thể trích xuất văn bản hữu ích từ PDF này. File có thể bị hỏng, quét chất lượng thấp hoặc không chứa văn bản."
            else:
                full_text = "Không thể trích xuất văn bản từ bất kỳ trang nào của PDF này"
                logger.error(f"Hoàn toàn không thể trích xuất văn bản từ PDF {Path(pdf_path).name}")

            return full_text

        except Exception as e:
            logger.error(f"Lỗi xử lý PDF {pdf_path}: {e}")
            return f"Lỗi trích xuất văn bản từ PDF: {str(e)}. Vui lòng kiểm tra file có thể mở được và không bị bảo vệ."
        
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
        """Trích xuất văn bản từ file (PDF hoặc hình ảnh)"""
        file_ext = Path(file_path).suffix.lower()
        
        logger.info(f"Bắt đầu trích xuất văn bản từ file: {Path(file_path).name} (loại: {file_ext})")

        # Kiểm tra file tồn tại
        if not os.path.exists(file_path):
            error_msg = f"File không tồn tại: {file_path}"
            logger.error(error_msg)
            return error_msg

        # Kiểm tra kích thước file
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            error_msg = f"File rỗng: {Path(file_path).name}"
            logger.error(error_msg)
            return error_msg
        
        # Log kích thước file
        size_mb = file_size / (1024 * 1024)
        logger.info(f"Kích thước file: {size_mb:.2f} MB")

        # Xử lý theo loại file
        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            return self.extract_text_from_image(file_path)
        else:
            error_msg = f"Loại file không được hỗ trợ: {file_ext}. Chỉ hỗ trợ PDF và các file hình ảnh (JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP)"
            logger.error(error_msg)
            return error_msg

    def batch_extract_text(self, file_paths: List[str]) -> Dict[str, str]:
        """Trích xuất văn bản từ nhiều file cùng lúc"""
        results = {}
        
        logger.info(f"Bắt đầu trích xuất văn bản từ {len(file_paths)} file")
        
        for i, file_path in enumerate(file_paths, 1):
            logger.info(f"Đang xử lý file {i}/{len(file_paths)}: {Path(file_path).name}")
            
            try:
                extracted_text = self.extract_text(file_path)
                results[file_path] = extracted_text
                
                # Log kết quả
                if extracted_text.startswith("Lỗi") or extracted_text.startswith("Không thể"):
                    logger.warning(f"Không thành công: {Path(file_path).name}")
                else:
                    logger.info(f"Thành công: {Path(file_path).name} - {len(extracted_text)} ký tự")
                    
            except Exception as e:
                error_msg = f"Lỗi xử lý file {Path(file_path).name}: {str(e)}"
                logger.error(error_msg)
                results[file_path] = error_msg
        
        successful = sum(1 for text in results.values() if not (text.startswith("Lỗi") or text.startswith("Không thể")))
        logger.info(f"Hoàn thành batch OCR: {successful}/{len(file_paths)} file thành công")
        
        return results

    def test_connection(self) -> bool:
        """Kiểm tra kết nối với Gemini API"""
        try:
            # Tạo một hình ảnh test đơn giản với văn bản
            from PIL import Image, ImageDraw, ImageFont
            
            # Tạo ảnh test 200x100 với nền trắng
            test_image = Image.new('RGB', (200, 100), color='white')
            draw = ImageDraw.Draw(test_image)
            
            # Thêm văn bản test
            try:
                # Thử sử dụng font hệ thống
                font = ImageFont.load_default()
            except:
                font = None
            
            draw.text((10, 40), "TEST OCR", fill='black', font=font)
            
            # Test với Gemini
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[test_image, "Đọc văn bản trong hình ảnh này"]
            )
            
            result_text = response.text.strip()
            
            # Kiểm tra xem có đọc được "TEST" không
            if "TEST" in result_text.upper():
                logger.info("Kiểm tra kết nối Gemini API thành công")
                return True
            else:
                logger.warning(f"Gemini API hoạt động nhưng kết quả OCR không chính xác: {result_text}")
                return False
            
        except Exception as e:
            logger.error(f"Kiểm tra kết nối Gemini API thất bại: {e}")
            return False

    def analyze_image_quality(self, image_path: str) -> Dict[str, any]:
        """Phân tích chất lượng hình ảnh cho OCR"""
        try:
            image = Image.open(image_path)
            
            # Lấy thông tin cơ bản
            width, height = image.size
            mode = image.mode
            
            # Tính toán megapixels
            megapixels = (width * height) / 1_000_000
            
            # Đánh giá chất lượng
            quality_score = 0
            recommendations = []
            
            # Kiểm tra kích thước
            if width < 800 or height < 600:
                recommendations.append("Hình ảnh có độ phân giải thấp, có thể ảnh hưởng đến chất lượng OCR")
                quality_score += 1
            elif width >= 1500 and height >= 1200:
                quality_score += 3
            else:
                quality_score += 2
            
            # Kiểm tra chế độ màu
            if mode == 'L':  # Grayscale
                quality_score += 2
                recommendations.append("Hình ảnh grayscale - tốt cho OCR")
            elif mode == 'RGB':
                quality_score += 2
            else:
                recommendations.append("Chế độ màu có thể không tối ưu cho OCR")
                quality_score += 1
            
            # Đánh giá tổng thể
            if quality_score >= 4:
                overall_quality = "Tốt"
            elif quality_score >= 3:
                overall_quality = "Khá"
            else:
                overall_quality = "Cần cải thiện"
            
            return {
                "filename": Path(image_path).name,
                "dimensions": f"{width}x{height}",
                "megapixels": round(megapixels, 2),
                "color_mode": mode,
                "quality_score": quality_score,
                "overall_quality": overall_quality,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Lỗi phân tích chất lượng hình ảnh {image_path}: {e}")
            return {
                "filename": Path(image_path).name,
                "error": str(e)
            }

    def enhance_image_for_ocr(self, image_path: str, output_path: str = None) -> str:
        """Cải thiện hình ảnh để OCR tốt hơn"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            
            image = Image.open(image_path)
            
            # Chuyển về grayscale nếu cần
            if image.mode != 'L':
                image = image.convert('L')
            
            # Tăng độ tương phản
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Tăng độ sắc nét
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Áp dụng bộ lọc để giảm nhiễu
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Tạo đường dẫn output
            if output_path is None:
                base_path = Path(image_path)
                output_path = base_path.parent / f"{base_path.stem}_enhanced{base_path.suffix}"
            
            # Lưu hình ảnh đã cải thiện
            image.save(output_path, quality=95)
            
            logger.info(f"Đã cải thiện hình ảnh: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Lỗi cải thiện hình ảnh {image_path}: {e}")
            return image_path  # Trả về đường dẫn gốc nếu lỗi

    def get_supported_formats(self) -> List[str]:
        """Lấy danh sách định dạng file được hỗ trợ"""
        return [
            '.pdf',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
        ]

    def validate_file(self, file_path: str) -> Dict[str, any]:
        """Xác thực file trước khi xử lý"""
        file_path = Path(file_path)
        
        validation_result = {
            "is_valid": False,
            "filename": file_path.name,
            "issues": []
        }
        
        # Kiểm tra file tồn tại
        if not file_path.exists():
            validation_result["issues"].append("File không tồn tại")
            return validation_result
        
        # Kiểm tra extension
        if file_path.suffix.lower() not in self.get_supported_formats():
            validation_result["issues"].append(f"Định dạng file không được hỗ trợ: {file_path.suffix}")
            return validation_result
        
        # Kiểm tra kích thước file
        file_size = file_path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        
        if file_size == 0:
            validation_result["issues"].append("File rỗng")
            return validation_result
        elif file_size > max_size:
            validation_result["issues"].append(f"File quá lớn (>{max_size/1024/1024:.1f}MB)")
            return validation_result
        
        # Nếu là hình ảnh, kiểm tra thêm
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            try:
                image = Image.open(file_path)
                width, height = image.size
                
                if width < 100 or height < 100:
                    validation_result["issues"].append("Hình ảnh quá nhỏ (dưới 100x100)")
                elif width > 10000 or height > 10000:
                    validation_result["issues"].append("Hình ảnh quá lớn (trên 10000x10000)")
                
                image.close()
                
            except Exception as e:
                validation_result["issues"].append(f"Không thể mở hình ảnh: {str(e)}")
                return validation_result
        
        # Nếu không có lỗi
        if not validation_result["issues"]:
            validation_result["is_valid"] = True
            validation_result["file_size_mb"] = round(file_size / 1024 / 1024, 2)
        
        return validation_result

# Instance toàn cục
gemini_ocr = GeminiOCR()