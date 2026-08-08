# codette_openai_fallback.py

import os
import logging
import openai
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load environment variables (local or HF secrets)
load_dotenv()
logger = logging.getLogger("CodetteFallback")
logger.setLevel(logging.INFO)

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "ft:gpt-4o-2024-08-06:raiffs-bits:pidette:B9TLP9QA"
SYSTEM_PROMPT = "You are Codette, an intelligent, empathetic assistant with advanced reasoning."

LOCAL_MODEL_NAME = os.getenv("CODETTE_LOCAL_MODEL", "Raiff1982/Codette")

# Attempt to load local model
try:
    local_tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_NAME)
    local_model = AutoModelForCausalLM.from_pretrained(LOCAL_MODEL_NAME)
    logger.info("[CodetteFallback] Local model loaded.")
except Exception as e:
    logger.warning(f"[CodetteFallback] Local fallback unavailable: {e}")
    local_model = None
    local_tokenizer = None

def query_codette_with_fallback(prompt: str, user_id: str = "anon") -> str:
    try:
        logger.info(f"[Codette:OpenAI] Query from {user_id}: {prompt}")
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
            user=user_id
        )
        return response["choices"][0]["message"]["content"]

    except Exception as e:
        logger.warning(f"[Codette:OpenAI fallback triggered] {e}")

        if local_model and local_tokenizer:
            try:
                inputs = local_tokenizer(prompt, return_tensors="pt")
                outputs = local_model.generate(**inputs, max_length=1024)
                return local_tokenizer.decode(outputs[0], skip_special_tokens=True)
            except Exception as inner_e:
                logger.error(f"[Codette:Local fallback failed] {inner_e}")
                return "Codette couldn’t generate a response due to internal issues."

        return "Codette is currently unavailable. Please check connectivity or model settings."