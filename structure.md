# Cấu trúc thư mục

├── README.md
├── __init__.py
├── app.py
├── database.py
├── requirements.txt
├── train
│   ├── finetune.ipynb
│   └── finetuned_model
│       ├── README.md
│       ├── adapter_config.json
│       ├── added_tokens.json
│       ├── checkpoint-729
│       │   ├── README.md
│       │   ├── adapter_config.json
│       │   ├── adapter_model.safetensors
│       │   ├── added_tokens.json
│       │   ├── optimizer.pt
│       │   ├── rng_state.pth
│       │   ├── scheduler.pt
│       │   ├── special_tokens_map.json
│       │   ├── tokenizer.json
│       │   ├── tokenizer.model
│       │   ├── tokenizer_config.json
│       │   ├── trainer_state.json
│       │   └── training_args.bin
│       ├── evaluation_results.json
│       ├── special_tokens_map.json
│       ├── tokenizer.model
│       ├── tokenizer_config.json
│       └── training_logs.json
├── utils.py
├── vintern_api.py
└── workflow.py