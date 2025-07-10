from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

model = AutoModelForSeq2SeqLM.from_pretrained("VietAI/vit5-base")
tokenizer = AutoTokenizer.from_pretrained("VietAI/vit5-base", use_fast=False)

model.save_pretrained("vit5-base")
tokenizer.save_pretrained("vit5-base")
