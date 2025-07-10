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
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.model_name = "gemini-2.0-flash-lite"
        self.client = genai.Client(api_key=self.api_key)
        logger.info("Gemini model initialized successfully")

    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using Gemini Vision"""
        try:
            image = Image.open(image_path)
            prompt = """
                Hãy trích xuất toàn bộ text từ hình ảnh CV này.
                Trả về text một cách chính xác, giữ nguyên cấu trúc và định dạng.
                Không thêm bất kỳ giải thích hay nhận xét nào, chỉ trả về text đã trích xuất.
            """

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[image, prompt]
            )

            extracted_text = response.text.strip()
            logger.info(f"Response OCR: {extracted_text}")
            logger.info(f"Extracted text from {Path(image_path).name} successfully")
            return extracted_text
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {str(e)}")
            return f"Error extracting text: {str(e)}"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF by converting to images and OCR"""
        extracted_texts = []
        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)

                temp_dir = os.getenv("TEMP_DIR", "./temp")
                os.makedirs(temp_dir, exist_ok=True)
                image_path = os.path.join(temp_dir, f"{Path(pdf_path).stem}_page_{page_num + 1}.jpg")
                pix.save(image_path)
                text = self.extract_text_from_image(image_path)

                if text and not text.startswith("Error"):
                    extracted_texts.append(text)

                try:
                    os.remove(image_path)
                except:
                    pass

            full_text = "\n\n".join(extracted_texts)
            logger.info(f"Response OCR: {full_text}")
            logger.info(f"Successfully extracted text from PDF {Path(pdf_path).name} via OCR")
            return full_text

        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return f"Error extracting text from PDF: {str(e)}"

    def extract_text(self, file_path: str) -> str:
        """Extract text from file (PDF or image)"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return self.extract_text_from_image(file_path)
        else:
            return f"Unsupported file type: {file_ext}"

# Global instance
gemini_ocr = GeminiOCR()