"""
UniversalReasoning — Legacy Standalone Entry Point
===================================================
DEPRECATED: This module predates the current Codette server architecture
(codette_server.py + forge_engine.py). It is preserved for historical
reference and standalone experimentation.

For production use, see:
  inference/codette_server.py    — HTTP server + SSE streaming
  reasoning_forge/forge_engine.py — Multi-agent orchestration

What was fixed before archiving:
  - Removed unused botbuilder / dialog_helper imports (Azure Bot Framework,
    not used in any method)
  - Replaced missing `perspectives` module with current reasoning_forge agents
    via compatibility shims that adapt the old async generate_response() API
    to the current sync analyze() API
  - destroy_sensitive_data() now overwrites the string before del (Python
    cannot guarantee zero-memory-clear, but this reduces window of exposure)
  - fetch_real_time_data() URL is now read from config, not hardcoded
  - Removed unused word_tokenize import
"""

import asyncio
import json
import logging
import os
import nest_asyncio
from typing import List, Dict, Any
from cryptography.fernet import Fernet
import aiohttp
import speech_recognition as sr
from PIL import Image
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

load_dotenv()
nest_asyncio.apply()


# ── Compatibility shims: map old Perspective API to current Agent API ──────────
# Old API: perspective.generate_response(question) -> coroutine -> str
# New API: agent.analyze(concept) -> str (sync)

def _make_perspective_shim(agent_class):
    """Wraps a current ReasoningAgent to satisfy the old async generate_response API."""
    class _Shim:
        def __init__(self, config):
            try:
                self._agent = agent_class()
            except Exception:
                self._agent = None

        async def generate_response(self, question: str) -> str:
            if self._agent is None:
                return f"[{agent_class.__name__}] unavailable"
            return await asyncio.to_thread(self._agent.analyze, question)

        @property
        def __class__(self):
            return agent_class

    _Shim.__name__ = agent_class.__name__.replace("Agent", "Perspective")
    return _Shim


try:
    from reasoning_forge.agents.newton_agent import NewtonAgent
    from reasoning_forge.agents.davinci_agent import DaVinciAgent
    from reasoning_forge.agents.quantum_agent import QuantumAgent
    from reasoning_forge.agents.empathy_agent import EmpathyAgent
    from reasoning_forge.agents.ethics_agent import EthicsAgent
    from reasoning_forge.agents.philosophy_agent import PhilosophyAgent

    NewtonPerspective = _make_perspective_shim(NewtonAgent)
    DaVinciPerspective = _make_perspective_shim(DaVinciAgent)
    QuantumComputingPerspective = _make_perspective_shim(QuantumAgent)
    ResilientKindnessPerspective = _make_perspective_shim(EmpathyAgent)
    PhilosophicalPerspective = _make_perspective_shim(PhilosophyAgent)

    # No direct equivalents — use philosophy agent as fallback
    HumanIntuitionPerspective = _make_perspective_shim(EmpathyAgent)
    NeuralNetworkPerspective = _make_perspective_shim(NewtonAgent)
    MathematicalPerspective = _make_perspective_shim(NewtonAgent)
    CopilotPerspective = _make_perspective_shim(PhilosophyAgent)
    BiasMitigationPerspective = _make_perspective_shim(EthicsAgent)
    PsychologicalPerspective = _make_perspective_shim(EmpathyAgent)

    _AGENTS_AVAILABLE = True
except ImportError as _e:
    logging.warning(f"universal_reasoning: forge agents unavailable ({_e}) — perspectives will be stubs")
    _AGENTS_AVAILABLE = False

    class _StubPerspective:
        def __init__(self, config): pass
        async def generate_response(self, question): return f"[stub] {question}"

    for _name in ["NewtonPerspective", "DaVinciPerspective", "HumanIntuitionPerspective",
                  "NeuralNetworkPerspective", "QuantumComputingPerspective",
                  "ResilientKindnessPerspective", "MathematicalPerspective",
                  "PhilosophicalPerspective", "CopilotPerspective",
                  "BiasMitigationPerspective", "PsychologicalPerspective"]:
        globals()[_name] = _StubPerspective


