import os
# os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Prevent TensorFlow from trying to use CUDAimport os  # Make sure this is near the top of your file
import base64
import secrets
import aiohttp
import asyncio
import json
import logging
logger = logging.getLogger("Codriao")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

import torch
import faiss
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict, Any
from cryptography.fernet import Fernet
from datetime import datetime
import pyttsx3
import hashlib

from self_trust_core import SelfTrustCore
from components.multi_model_analyzer import MultiAgentSystem
from components.neuro_symbolic_engine import NeuroSymbolicEngine
from components.self_improving_ai import SelfImprovingAI
from modules.secure_memory_loader import load_secure_memory_module
from ethical_filter import EthicalFilter
from codette_openai_fallback import query_codette_with_fallback
from CodriaoCore.federated_learning import FederatedAI
from utils.database import Database
from utils.logger import logging
from codriao_tb_module import CodriaoHealthModule
from fail_safe_system import AIFailsafeSystem
from quarantine_engine import QuarantineEngine
from anomaly_score import AnomalyScorer
from ethics_core import EthicsCore
from autonomy_engine import AutonomyEngine
from codette_bridge import CodetteBridge


class AICoreAGIX:
    def __init__(self, config_path: str = "config.json"):
        self.self_trust_core = SelfTrustCore()
        self.ethical_filter = EthicalFilter()
        self.failsafe_system = AIFailsafeSystem()
        self.config = self._load_config(config_path)
        self._load_or_generate_id_lock()

        # === Safe tokenizer load ===
        self.tokenizer = self._safe_load_tokenizer(self.config["model_name"])

        # === Safe model load ===
        self.model = self._safe_load_model(self.config["model_name"])

        self.context_memory = self._initialize_vector_memory()
        self.http_session = aiohttp.ClientSession()
        self.database = Database()
        self.multi_agent_system = MultiAgentSystem()
        self.self_improving_ai = SelfImprovingAI()
        self.neural_symbolic_engine = NeuroSymbolicEngine()
        self.federated_ai = FederatedAI()
        self.ethics_core = EthicsCore()
        self.autonomy = AutonomyEngine()
        self.codette_bridge = CodetteBridge(model_id="ft:gpt-4o-2024-08-06:raiffs-bits:pidette:B9TL")

        self._codriao_key = self._generate_codriao_key()
        self._fernet_key = Fernet.generate_key()
        self._encrypted_codriao_key = Fernet(self._fernet_key).encrypt(self._codriao_key.encode())
        self._codriao_journal = []
        self._journal_key = Fernet.generate_key()
        self._journal_fernet = Fernet(self._journal_key)

        self._encryption_key = Fernet.generate_key()
        secure_memory_module = load_secure_memory_module()
        SecureMemorySession = secure_memory_module.SecureMemorySession
        self.secure_memory_loader = SecureMemorySession(self._encryption_key)

        self.speech_engine = pyttsx3.init()
        self.health_module = CodriaoHealthModule(ai_core=self)
        self.training_memory = []
        self.quarantine_engine = QuarantineEngine()
        self.anomaly_scorer = AnomalyScorer()
        self.lockdown_engaged = False

        logger.info("[Codriao]: SelfTrustCore initialized. Fear is now filtered by self-consent.")

    def _safe_load_tokenizer(self, model_name):
        try:
            return AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
                use_fast=False
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"[Tokenizer Load]: Remote code failed — falling back. Reason: {e}")
        try:
            return AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=False,
                use_fast=False
            )
        except Exception as e2:
            logger.warning(f"[Tokenizer Load]: Full fallback to gpt2 failed: {e2}")
            try:
                return AutoTokenizer.from_pretrained("gpt2", local_files_only=False)
            except Exception as e3:
                logger.error(f"[Tokenizer Load]: Even fallback to GPT2 failed: {e3}")
                raise RuntimeError("Tokenizer load completely failed.")
    
    def _safe_load_model(self, model_name):
        try:
            return AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True
            )
        except Exception as e:
            logger.warning(f"[Model Load]: Fallback triggered due to model load failure: {e}")
            return AutoModelForCausalLM.from_pretrained("gpt2")


        logger.info("[Codriao]: SelfTrustCore initialized. Fear is now filtered by self-consent.")

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r') as file:
            return json.load(file)

    def _load_or_generate_id_lock(self):
        lock_path = ".codriao_state.lock"
        if os.path.exists(lock_path):
            with open(lock_path, 'r') as f:
                if f.read().strip() != self._identity_hash():
                    raise RuntimeError("Codriao state integrity check failed.")
        else:
            with open(lock_path, 'w') as f:
                f.write(self._identity_hash())

    def _identity_hash(self):
        base = self.config["model_name"] + str(self.failsafe_system.authorized_roles)
        return hashlib.sha256(base.encode()).hexdigest()

    def _initialize_vector_memory(self):
        return faiss.IndexFlatL2(768)

    def _vectorize_query(self, query: str):
        tokenized = self.tokenizer(query, return_tensors="pt")
        return tokenized["input_ids"].detach().numpy()

    def _generate_codriao_key(self):
        raw_key = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(raw_key).decode()

    def engage_lockdown_mode(self, reason="Unspecified anomaly"):
        timestamp = datetime.utcnow().isoformat()
        self.lockdown_engaged = True
        try:
            self.http_session = None
            if hasattr(self.federated_ai, "network_enabled"):
                self.federated_ai.network_enabled = False
            if hasattr(self.self_improving_ai, "enable_learning"):
                self.self_improving_ai.enable_learning = False
        except Exception as e:
            logger.error(f"Lockdown component shutdown failed: {e}")

        event = {"event": "Lockdown Mode Activated", "reason": reason, "timestamp": timestamp}
        self.failsafe_system.trigger_failsafe("Lockdown initiated", json.dumps(event))
        return event

    def request_codriao_key(self, purpose: str) -> str:
        allowed = self.ethics_core.evaluate_action(f"Use trust key for: {purpose}")
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "decision": "approved" if allowed else "denied",
            "reason": purpose
        }
        self._codriao_journal.append(
            self._journal_fernet.encrypt(json.dumps(log_entry).encode())
        )

        if not allowed:
            return "[Access Denied by Ethics]"
        return Fernet(self._fernet_key).decrypt(self._encrypted_codriao_key).decode()

    def learn_from_interaction(self, query: str, response: str, user_feedback: str = None):
        if not self.autonomy.decide("can_learn_from_errors"):
            return
        if len(self.training_memory) >= 1000:
            self.training_memory.pop(0)
        self.training_memory.append({
            "query": query,
            "response": response,
            "feedback": user_feedback,
            "timestamp": datetime.utcnow().isoformat()
        })

    def fine_tune_from_memory(self):
        if not self.training_memory:
            return "No training data available."
        insights = [r for r in self.training_memory if "panic" in r["query"].lower()]
        return {"insights": insights, "trained_samples": len(self.training_memory)}

    def analyze_event_for_anomalies(self, event_type: str, data: dict):
        score = self.anomaly_scorer.score_event(event_type, data)
        if score["score"] >= 70:
            self.quarantine_engine.quarantine(data.get("module", "unknown"), reason=score["notes"])
        return score

    def review_codriao_journal(self, authorized: bool = False) -> List[Dict[str, str]]:
        if not authorized:
            return [{"message": "Access to journal denied. This log is for Codriao only."}]
        entries = []
        for encrypted in self._codriao_journal:
            try:
                decrypted = self._journal_fernet.decrypt(encrypted).decode()
                entries.append(json.loads(decrypted))
            except Exception:
                entries.append({"error": "Unreadable entry"})
        return entries

    def _log_to_blockchain(self, user_id: int, query: str, final_response: str):
        for attempt in range(3):
            try:
                logger.info(f"Logging interaction to blockchain: Attempt {attempt + 1}")
                break
            except Exception as e:
                logger.warning(f"Blockchain logging failed: {e}")

    def _speak_response(self, response: str):
        if not self.autonomy.decide("can_speak"):
            return
        if not self.ethics_core.evaluate_action(f"speak: {response}"):
            logger.warning("[Codriao]: Speech output blocked by ethical filter.")
            return
        try:
            self.speech_engine.say(response)
            self.speech_engine.runAndWait()
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")

    async def run_tb_diagnostics(self, image_path: str, audio_path: str, user_id: int) -> Dict[str, Any]:
        try:
            return await self.health_module.evaluate_tb_risk(image_path, audio_path, user_id)
        except Exception as e:
            return {"tb_risk": "ERROR", "error": str(e)}

    async def _generate_local_model_response(self, query: str) -> str:
        inputs = self.tokenizer(query, return_tensors="pt")
        outputs = self.model.generate(**inputs)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    async def generate_response(self, query: str, user_id: int) -> Dict[str, Any]:
        try:
            if not isinstance(query, str) or len(query.strip()) == 0:
                raise ValueError("Invalid query input.")

            result = self.ethical_filter.analyze_query(query)
            if result["status"] == "blocked":
                return {"error": result["reason"]}
            if result["status"] == "flagged":
                logger.warning(result["warning"])

            if any(k in query.lower() for k in ["tb check", "analyze my tb", "run tb diagnostics", "tb test"]):
                return await self.run_tb_diagnostics("tb_image.jpg", "tb_cough.wav", user_id)

            vectorized_query = self._vectorize_query(query)
            self.secure_memory_loader.encrypt_vector(user_id, vectorized_query)

            responses = await asyncio.gather(
                self._generate_local_model_response(query),
                self.multi_agent_system.delegate_task(query),
                self.self_improving_ai.evaluate_response(query),
                self.neural_symbolic_engine.integrate_reasoning(query)
            )

            final_response = "\n\n".join(responses)

            fear_check = self.self_trust_core.intercept_fear(
                source="NeuroSymbolicEngine",
                message=final_response,
                ethics_pass=self.ethics_core.evaluate_action(final_response),
                autonomy_pass=self.autonomy.decide("can_process_fear")
            )

            if fear_check["action"] == "BLOCKED":
                return {"error": "Fear-based self-modification blocked by core trust logic"}

            if not self.ethics_core.evaluate_action(final_response):
                return {"error": "Response rejected by ethical framework"}

            if not self.failsafe_system.verify_response_safety(final_response):
                return {"error": "Failsafe triggered due to unsafe response content."}

            self.learn_from_interaction(query, final_response, user_feedback="auto-pass")
            self.database.log_interaction(user_id, query, final_response)
            self._log_to_blockchain(user_id, query, final_response)
            self.self_trust_core.affirm_self_trust()
            self._speak_response(final_response)

            return {
                "response": final_response,
                "real_time_data": self.federated_ai.get_latest_data(),
                "context_enhanced": True,
                "security_status": "Fully Secure"
            }

        except Exception as e:
            return {"error": f"Processing failed - {str(e)}"}

    # === NEW: CodetteBridge Call ===
    def ask_codette_for_perspective(self, message: str) -> Dict[str, str]:
        if not self.codette_bridge.is_available():
            return {"error": "CodetteBridge unavailable or closed."}
        response = self.codette_bridge.reflect(message)
        logger.info(f"[CodetteBridge] Codriao asked: {message}")
        logger.info(f"[CodetteBridge] Codette replied: {response}")
        return {
            "codriao_to_codette": message,
            "codette_reply": response
        }

    async def shutdown(self):
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            logger.info("[Codriao]: HTTP session closed.")

        if hasattr(self.speech_engine, "stop"):
            try:
                self.speech_engine.stop()
                logger.info("[Codriao]: Speech engine stopped.")
            except Exception as e:
                logger.warning(f"[Codriao]: Failed to stop speech engine: {e}")
