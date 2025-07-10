# ================================================================================
# VIETNAMESE LLAMA EVALUATOR - COMMENTED OUT
# ================================================================================
# 
# This file has been commented out to use GPT-3.5-turbo instead for better
# performance and reliability. The original LLaMA implementation is preserved
# for reference and can be uncommented if needed in the future.
#
# Replaced by: gpt_evaluator.py
# Date: [Current Date]
# Reason: Better performance, faster response times, more reliable JSON parsing
# ================================================================================

"""
import os
import logging
import torch
from typing import Optional
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    LlamaTokenizer,
    LlamaForCausalLM
)
from textwrap import dedent
import json

logger = logging.getLogger(__name__)

class VietnameseLlamaEvaluator:
    def __init__(self):
        self.finetuned_model_path = os.getenv("FINETUNED_LLAMA_MODEL", "./train/finetuned_model")
        self.original_model_name = os.getenv("VIETNAMESE_LLAMA_MODEL", "VietnamAIHub/Vietnamese_llama2_7B_8K_SFT_General_domain")

        self.model = None
        self.tokenizer = None
        self.stop_token_ids = [0]
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Initializing Vietnamese LLaMa on {self.device}")
        self._load_model()

    def _check_local_model_exists(self, model_path: str) -> bool:
        # Check if local finetuned model exists
        try:
            if os.path.isdir(model_path):
                config_file = os.path.join(model_path, "config.json")
                model_files = [
                    "pytorch_model.bin",
                    "model.safetensors",
                    "adapter_model.bin",
                    "adapter_model.safetensors"
                ]

                if os.path.exists(config_file):
                    for model_file in model_files:
                        if os.path.exists(os.path.join(model_path, model_file)):
                            logger.info(f"Found local finetuned model at: {model_path}")
                            return True

            logger.warning(f"Local model not found at: {model_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking local model: {e}")
            return False

    def _load_tokenizer(self, model_path: str, is_local: bool = False) -> bool:
        # Load tokenizer with error handling
        try:
            logger.info(f"Loading tokenizer from: {model_path}")

            tokenizer_kwargs = {
                "padding_side": "right",
                "use_fast": False,
                "trust_remote_code": True,
                "legacy": False
            }

            if not is_local:
                tokenizer_kwargs.update({
                    "cache_dir": os.getenv("CACHE_DIR", "./cache"),
                    "token": os.getenv("HF_KEY")
                })

            tokenizer_classes = [AutoTokenizer, LlamaTokenizer]

            for TokenizerClass in tokenizer_classes:
                try:
                    self.tokenizer = TokenizerClass.from_pretrained(
                        model_path,
                        **tokenizer_kwargs
                    )

                    if not hasattr(self.tokenizer, 'pad_token') or self.tokenizer.pad_token is None:
                        self.tokenizer.pad_token = self.tokenizer.eos_token

                    if not hasattr(self.tokenizer, 'pad_token_id') or self.tokenizer.pad_token_id is None:
                        self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

                    try:
                        if hasattr(self.tokenizer, 'bos_token_id') and self.tokenizer.bos_token_id is not None:
                            pass
                        else:
                            self.tokenizer.bos_token_id = 1
                    except Exception as e:
                        logger.warning(f"Could not set bos_token_id: {e}")
                    logger.info(f"Successfully loaded tokenizer using {TokenizerClass.__name__}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to load tokenizer with {TokenizerClass.__name__}: {e}")
                    continue
            return False

        except Exception as e:
            logger.error(f"Error loading tokenizer: {e}")
            return False

    def _load_model_with_quantization(self, model_path: str, is_local: bool = False) -> bool:
        # Load model with quantization
        try:
            logger.info(f"Loading model from: {model_path}")

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )

            model_kwargs = {
                "quantization_config": bnb_config,
                "device_map": "auto",
                "torch_dtype": torch.float16,
                "trust_remote_code": True,
                "low_cpu_mem_usage": True,
            }

            if not is_local:
                model_kwargs.update({
                    "cache_dir": os.getenv("CACHE_DIR", "./cache"),
                    "token": os.getenv("HF_KEY")
                })

            model_classes = [AutoModelForCausalLM, LlamaForCausalLM]

            for ModelClass in model_classes:
                try:
                    self.model = ModelClass.from_pretrained(
                        model_path,
                        **model_kwargs
                    )

                    self.model.eval()
                    logger.info(f"Successfully loaded model using {ModelClass.__name__}")
                    return True

                except Exception as e:
                    logger.warning(f"Failed to load model with {ModelClass.__name__}: {e}")
                    continue

            return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def _load_model(self):
        # Load model with fallback strategy
        try:
            if self._check_local_model_exists(self.finetuned_model_path):
                logger.info("Attempting to load local finetuned model...")

                if (self._load_tokenizer(self.finetuned_model_path, is_local=True) and 
                    self._load_model_with_quantization(self.finetuned_model_path, is_local=True)):
                    logger.info("Successfully loaded local finetuned model")
                    return
                else:
                    logger.warning("Failed to load local finetuned model, falling back to original")

            logger.info("Loading original model from HuggingFace...")

            if (self._load_tokenizer(self.original_model_name, is_local=False) and 
                self._load_model_with_quantization(self.original_model_name, is_local=False)):
                logger.info("Successfully loaded original model from HuggingFace")
                return

            logger.warning("Attempting to load without quantization...")

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.original_model_name,
                cache_dir=os.getenv("CACHE_DIR", "./cache"),
                padding_side="right",
                use_fast=False,
                trust_remote_code=True,
                token=os.getenv("HF_KEY")
            )

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.original_model_name,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True,
                cache_dir=os.getenv("CACHE_DIR", "./cache"),
                token=os.getenv("HF_KEY")
            )

            self.model.eval()
            logger.info("Successfully loaded model without quantization")
        except Exception as e:
            logger.error(f"Failed to load any model configuration: {e}")
            raise Exception(f"Cannot load Vietnamese LLaMA model: {e}")

    def _create_evaluation_prompt(self, job_description: str, cv_text: str) -> str:
        # Create evaluation prompt for the model
        prompt = dedent(f'''<s>[INST] Bạn là một chuyên gia tuyển dụng. Hãy đánh giá CV sau đây dựa trên yêu cầu công việc và trả về kết quả theo định dạng JSON.
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
        ''')

        return prompt

    def evaluate_cv(self, job_description: str, cv_text: str) -> str:
        # Evaluate CV and return result
        try:
            if not self.model or not self.tokenizer:
                raise Exception("Model or tokenizer not loaded")

            prompt = self._create_evaluation_prompt(job_description=job_description, cv_text=cv_text)

            try:
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=6000,
                    padding=True
                )
            except Exception as e:
                logger.error(f"Error tokenizing prompt: {e}")
                return f"Error during tokenization: {str(e)}"

            try:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            except Exception as e:
                logger.error(f"Error moving inputs to device: {e}")
                return f"Error moving to device: {str(e)}"

            try:
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
            except Exception as e:
                logger.error(f"Error during generation: {e}")
                return f"Error during generation: {str(e)}"

            try:
                response = self.tokenizer.decode(
                    outputs[0][inputs['input_ids'].shape[1]:],
                    skip_special_tokens=True
                )

                logger.info("Successfully evaluated CV with Vietnamese LLaMA")
                return response.strip()

            except Exception as e:
                logger.error(f"Error decoding response: {e}")
                return f"Error decoding response: {str(e)}"

        except Exception as e:
            logger.error(f"Error evaluating CV: {e}")
            return f"Error during evaluation: {str(e)}"

    def extract_json_from_response(self, response: str) -> Optional[dict]:
        # Extract JSON from model response
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)

            logger.warning("No JSON found in response, creating default evaluation")
            return {
                "overall_score": 5.0,
                "is_qualified": False,
                "criteria_scores": {
                    "job_fit": 5.0,
                    "experience": 5.0,
                    "skills": 5.0,
                    "education": 5.0
                },
                "strengths": ["Cần phân tích thêm"],
                "weaknesses": ["Không thể đánh giá chi tiết"],
                "summary": "Không thể phân tích JSON từ phản hồi của model"
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return {
                "overall_score": 5.0,
                "is_qualified": False,
                "criteria_scores": {
                    "job_fit": 5.0,
                    "experience": 5.0,
                    "skills": 5.0,
                    "education": 5.0
                },
                "strengths": ["Cần phân tích thêm"],
                "weaknesses": ["Lỗi phân tích JSON"],
                "summary": f"Lỗi phân tích JSON: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            return None

_vietnamese_llama = None

def get_vietnamese_llama():
    # Get Vietnamese LLaMA instance (singleton)
    global _vietnamese_llama
    if _vietnamese_llama is None:
        _vietnamese_llama = VietnameseLlamaEvaluator()
    return _vietnamese_llama
"""

# ================================================================================
# REPLACEMENT FUNCTIONS FOR BACKWARD COMPATIBILITY
# ================================================================================

import logging
from gpt_evaluator import get_gpt_evaluator

logger = logging.getLogger(__name__)

def get_vietnamese_llama():
    """
    Backward compatibility function that returns GPT evaluator instead of LLaMA.
    This maintains the same interface while using the more efficient GPT-3.5-turbo.
    """
    logger.info("Vietnamese LLaMA requested, returning GPT evaluator instead")
    return get_gpt_evaluator()

# Note: The GPT evaluator has the same interface methods:
# - evaluate_cv(job_description, cv_text)
# - extract_json_from_response(response)
# So existing code will continue to work without modification.