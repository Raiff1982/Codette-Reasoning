import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel


class CodetteModelLoader:

    def __init__(
        self,
        base_model="meta-llama/Llama-3.1-8B-Instruct",
        adapters=None,
    ):
        self.base_model_name = base_model
        self.adapters = adapters or {}
        self.model = None
        self.tokenizer = None
        self.active_adapter = None

        self._load_base_model()

    def _load_base_model(self):

        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name,
            trust_remote_code=True
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            quantization_config=quant_config,
            device_map="auto",
            trust_remote_code=True,
        )

        self.model = base_model

    def load_adapters(self):

        first = True

        for name, path in self.adapters.items():

            path = str(Path(path))

            if first:

                self.model = PeftModel.from_pretrained(
                    self.model,
                    path,
                    adapter_name=name,
                    is_trainable=False,
                )

                self.active_adapter = name
                first = False

            else:

                self.model.load_adapter(
                    path,
                    adapter_name=name,
                )

    def set_active_adapter(self, name):

        if name not in self.model.peft_config:
            raise ValueError(f"Adapter not loaded: {name}")

        self.model.set_adapter(name)
        self.active_adapter = name

    def format_messages(self, messages):

        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

    def tokenize(self, prompt):

        return self.tokenizer(
            prompt,
            return_tensors="pt"
        ).to(self.model.device)