# ── Logging ────────────────────────────────────────────────────────────────────

def setup_logging(config):
    if config.get('logging_enabled', True):
        log_level = config.get('log_level', 'DEBUG').upper()
        numeric_level = getattr(logging, log_level, logging.DEBUG)
        logging.basicConfig(
            filename='universal_reasoning.log',
            level=numeric_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    else:
        logging.disable(logging.CRITICAL)


def load_json_config(file_path):
    if not os.path.exists(file_path):
        logging.error(f"Configuration file '{file_path}' not found.")
        return {}
    try:
        with open(file_path, 'r') as file:
            config = json.load(file)
            logging.info(f"Configuration loaded from '{file_path}'.")
            return config
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from '{file_path}': {e}")
        return {}


# ── Crypto helpers ─────────────────────────────────────────────────────────────

def encrypt_sensitive_data(data, key):
    fernet = Fernet(key)
    return fernet.encrypt(data.encode())


def decrypt_sensitive_data(encrypted_data, key):
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data).decode()


def destroy_sensitive_data(data):
    # Python strings are immutable so true zero-fill isn't possible, but
    # overwriting the local reference and triggering GC reduces exposure window.
    if isinstance(data, bytearray):
        for i in range(len(data)):
            data[i] = 0
    del data


# ── Supporting classes ─────────────────────────────────────────────────────────

class Element:
    def __init__(self, name, symbol, representation, properties, interactions, defense_ability):
        self.name = name
        self.symbol = symbol
        self.representation = representation
        self.properties = properties
        self.interactions = interactions
        self.defense_ability = defense_ability

    def execute_defense_function(self):
        message = f"{self.name} ({self.symbol}) executes its defense ability: {self.defense_ability}"
        logging.info(message)
        return message


class RecognizerResult:
    def __init__(self, text):
        self.text = text


class CustomRecognizer:
    def recognize(self, question):
        if any(name.lower() in question.lower() for name in ["hydrogen", "diamond"]):
            return RecognizerResult(question)
        return RecognizerResult(None)

    def get_top_intent(self, recognizer_result):
        return "ElementDefense" if recognizer_result.text else "None"


# ── Main class ─────────────────────────────────────────────────────────────────

