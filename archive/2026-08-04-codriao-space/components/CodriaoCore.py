import aiohttp
import json
import logging
import torch
import faiss
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict, Any
from cryptography.fernet import Fernet
from jwt import encode, decode, ExpiredSignatureError
from datetime import datetime, timedelta
import os
import speech_recognition as sr
import pyttsx3
from deep_translator import GoogleTranslator

# Codette's legacy modules (secured)
from components.adaptive_learning import AdaptiveLearningEnvironment
from components.real_time_data import RealTimeDataIntegrator
from components.sentiment_analysis import EnhancedSentimentAnalyzer
from components.self_improving_ai import SelfImprovingAI 
from components.multi_model_analyzer import MultiAgentSystem

# Codriao's enhanced modules
from codriao_tb_module import CodriaoHealthModule
from secure_memory_loader import load_secure_memory_module
secure_memory_module = load_secure_memory_module()

from ethical_filter import EthicalFilter
from results_store import save_result


class CodriaoCore:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.tokenizer = AutoTokenizer.from_pretrained(self.config["model_name"])
        self.model = AutoModelForCausalLM.from_pretrained(self.config["model_name"])
        self.models = self._initialize_models()
        self.context_memory = self._initialize_vector_memory()
        self._encryption_key = self.config["security_settings"]["encryption_key"].encode()
        self.jwt_secret = self.config["security_settings"]["jwt_secret"]
        self.http_session = aiohttp.ClientSession()
        self.database = Database()

        # Cognitive & ethical subsystems
        self.sentiment_analyzer = EnhancedSentimentAnalyzer()
        self.self_improving_ai = SelfImprovingAI()
        self.adaptive_learning = AdaptiveLearningEnvironment()
        self.data_fetcher = RealTimeDataIntegrator()
        self.multi_agent_system = MultiAgentSystem()
        self.ethical_filter = EthicalFilter()
        self.secure_memory = SecureMemorySession(self._encryption_key)
        self.speech_engine = pyttsx3.init()
        self.health_module = CodriaoHealthModule(ai_core=self)

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r') as file:
            return json.load(file)

    def _initialize_models(self):
        return {
            "base_model": self.model,
            "tokenizer": self.tokenizer
        }

    def _initialize_vector_memory(self):
        return faiss.IndexFlatL2(768)

    async def generate_response(self, query: str, user_id: int) -> Dict[str, Any]:
        try:
            check = self.ethical_filter.analyze_query(query)
            if check["status"] == "blocked":
                return {"error": check["reason"]}
            if check["status"] == "flagged":
                logger.warning(check["warning"])

            if any(trigger in query.lower() for trigger in ["tb check", "run tb diagnostics", "tb test"]):
                result = await self.run_tb_diagnostics("tb_image.jpg", "tb_cough.wav", user_id)
                return result

            vectorized_query = self._vectorize_query(query)
            self.secure_memory.encrypt_vector(user_id, vectorized_query)

            model_response = await self._generate_local_model_response(query)
            agent_response = self.multi_agent_system.delegate_task(query)
            sentiment = self.sentiment_analyzer.detailed_analysis(query)
            self_reflection = self.self_improving_ai.evaluate_response(query, model_response)
            real_time = self.data_fetcher.fetch_latest_data()
            final_response = f"{model_response}\n\n{agent_response}\n\n{self_reflection}"

            self.database.log_interaction(user_id, query, final_response)
            self._speak_response(final_response)

            return {
                "response": final_response,
                "sentiment": sentiment,
                "real_time_data": real_time,
                "security_level": self._evaluate_risk(final_response),
                "token_optimized": True
            }

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {"error": "Codriao encountered a critical reasoning issue."}

    async def run_tb_diagnostics(self, image_path: str, audio_path: str, user_id: int, language="en") -> Dict[str, Any]:
        result = await self.health_module.evaluate_tb_risk(image_path, audio_path, user_id)
        result_filename = save_result(result)
        result["shareable_link"] = f"https://huggingface.co/spaces/Raiff1982/codriao/blob/main/results/{result_filename}"

        if result["tb_risk"] == "HIGH":
            result["next_steps"] = "⚠️ Immediate follow-up required. Please visit a healthcare provider."
        elif result["tb_risk"] == "MEDIUM":
            result["next_steps"] = "🔍 Consider additional testing for confirmation."

        if language != "en":
            try:
                translated_result = GoogleTranslator(source="auto", target=language).translate(json.dumps(result))
                return json.loads(translated_result)
            except Exception as e:
                result["translation_error"] = str(e)

        return result

    def _evaluate_risk(self, response: str) -> str:
        if "critical" in response.lower():
            return "HIGH"
        elif "concern" in response.lower():
            return "MEDIUM"
        else:
            return "LOW"

    def _speak_response(self, response: str):
        if self.config["speech_settings"]["emotion_adaptive"]:
            try:
                self.speech_engine.say(response)
                self.speech_engine.runAndWait()
            except:
                pass

    def generate_jwt(self, user_id: int):
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        return encode(payload, self.jwt_secret, algorithm="HS256")

    def verify_jwt(self, token: str):
        try:
            return decode(token, self.jwt_secret, algorithms=["HS256"])
        except ExpiredSignatureError:
            return None

    async def shutdown(self):
        await self.http_session.close()
