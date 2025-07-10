import os
import logging
import torch
from typing import Optional
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)
from textwrap import dedent
import json

logger = logging.getLogger(__name__)

class VietnameseLlamaEvaluator:
    def __init__(self):
        self.model_name = os.getenv("VIETNAMESE_LLAMA_MODEL", "VietnamAIHub/Vietnamese_llama2_7B_8K_SFT_General_domain")
        self.model = None
        self.tokenizer = None
        self.stop_token_ids = [0]
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Initializing Vietnamese LLaMa on {self.device}")
        self._load_model()

    def _load_model(self):
        """Load model with quantization"""
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )

            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=os.getenv("CACHE_DIR", "./cache"),
                padding_side="right",
                use_fast=False,
                tokenizer_type='llama',
                token=os.getenv("HF_KEY")
            )

            self.tokenizer.bos_token_id = 1

            logger.info("Loading model with quantization...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=bnb_config,
                device_map="auto",
                torch_dtype=torch.float16,
                pretraining_tp=1,
                cache_dir=os.getenv("CACHE_DIR", "./cache"),
                trust_remote_code=True,
                use_fast=False,
                low_cpu_mem_usage=True,
                token=os.getenv("HF_KEY")
            )

            self.model.eval()
            logger.info("Vietnamese LLaMA model loaded successfully with quantization")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    def _create_evaluation_prompt(self, job_description: str, cv_text: str) -> str:
        """Create evaluation prompt for the model"""
        prompt = dedent(f"""<s>[INST] Bạn là một chuyên gia tuyển dụng. Hãy đánh giá CV sau đây dựa trên yêu cầu công việc và trả về kết quả theo định dạng JSON.
            YÊU CẦU CÔNG VIỆC:
            {job_description}
            THÔNG TIN CV:
            {cv_text}
            Hãy đánh giá CV theo các tiêu chí sau và trả về kết quả JSON:
            1. Phù hợp với yêu cầu công việc (40%)
            2. Kinh nghiệm làm việc (30%)
            3. Kỹ năng chuyên môn (20%)
            4. Học vấn và chứng chỉ (10%)
            Trả lời theo định dạng JSON sau:
            {{
                "overall_score": [điểm từ 0-10],
                "is_qualified": [true/false],
                "criteria_scores": {{
                    "job_fit": [điểm 0-10],
                    "experience": [điểm 0-10],
                    "skills": [điểm 0-10],
                    "education": [điểm 0-10]
                }},
                "strengths": ["điểm mạnh 1", "điểm mạnh 2"],
                "weaknesses": ["điểm yếu 1", "điểm yếu 2"],
                "summary": "tóm tắt đánh giá ngắn gọn"
            }}
            Chỉ trả về JSON, không thêm giải thích khác. [/INST]
        """)

        return prompt

    def evaluate_cv(self, job_description: str, cv_text: str) -> str:
        """Evaluate CV and return result"""
        try:
            if not self.model or not self.tokenizer:
                raise Exception("Model not loaded")

            prompt = self._create_evaluation_prompt(job_description=job_description, cv_text=cv_text)

            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=6000,
                padding=True
            )

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=1000,
                    temperature=0.3,
                    do_sample=True,
                    top_p=0.9,
                    top_k=50,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            # Decode response
            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            )

            logger.info("Successfully evaluated CV with Vietnamese LLaMA")
            return response.strip()

        except Exception as e:
            logger.error(f"Error evaluating CV: {e}")
            return f"Error during evaluation: {str(e)}"

    def extract_json_from_response(self, response: str) -> Optional[dict]:
        """Extract JSON from model response"""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)

            return None

        except Exception as e:
            logger.warning(f"Failed to extract JSON: {e}")
            return None

_vietnamese_llama = None

def get_vietnamese_llama():
    """Get Vietnamese LLaMA instance (singleton)"""
    global _vietnamese_llama
    if _vietnamese_llama is None:
        _vietnamese_llama = VietnameseLlamaEvaluator()
    return _vietnamese_llama