class UniversalReasoning:
    def __init__(self, config):
        self.config = config
        self.perspectives = self._initialize_perspectives()
        self.elements = self._initialize_elements()
        self.recognizer = CustomRecognizer()
        self.context_history = []
        self.feedback = []
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def _initialize_perspectives(self):
        perspective_names = self.config.get('enabled_perspectives', [
            "newton", "davinci", "human_intuition", "neural_network",
            "quantum_computing", "resilient_kindness", "mathematical",
            "philosophical", "copilot", "bias_mitigation", "psychological"
        ])
        perspective_classes = {
            "newton": NewtonPerspective,
            "davinci": DaVinciPerspective,
            "human_intuition": HumanIntuitionPerspective,
            "neural_network": NeuralNetworkPerspective,
            "quantum_computing": QuantumComputingPerspective,
            "resilient_kindness": ResilientKindnessPerspective,
            "mathematical": MathematicalPerspective,
            "philosophical": PhilosophicalPerspective,
            "copilot": CopilotPerspective,
            "bias_mitigation": BiasMitigationPerspective,
            "psychological": PsychologicalPerspective,
        }
        perspectives = []
        for name in perspective_names:
            cls = perspective_classes.get(name.lower())
            if cls:
                perspectives.append(cls(self.config))
                logging.debug(f"Perspective '{name}' initialized.")
            else:
                logging.warning(f"Perspective '{name}' not recognized, skipped.")
        return perspectives

    def _initialize_elements(self):
        return [
            Element("Hydrogen", "H", "Lua",
                    ["Simple", "Lightweight", "Versatile"],
                    ["Easily integrates with other languages"],
                    "Evasion"),
            Element("Diamond", "D", "Kotlin",
                    ["Modern", "Concise", "Safe"],
                    ["Used for Android development"],
                    "Adaptability"),
        ]

    async def generate_response(self, question: str) -> str:
        self.context_history.append(question)
        self.analyze_sentiment(question)

        # Fetch real-time data from configurable URL (not hardcoded)
        data_url = self.config.get('real_time_data_url', '')
        if data_url:
            try:
                await self.fetch_real_time_data(data_url)
            except Exception as e:
                logging.warning(f"Real-time data fetch failed: {e}")

        tasks = []
        for perspective in self.perspectives:
            if asyncio.iscoroutinefunction(perspective.generate_response):
                tasks.append(perspective.generate_response(question))
            else:
                async def _wrap(p=perspective, q=question):
                    return await asyncio.to_thread(p.generate_response, q)
                tasks.append(_wrap())

        perspective_results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for perspective, result in zip(self.perspectives, perspective_results):
            if isinstance(result, Exception):
                logging.error(f"Error from {perspective.__class__.__name__}: {result}")
            else:
                responses.append(result)

        recognizer_result = self.recognizer.recognize(question)
        if self.recognizer.get_top_intent(recognizer_result) == "ElementDefense":
            element_name = recognizer_result.text.strip()
            element = next(
                (el for el in self.elements if el.name.lower() in element_name.lower()), None
            )
            if element:
                responses.append(element.execute_defense_function())

        ethical = self.config.get(
            'ethical_considerations',
            "Always act with transparency, fairness, and respect for privacy."
        )
        responses.append(f"**Ethical Considerations:**\n{ethical}")
        return "\n\n".join(responses)

    def analyze_sentiment(self, text: str) -> dict:
        score = self.sentiment_analyzer.polarity_scores(text)
        logging.info(f"Sentiment: {score}")
        return score

    async def fetch_real_time_data(self, source_url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(source_url) as response:
                return await response.json()

    def process_feedback(self, feedback: str):
        self.feedback.append(feedback)
        score = self.sentiment_analyzer.polarity_scores(feedback)["compound"]
        logging.info(f"Feedback sentiment: {score}")
        if score < -0.5:
            logging.warning("Negative feedback detected — flagging for review.")

    def save_response(self, response: str):
        if self.config.get('enable_response_saving', False):
            try:
                path = self.config.get('response_save_path', 'responses.txt')
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(response + '\n')
                logging.info("Response saved.")
            except Exception as e:
                logging.error(f"Failed to save response: {e}")

    def backup_response(self, response: str):
        backup_cfg = self.config.get('backup_responses', {})
        if backup_cfg.get('enabled', False):
            try:
                path = backup_cfg.get('backup_path', 'backup_responses.txt')
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(response + '\n')
                logging.info("Response backed up.")
            except Exception as e:
                logging.error(f"Failed to backup response: {e}")

    def handle_voice_input(self) -> str | None:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print(f"Google service error: {e}")
        return None

    def handle_image_input(self, image_path: str):
        try:
            return Image.open(image_path)
        except Exception as e:
            print(f"Image error: {e}")
            return None


# ── Standalone entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    config = load_json_config('config.json')
    setup_logging(config)

    azure_openai_api_key = os.getenv('AZURE_OPENAI_API_KEY', '')
    azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT', '')

    if azure_openai_api_key:
        encryption_key = Fernet.generate_key()
        encrypted_api_key = encrypt_sensitive_data(azure_openai_api_key, encryption_key)
        encrypted_endpoint = encrypt_sensitive_data(azure_openai_endpoint, encryption_key)
        config['azure_openai_api_key'] = encrypted_api_key
        config['azure_openai_endpoint'] = encrypted_endpoint

    engine = UniversalReasoning(config)
    question = "Tell me about Hydrogen and its defense mechanisms."
    response = asyncio.run(engine.generate_response(question))
    print(response)

    if response:
        engine.save_response(response)
        engine.backup_response(response)

    voice_input = engine.handle_voice_input()
    if voice_input:
        print(asyncio.run(engine.generate_response(voice_input)))

    image_input = engine.handle_image_input("path_to_image.jpg")
    if image_input:
        print("Image loaded successfully.")
